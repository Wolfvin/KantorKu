use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use crate::state::kantor_state::{ContractState, KantorState};
use crate::ui::theme::Theme;

/// Render the Manager Chat panel (right column in Kantor mode)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .title(" MANAGER ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.primary));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.manager_messages.is_empty() {
        let placeholder = Paragraph::new(
            "Waiting for Manager...\n\nSend a message to start a session."
        )
        .style(Style::default().fg(theme.dim))
        .wrap(Wrap { trim: true });
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

    // Render messages — show most recent N that fit
    let visible_count = chunks[0].height as usize;
    let messages: Vec<_> = state.manager_messages.iter().collect();
    let start = messages.len().saturating_sub(visible_count);
    let visible = &messages[start..];

    let items: Vec<ListItem> = visible.iter().map(|msg| {
        let (role_style, role_label) = match msg.role.as_str() {
            "user" => (Style::default().fg(theme.accent), "You".to_string()),
            "manager" => (Style::default().fg(theme.primary), "Manager".to_string()),
            "thinking" => (Style::default().fg(theme.secondary), "Thinking".to_string()),
            "system" => (Style::default().fg(theme.info), "System".to_string()),
            _ => (Style::default().fg(theme.dim), msg.role.clone()),
        };

        let content = if msg.content.len() > 300 {
            format!("{}...", &msg.content[..297])
        } else {
            msg.content.clone()
        };

        let label = format!("{:<10} ", role_label);
        Line::from(vec![
            Span::styled(label, role_style.add_modifier(Modifier::BOLD)),
            Span::styled(content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, chunks[0]);

    // Hints — using ContractState enum
    let hints = match state.contract_state {
        ContractState::ContractPresented => "Ctrl+A: Accept  Ctrl+R: Revise  Ctrl+I: Disrupt",
        ContractState::Working => "Ctrl+I: Disrupt  Ctrl+M: Multi-line",
        _ => "Enter: Send  Ctrl+M: Multi-line  Ctrl+L: Clear",
    };
    f.render_widget(
        Paragraph::new(hints).style(Style::default().fg(theme.dim)),
        chunks[1],
    );
}
