use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::components::squad_color;
use crate::ui::theme::Theme;

/// Render the Briefing panel (tab in Workers Live)
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if !state.briefing_active && state.briefing_messages.is_empty() {
        let placeholder = Paragraph::new(
            "No active briefing.\n\nBriefing starts when the Conductor opens a BriefingRoom\nbefore execution. Workers discuss the plan here."
        )
        .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    // Header showing briefing workers
    if state.briefing_active && !state.briefing_workers.is_empty() {
        let workers_str = state.briefing_workers.join(", ");
        let header = Paragraph::new(format!("Briefing: {workers_str}"))
            .style(Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD));
        let header_area = Rect { height: 1, ..area };
        f.render_widget(header, header_area);

        let rest_area = Rect { y: area.y + 1, height: area.height.saturating_sub(1), ..area };
        render_messages(f, rest_area, state, theme);
    } else {
        render_messages(f, area, state, theme);
    }
}

fn render_messages(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let items: Vec<ListItem> = state.briefing_messages.iter().map(|msg| {
        let (speaker_style, icon) = if msg.speaker == "system" {
            (Style::default().fg(theme.secondary), "┼")
        } else {
            (Style::default().fg(squad_color(&msg.speaker, theme)), "💬")
        };

        let content_preview = if msg.content.len() > 150 {
            format!("{}...", &msg.content[..147])
        } else {
            msg.content.clone()
        };

        Line::from(vec![
            Span::styled(format!("{} ", icon), Style::default().fg(theme.dim)),
            Span::styled(format!("{:<16}", msg.speaker), speaker_style),
            Span::styled(content_preview, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    f.render_widget(List::new(items), area);
}
