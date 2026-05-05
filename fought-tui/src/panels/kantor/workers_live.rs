use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Tabs},
    Frame,
};

use crate::state::kantor_state::{ContractState, KantorState, WorkersTab};
use crate::ui::components::{squad_color, spinner_char};
use crate::ui::theme::Theme;

/// Render the tabbed Workers Live panel (middle column in Kantor mode)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme, tick: u64) {
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(1), Constraint::Length(1), Constraint::Min(0)])
        .split(inner);

    // Phase indicator — using ContractState enum
    let (phase_text, phase_color) = match state.contract_state {
        ContractState::Idle => ("○ IDLE", theme.dim),
        ContractState::ManagerThinking | ContractState::Clarifying
        | ContractState::ContractPresented | ContractState::AwaitingRevision => ("◐ NEGOTIATING", theme.yellow),
        ContractState::TeamReview | ContractState::TodoReview => ("┼ BRIEFING", theme.secondary),
        ContractState::Working | ContractState::Accepted => ("⚡ EXECUTING", theme.success),
        ContractState::Verifying => ("◇ VERIFYING", theme.info),
        ContractState::Done => ("✓ COMPLETE", theme.green),
        ContractState::Failed => ("✗ FAILED", theme.error),
        ContractState::ClientFeedback => ("◐ FEEDBACK", theme.info),
    };
    f.render_widget(
        Paragraph::new(format!("  {phase_text}")).style(Style::default().fg(phase_color)),
        chunks[0],
    );

    // Tab bar
    let tab_idx = match state.active_tab {
        WorkersTab::Workers => 0,
        WorkersTab::Briefing => 1,
        WorkersTab::Dag => 2,
        WorkersTab::Events => 3,
    };
    let tab_titles: Vec<Line> = ["Workers", "Briefing", "DAG", "Events"]
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
    f.render_widget(tabs, chunks[1]);

    // Tab content
    match state.active_tab {
        WorkersTab::Workers => render_workers_tab(f, chunks[2], state, theme, tick),
        WorkersTab::Briefing => render_briefing_tab(f, chunks[2], state, theme),
        WorkersTab::Dag => render_dag_tab(f, chunks[2], state, theme),
        WorkersTab::Events => render_events_tab(f, chunks[2], state, theme),
    }
}

fn render_workers_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme, tick: u64) {
    let visible_count = area.height as usize;
    let events: Vec<&crate::state::kantor_state::WorkerEvent> = state
        .worker_events
        .iter()
        .rev()
        .take(visible_count)
        .collect();

    let items: Vec<ListItem> = events.iter().map(|ev| {
        let (icon, icon_color) = match ev.event_type.as_str() {
            "task_done" => ("✓", theme.green),
            "task_failed" => ("✗", theme.red),
            "task_started" => ("●", theme.yellow),
            "task_assigned" => ("○", theme.dim),
            "llm_start" => ("▶", theme.cyan),
            "llm_done" => ("■", theme.dim),
            "llm_chunk" => ("─", theme.dim),
            "speak_up" => ("◆", theme.fg),
            "circuit_open" => ("⚡", theme.red),
            "circuit_closed" => ("✓", theme.green),
            "rate_limit" => ("⏳", theme.yellow),
            "delegation_request" => ("→", theme.cyan),
            "delegation_result" => ("←", theme.info),
            _ => ("·", theme.dim),
        };

        let worker_color = squad_color(&ev.worker_id, theme);
        let content_preview = if ev.content.len() > 80 {
            format!("{}...", &ev.content[..77])
        } else if ev.content.is_empty() {
            ev.event_type.clone()
        } else {
            ev.content.clone()
        };

        // LLM streaming indicator
        let streaming = if state.llm_streaming_worker.as_deref() == Some(&ev.worker_id)
            && ev.event_type == "llm_start" {
            format!(" {}", spinner_char(tick))
        } else {
            String::new()
        };

        Line::from(vec![
            Span::styled(format!("{} ", icon), Style::default().fg(icon_color)),
            Span::styled(format!("{:<16}", ev.worker_id), Style::default().fg(worker_color)),
            Span::styled(format!("{}{}", content_preview, streaming), Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    f.render_widget(List::new(items), area);
}

fn render_briefing_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.briefing_messages.is_empty() {
        let placeholder = Paragraph::new("No active briefing.\nBriefing starts before team execution.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    let items: Vec<ListItem> = state.briefing_messages.iter().map(|msg| {
        let (speaker_style, icon) = if msg.speaker == "system" {
            (Style::default().fg(theme.secondary), "┼")
        } else {
            (Style::default().fg(squad_color(&msg.speaker, theme)), "◆")
        };

        let content_preview = if msg.content.len() > 120 {
            format!("{}...", &msg.content[..117])
        } else {
            msg.content.clone()
        };

        Line::from(vec![
            Span::styled(format!("{} ", icon), Style::default().fg(theme.dim)),
            Span::styled(format!("{:<16}", msg.speaker), speaker_style),
            Span::styled(content_preview, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    f.render_widget(List::new(items), area);
}

fn render_dag_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.dag_nodes.is_empty() {
        let placeholder = Paragraph::new("No task DAG yet.\nDAG builds as tasks are assigned.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    let lines = render_dag_tree(&state.dag_nodes, 0, theme);
    let items: Vec<ListItem> = lines.into_iter().map(ListItem::new).collect();
    f.render_widget(List::new(items), area);
}

fn render_events_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.event_log.is_empty() {
        let placeholder = Paragraph::new("No events yet.")
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
            Span::styled(format!("{} ", ev.timestamp), Style::default().fg(theme.dim)),
            Span::styled(format!("{:<22}", ev.event_type), Style::default().fg(color)),
            Span::styled(&ev.content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    f.render_widget(List::new(items), area);
}

/// Render DAG as ASCII tree with proper ratatui styling (no dead ANSI code)
fn render_dag_tree(nodes: &[crate::state::kantor_state::DagNode], depth: usize, theme: &Theme) -> Vec<Line<'static>> {
    let mut lines = Vec::new();
    for (i, node) in nodes.iter().enumerate() {
        let is_last = i == nodes.len() - 1;
        let prefix = if depth == 0 {
            String::new()
        } else {
            let indent = "│   ".repeat(depth.saturating_sub(1));
            let connector = if is_last { "└── " } else { "├── " };
            format!("{indent}{connector}")
        };

        let (icon, icon_color) = match node.status.as_str() {
            "done" | "completed" => ("✓", theme.green),
            "working" | "in_progress" => ("●", theme.yellow),
            "failed" | "error" => ("✗", theme.red),
            "pending" => ("○", theme.dim),
            _ => ("·", theme.dim),
        };

        let title = if let Some(task_id) = &node.task_id {
            format!("{} ({}…{})", node.title, &node.worker_id, &task_id[..7.min(task_id.len())])
        } else {
            format!("{} ({})", node.title, node.worker_id)
        };

        lines.push(Line::from(vec![
            Span::styled(prefix, Style::default().fg(theme.dim)),
            Span::styled(icon.to_string(), Style::default().fg(icon_color)),
            Span::styled(format!(" {title}"), Style::default().fg(theme.fg)),
        ]));

        if !node.children.is_empty() {
            let child_lines = render_dag_tree(&node.children, depth + 1, theme);
            lines.extend(child_lines);
        }
    }
    lines
}
