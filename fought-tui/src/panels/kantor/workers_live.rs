use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Tabs},
    Frame,
};

use crate::state::kantor_state::{KantorState, WorkersTab};
use crate::ui::components::{squad_color, spinner_char, phase_label, worker_status_icon};
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

    // Phase indicator — reuse phase_label from components
    let (phase_text, phase_color_name) = phase_label(state.contract_state.as_str());
    let phase_color = match phase_color_name {
        "dim" => theme.dim,
        "yellow" => theme.yellow,
        "secondary" => theme.secondary,
        "green" | "success" => theme.success,
        "blue" | "info" => theme.info,
        "red" | "error" => theme.error,
        "warning" => theme.warning,
        _ => theme.dim,
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

    // Tab content — delegate to standalone panel modules
    match state.active_tab {
        WorkersTab::Workers => render_workers_tab(f, chunks[2], state, theme, tick),
        WorkersTab::Briefing => crate::panels::kantor::briefing::render(f, chunks[2], state, theme),
        WorkersTab::Dag => crate::panels::kantor::dag::render(f, chunks[2], state, theme),
        WorkersTab::Events => crate::panels::kantor::events::render(f, chunks[2], state, theme),
    }
}

fn render_workers_tab(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme, tick: u64) {
    // Split into: worker roster (top 40%) + event stream (bottom 60%)
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
        .split(area);

    // Worker roster — show each worker with status icon
    let roster_items: Vec<ListItem> = state.workers_list.iter().map(|worker_id| {
        let status = if state.llm_streaming_worker.as_deref() == Some(worker_id) {
            "working"
        } else {
            "idle"
        };
        let icon = worker_status_icon(status);
        let color = squad_color(worker_id, theme);
        let streaming = if status == "working" {
            format!(" {}", spinner_char(tick))
        } else {
            String::new()
        };
        Line::from(vec![
            Span::styled(format!("{} ", icon), Style::default().fg(if status == "working" { theme.yellow } else { theme.dim })),
            Span::styled(format!("{:<20}", worker_id), Style::default().fg(color)),
            Span::styled(format!("{}{}", status, streaming), Style::default().fg(theme.dim)),
        ])
    }).map(ListItem::new).collect();

    let roster_area = if !roster_items.is_empty() {
        f.render_widget(
            List::new(roster_items).block(Block::default().title("Roster").borders(Borders::NONE)),
            chunks[0],
        );
        chunks[1]
    } else {
        chunks[1]
    };

    // Event stream
    let visible_count = roster_area.height as usize;
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
            crate::truncate_str(&ev.content, 77)
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

    f.render_widget(List::new(items), roster_area);
}
