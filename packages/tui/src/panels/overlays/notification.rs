use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::Line,
    widgets::{Clear, Paragraph},
    Frame,
};

use crate::state::app_state::NotificationSeverity;
use crate::ui::theme::Theme;

/// Render a toast notification at the bottom-center of the screen
pub fn render(f: &mut Frame, message: &str, severity: NotificationSeverity, theme: &Theme) {
    let area = f.area();
    let width = (message.len() + 4).min(area.width as usize - 4) as u16;
    let height = 1u16;
    let x = area.x + (area.width.saturating_sub(width)) / 2;
    let y = area.y + area.height.saturating_sub(2);

    let toast_area = Rect { x, y, width, height };
    f.render_widget(Clear, toast_area);

    let color = match severity {
        NotificationSeverity::Info => theme.info,
        NotificationSeverity::Warning => theme.warning,
        NotificationSeverity::Error => theme.error,
    };

    let line = Line::from(format!(" {} ", message));
    f.render_widget(
        Paragraph::new(line).style(Style::default().fg(theme.bg).bg(color).add_modifier(Modifier::BOLD)),
        toast_area,
    );
}
