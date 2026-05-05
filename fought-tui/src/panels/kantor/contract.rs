use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::{ContractState, KantorState};
use crate::ui::components::{contract_state_color, render_progress};
use crate::ui::theme::Theme;

/// Render the Contract panel (left column in Kantor mode)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let state_str = state.contract_state.as_str();
    let state_color = contract_state_color(state_str, theme);
    let block = Block::default()
        .title(format!(" CONTRACT [{}] ", state_str.to_uppercase()))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(state_color));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Layout: contract info + progress + todos
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),   // Contract title + description
            Constraint::Length(1),   // Progress bar
            Constraint::Length(1),   // Workers list
            Constraint::Min(0),      // Todo list
            Constraint::Length(1),   // Action hints
        ])
        .split(inner);

    // Title
    let title = if let Some(contract) = &state.pending_contract {
        contract.title.clone()
    } else {
        "No active contract".to_string()
    };
    let desc = if let Some(contract) = &state.pending_contract {
        if contract.description.len() > 80 {
            format!("{}...", &contract.description[..77])
        } else {
            contract.description.clone()
        }
    } else {
        "Send a message to the Manager to start.".to_string()
    };

    let title_widget = Paragraph::new(vec![
        Line::from(Span::styled(title, Style::default().fg(theme.fg).add_modifier(Modifier::BOLD))),
        Line::from(Span::styled(desc, Style::default().fg(theme.dim))),
    ]);
    f.render_widget(title_widget, chunks[0]);

    // Progress bar
    let done = state.todos.iter().filter(|t| t.done).count();
    let total = state.todos.len();
    render_progress(f, chunks[1], done, total, state_color);

    // Workers list (if contract has workers)
    if let Some(contract) = &state.pending_contract {
        let workers_str = contract.workers.join(" · ");
        let workers_line = Paragraph::new(workers_str)
            .style(Style::default().fg(theme.cyan));
        f.render_widget(workers_line, chunks[2]);
    }

    // Todo list
    let items: Vec<ListItem> = state.todos.iter().map(|todo| {
        let (prefix, style) = if todo.done {
            ("✓", Style::default().fg(theme.green).add_modifier(Modifier::DIM))
        } else {
            ("○", Style::default().fg(theme.fg))
        };
        let mut text = format!("{} {}", prefix, todo.title);
        if let Some(worker) = &todo.worker_id {
            text = format!("{} {}  ({})", prefix, todo.title, worker);
        }
        ListItem::new(text).style(style)
    }).collect();

    let list = List::new(items);
    f.render_widget(list, chunks[3]);

    // Action hints — using ContractState enum
    let hints = match state.contract_state {
        ContractState::ContractPresented => "Ctrl+A: Accept  Ctrl+R: Revise  Ctrl+I: Disrupt",
        ContractState::Working => "Ctrl+I: Disrupt",
        _ => "",
    };
    if !hints.is_empty() {
        let hint = Paragraph::new(hints)
            .style(Style::default().fg(theme.dim));
        f.render_widget(hint, chunks[4]);
    }
}
