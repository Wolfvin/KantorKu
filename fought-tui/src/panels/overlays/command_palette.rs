use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::Line,
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph},
    Frame,
};

use crate::state::AppState;
use crate::ui::theme::Theme;

/// Render the command palette overlay (Ctrl+P)
pub fn render(f: &mut Frame, state: &AppState, theme: &Theme) {
    let area = centered_rect(60, 50, f.area());
    f.render_widget(Clear, area);

    let block = Block::default()
        .title(" Command Palette ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .style(Style::default().bg(theme.bg));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Search query at top
    let query_area = Rect { height: 1, y: inner.y, ..inner };
    let query_line = Line::from(format!("> {}█", state.command_palette_query));
    f.render_widget(
        Paragraph::new(query_line).style(Style::default().fg(theme.fg)),
        query_area,
    );

    // Commands list
    let commands = state.filtered_commands();
    let list_area = Rect {
        y: inner.y + 1,
        height: inner.height.saturating_sub(1),
        ..inner
    };

    let items: Vec<ListItem> = commands.iter().enumerate().map(|(i, cmd)| {
        let is_selected = i == state.command_palette_selection;
        let mode_badge = match cmd.mode {
            crate::state::app_state::CommandMode::Global => "[G]",
            crate::state::app_state::CommandMode::Kantor => "[K]",
            crate::state::app_state::CommandMode::Library => "[L]",
        };
        let style = if is_selected {
            Style::default().fg(theme.bg).bg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.fg)
        };
        ListItem::new(format!("{} {}  {}", mode_badge, cmd.label, cmd.description)).style(style)
    }).collect();

    let list = List::new(items);
    f.render_widget(list, list_area);
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_width = r.width * percent_x / 100;
    let popup_height = r.height * percent_y / 100;
    Rect {
        x: r.x + (r.width.saturating_sub(popup_width)) / 2,
        y: r.y + (r.height.saturating_sub(popup_height)) / 2,
        width: popup_width.min(80),
        height: popup_height.min(30),
    }
}
