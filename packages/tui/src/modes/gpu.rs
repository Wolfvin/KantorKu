/// GPU mode — placeholder for external package connection.
/// See packages/gpu/

use ratatui::Frame;
use ratatui::layout::Rect;
use ratatui::widgets::Paragraph;
use crate::state::app_state::AppState;
use crate::ui::theme::Theme;

pub fn render(f: &mut Frame, area: Rect, _state: &AppState, _theme: &Theme) {
    let msg = "[Mode ini terhubung ke repo eksternal — belum diimplementasi]";
    f.render_widget(Paragraph::new(msg), area);
}
