use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use crate::state::library_state::LibraryState;
use crate::ui::components::spinner_char;
use crate::ui::theme::Theme;

/// Render the Ask Panel (right column in Library mode, Ask content mode)
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme, tick: u64) {
    let block = Block::default()
        .title(" ARCHIVIST — Ask the Library ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.primary));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.ask_history.is_empty() && state.archivist_streaming.is_empty() {
        let placeholder = Paragraph::new(
            "Ask the Archivist anything.\n\n\
             Answers come exclusively from Library content\n\
             with source attribution for every claim.\n\n\
             Type your question in the input bar below\n\
             and press Enter to send."
        )
        .style(Style::default().fg(theme.dim))
        .wrap(Wrap { trim: true });
        f.render_widget(placeholder, inner);
        return;
    }

    // Layout: chat + streaming + sources
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Min(0),      // Chat history
            Constraint::Length(3),   // Streaming indicator + sources
        ])
        .split(inner);

    // Chat messages
    let visible_count = chunks[0].height as usize;
    let start = state.ask_history.len().saturating_sub(visible_count);
    let messages = &state.ask_history[start..];

    let items: Vec<ListItem> = messages.iter().map(|msg| {
        let (role_style, role_label) = match msg.role.as_str() {
            "user" => (Style::default().fg(theme.accent), "You".to_string()),
            "archivist" => (Style::default().fg(theme.primary), "Archivist".to_string()),
            _ => (Style::default().fg(theme.dim), msg.role.clone()),
        };

        let content = if msg.content.len() > 300 {
            format!("{}...", &msg.content[..297])
        } else {
            msg.content.clone()
        };

        let mut spans = vec![
            Span::styled(format!("{:<12} ", role_label), role_style.add_modifier(Modifier::BOLD)),
            Span::styled(content, Style::default().fg(theme.fg)),
        ];

        // Source count for archivist messages
        if msg.role == "archivist" && !msg.sources.is_empty() {
            spans.push(Span::styled(
                format!(" [{} sources]", msg.sources.len()),
                Style::default().fg(theme.dim),
            ));
        }

        Line::from(spans)
    }).map(ListItem::new).collect();

    f.render_widget(List::new(items), chunks[0]);

    // Streaming indicator + sources
    if !state.archivist_streaming.is_empty() {
        let spinner = spinner_char(tick);
        let streaming_text: String = state.archivist_streaming.iter().take(5).cloned().collect();
        let preview = if streaming_text.len() > 100 {
            format!("{}...", &streaming_text[..97])
        } else {
            streaming_text
        };
        f.render_widget(
            Paragraph::new(format!("{} Archivist is thinking...\n{}", spinner, preview))
                .style(Style::default().fg(theme.yellow)),
            chunks[1],
        );
    } else if !state.archivist_sources.is_empty() {
        let source_items: Vec<Span> = state.archivist_sources.iter().take(3).map(|src| {
            Span::styled(
                format!("{} ({:.0}%)  ", src.title, src.relevance * 100.0),
                Style::default().fg(theme.cyan),
            )
        }).collect();
        f.render_widget(
            Paragraph::new(Line::from(source_items)),
            chunks[1],
        );
    }
}
