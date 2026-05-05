use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::theme::Theme;

/// Render the Briefing panel (tab in Workers Live middle panel)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .title("BRIEFING")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.briefing_messages.is_empty() {
        let placeholder = Paragraph::new("No active briefing.\nBriefing starts before team execution.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, inner);
        return;
    }

    let items: Vec<ListItem> = state.briefing_messages.iter().map(|msg| {
        let (worker_style, icon) = (Style::default().fg(theme.cyan), "💬");
        Line::from(vec![
            Span::styled(format!("{icon} "), Style::default().fg(theme.dim)),
            Span::styled(format!("{:<15} ", msg.worker_id), worker_style),
            Span::styled(&msg.content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, inner);
}
