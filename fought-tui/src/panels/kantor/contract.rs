use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::components::{contract_state_color, render_progress};
use crate::ui::theme::Theme;

/// Render the Contract panel (left column in Kantor mode)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .title("CONTRACT")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Layout: title + state + progress + todo list
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),   // Title + state badge
            Constraint::Length(1),   // Progress bar
            Constraint::Min(0),      // Todo list
        ])
        .split(inner);

    // Title and state
    let state_color = contract_state_color(&state.contract_state, theme);
    let state_label = format!("[{}]", state.contract_state.to_uppercase());

    let title = if let Some(contract) = &state.pending_contract {
        contract.title.clone()
    } else {
        "No active contract".to_string()
    };

    let header = Line::from(vec![
        Span::styled(title, Style::default().fg(theme.fg).add_modifier(Modifier::BOLD)),
        Span::raw("  "),
        Span::styled(state_label, Style::default().fg(state_color).add_modifier(Modifier::BOLD)),
    ]);
    f.render_widget(Paragraph::new(header), chunks[0]);

    // Progress bar
    let done = state.todos.iter().filter(|t| t.done).count();
    let total = state.todos.len();
    render_progress(f, chunks[1], done, total, state_color);

    // Todo list
    let items: Vec<ListItem> = state.todos.iter().map(|todo| {
        let prefix = if todo.done { "✓ " } else { "○ " };
        let style = if todo.done {
            Style::default().fg(theme.green).add_modifier(Modifier::DIM)
        } else {
            Style::default().fg(theme.fg)
        };

        let mut text = format!("{}{}", prefix, todo.title);
        if let Some(worker) = &todo.worker_id {
            text = format!("{}{}  ({})", prefix, todo.title, worker);
        }
        ListItem::new(text).style(style)
    }).collect();

    let list = List::new(items);
    f.render_widget(list, chunks[2]);
}
