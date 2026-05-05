use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Tabs},
    Frame,
};

use crate::state::kantor_state::{KantorState, WorkersTab};
use crate::ui::components::{spinner_char, task_state_icon, worker_status_icon};
use crate::ui::theme::Theme;

/// Tab titles for the middle panel
const TAB_TITLES: &[&str] = &["Workers", "Briefing", "DAG", "Events"];

/// Render the Workers Live panel (middle column in Kantor mode, tabbed)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Layout: tab bar + content
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(1), Constraint::Min(0)])
        .split(inner);

    // Tab bar
    let tab_idx = match state.active_tab {
        WorkersTab::Workers => 0,
        WorkersTab::Briefing => 1,
        WorkersTab::Dag => 2,
        WorkersTab::Events => 3,
    };

    let tab_titles: Vec<Line> = TAB_TITLES
        .iter()
        .enumerate()
        .map(|(i, title)| {
            let style = if i == tab_idx {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.dim)
            };
            Line::from(Span::styled(*title, style))
        })
        .collect();

    let tabs = Tabs::new(tab_titles);
    f.render_widget(tabs, chunks[0]);

    // Render active tab content
    match state.active_tab {
        WorkersTab::Workers => render_workers_tab(f, chunks[1], state, theme),
        WorkersTab::Briefing => render_briefing_tab(f, chunks[1], state, theme),
        WorkersTab::Dag => render_dag_tab(f, chunks[1], state, theme),
        WorkersTab::Events => render_events_tab(f, chunks[1], state, theme),
    }
}

fn render_workers_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    // Show last N worker events (matching Python's max 50 visible entries)
    let visible_count = area.height as usize;
    let events: Vec<&crate::state::kantor_state::WorkerEvent> = state
        .worker_events
        .iter()
        .rev()
        .take(visible_count)
        .collect();

    let items: Vec<ListItem> = events.iter().map(|ev| {
        let icon = match ev.event_type.as_str() {
            "task_done" => "✓",
            "task_failed" => "✗",
            "llm_chunk" => "─",
            s if s.starts_with("speak_up") => "💬",
            _ => "●",
        };

        let worker_style = Style::default().fg(theme.cyan);
        let content_style = Style::default().fg(theme.fg);

        let content_preview = if ev.content.len() > 60 {
            format!("{}...", &ev.content[..57])
        } else {
            ev.content.clone()
        };

        Line::from(vec![
            Span::styled(format!("{} ", icon), Style::default().fg(theme.dim)),
            Span::styled(format!("{:<15} ", ev.worker_id), worker_style),
            Span::styled(content_preview, content_style),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, area);
}

fn render_briefing_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.briefing_messages.is_empty() {
        let placeholder = Paragraph::new("No briefing messages yet.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    let items: Vec<ListItem> = state.briefing_messages.iter().map(|msg| {
        Line::from(vec![
            Span::styled(format!("{:<15} ", msg.worker_id), Style::default().fg(theme.cyan)),
            Span::styled(&msg.content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, area);
}

fn render_dag_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.dag_nodes.is_empty() {
        let placeholder = Paragraph::new("No task DAG yet.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    let lines = render_dag_tree(&state.dag_nodes, 0, true);
    let items: Vec<ListItem> = lines.iter().map(|line| {
        ListItem::new(line.clone())
    }).collect();

    let list = List::new(items);
    f.render_widget(list, area);
}

fn render_events_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.event_log.is_empty() {
        let placeholder = Paragraph::new("No events logged yet.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    let visible_count = area.height as usize;
    let events: Vec<&crate::state::kantor_state::LogEvent> = state
        .event_log
        .iter()
        .rev()
        .take(visible_count)
        .collect();

    let items: Vec<ListItem> = events.iter().map(|ev| {
        let color = crate::ui::components::severity_color(&ev.severity, theme);
        Line::from(vec![
            Span::styled(format!("{:<20} ", ev.event_type), Style::default().fg(color)),
            Span::styled(&ev.content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, area);
}

/// Render DAG as ASCII tree — the fix Python TUI lacked
fn render_dag_tree(nodes: &[crate::state::kantor_state::DagNode], depth: usize, _is_last: bool) -> Vec<Line<'static>> {
    let mut lines = Vec::new();

    for (i, node) in nodes.iter().enumerate() {
        let is_last_node = i == nodes.len() - 1;
        let prefix = if depth == 0 {
            String::new()
        } else {
            let connector = if is_last_node { "└── " } else { "├── " };
            let indent = if depth > 1 {
                "│   ".repeat(depth - 1)
            } else {
                String::new()
            };
            format!("{indent}{connector}")
        };

        let status_icon = match node.status.as_str() {
            "done" | "completed" => "✓",
            "working" | "in_progress" => "●",
            "failed" | "error" => "✗",
            "pending" => "○",
            _ => "·",
        };

        let line = Line::from(format!("{}{} {} ({})", prefix, status_icon, node.title, node.worker_id));
        lines.push(line);

        if !node.children.is_empty() {
            let child_lines = render_dag_tree(&node.children, depth + 1, is_last_node);
            lines.extend(child_lines);
        }
    }

    lines
}
