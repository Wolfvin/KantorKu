use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::components::severity_color;
use crate::ui::theme::Theme;

/// Render the Events Log panel (tab in Workers Live middle panel)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .title("EVENTS")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.event_log.is_empty() {
        let placeholder = Paragraph::new("No events yet.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, inner);
        return;
    }

    // Filter events if filter is set
    let filtered: Vec<&crate::state::kantor_state::LogEvent> = if let Some(filter) = &state.event_filter {
        state.event_log.iter().filter(|ev| ev.event_type.contains(filter.as_str())).collect()
    } else {
        state.event_log.iter().collect()
    };

    let visible_count = inner.height as usize;
    let events: Vec<&&crate::state::kantor_state::LogEvent> = filtered.iter().rev().take(visible_count).collect();

    let items: Vec<ListItem> = events.iter().map(|ev| {
        let color = severity_color(&ev.severity, theme);
        Line::from(vec![
            Span::styled(format!("{:<25} ", ev.event_type), Style::default().fg(color)),
            Span::styled(&ev.content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, inner);
}
