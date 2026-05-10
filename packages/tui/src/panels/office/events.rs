use ratatui::{
    layout::Rect,
    style::Style,
    text::{Line, Span},
    widgets::{List, ListItem, Paragraph},
    Frame,
};

use crate::state::office_state::OfficeState;
use crate::ui::components::severity_color;
use crate::ui::keybindings::filter_categories;
use crate::ui::theme::Theme;

/// Render the Events Log panel (tab in Workers Live)
pub fn render(f: &mut Frame, area: Rect, state: &OfficeState, theme: &Theme) {
    if state.event_log.is_empty() {
        let placeholder = Paragraph::new("No events logged yet.\n\nUse Alt+4 or Ctrl+Tab to switch to Events tab.\nFilter with /tasks, /errors, /llm, /briefing in the event filter.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    // Filter events if filter is set — use filter_categories for named categories
    let filtered: Vec<&crate::state::office_state::LogEvent> = if let Some(filter) = &state.event_filter {
        state.event_log.iter().filter(|ev| {
            // Check if filter matches a named category first
            if filter_categories::matches(filter, &ev.event_type) {
                return true;
            }
            // Fallback to substring match
            ev.event_type.contains(filter.as_str())
        }).collect()
    } else {
        state.event_log.iter().collect()
    };

    let visible_count = area.height as usize;
    let total = filtered.len();

    // Reverse for display (newest first), apply scroll offset
    let reversed: Vec<&&crate::state::office_state::LogEvent> = filtered.iter().rev().collect();
    let scroll_offset = state.event_scroll.min(total.saturating_sub(visible_count));
    let events: Vec<&&crate::state::office_state::LogEvent> = reversed
        .iter()
        .skip(scroll_offset)
        .take(visible_count)
        .copied()
        .collect();

    let items: Vec<ListItem> = events.iter().map(|ev| {
        let color = severity_color(&ev.severity, theme);
        Line::from(vec![
            Span::styled(format!("{} ", ev.timestamp), Style::default().fg(theme.dim)),
            Span::styled(format!("{:<22}", ev.event_type), Style::default().fg(color)),
            Span::styled(&ev.content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    f.render_widget(List::new(items), area);
}
