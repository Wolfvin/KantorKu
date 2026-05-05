use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::theme::Theme;

/// Render the Manager Chat panel (right column in Kantor mode)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .title("MANAGER")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.manager_messages.is_empty() {
        let placeholder = Paragraph::new("Waiting for Manager...")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, inner);
        return;
    }

    // Layout: messages + hints
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Min(0),      // Messages
            Constraint::Length(1),   // Hints
        ])
        .split(inner);

    // Render messages
    let items: Vec<ListItem> = state.manager_messages.iter().map(|msg| {
        let (role_style, role_label) = match msg.role.as_str() {
            "user" => (Style::default().fg(theme.accent), "> You".to_string()),
            "manager" => (Style::default().fg(theme.primary), "Manager".to_string()),
            "manager_brainstorm" => (Style::default().fg(theme.secondary), "Thinking".to_string()),
            _ => (Style::default().fg(theme.dim), msg.role.clone()),
        };

        // Truncate content for display
        let content = if msg.content.len() > 200 {
            format!("{}...", &msg.content[..197])
        } else {
            msg.content.clone()
        };

        Line::from(vec![
            Span::styled(format!("{:<10} ", role_label), role_style.add_modifier(Modifier::BOLD)),
            Span::styled(content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, chunks[0]);

    // Hints
    let hints = if state.contract_state == "contract_presented" {
        "Ctrl+A: Accept  Ctrl+R: Revise  Ctrl+I: Disrupt"
    } else {
        "Enter: Send  Ctrl+M: Multi-line  Ctrl+L: Clear"
    };
    let hint_line = Paragraph::new(hints)
        .style(Style::default().fg(theme.dim));
    f.render_widget(hint_line, chunks[1]);
}
