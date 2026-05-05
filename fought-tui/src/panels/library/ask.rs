use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use crate::state::library_state::{entry_type_icon, LibraryState};
use crate::ui::theme::Theme;

/// Render the Ask Panel (right column in Library mode, Ask content mode)
/// Chat interface with the Archivist AI
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let block = Block::default()
        .title("ARCHIVIST — Ask the Library")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.ask_history.is_empty() {
        let placeholder = Paragraph::new(
            "Ask the Archivist anything.\n\
             Answers come exclusively from Library content with source attribution.\n\n\
             Type your question in the input bar below and press Enter."
        )
        .style(Style::default().fg(theme.dim))
        .wrap(Wrap { trim: true });
        f.render_widget(placeholder, inner);
        return;
    }

    // Layout: chat messages + sources
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Min(0),      // Chat messages
            Constraint::Length(4),   // Sources
        ])
        .split(inner);

    // Render chat messages
    let items: Vec<ListItem> = state.ask_history.iter().map(|msg| {
        let (role_style, role_label) = match msg.role.as_str() {
            "user" => (Style::default().fg(theme.accent), "> You".to_string()),
            "archivist" => (Style::default().fg(theme.primary), "📚 Archivist".to_string()),
            _ => (Style::default().fg(theme.dim), msg.role.clone()),
        };

        let content = if msg.content.len() > 150 {
            format!("{}...", &msg.content[..147])
        } else {
            msg.content.clone()
        };

        Line::from(vec![
            Span::styled(format!("{:<15} ", role_label), role_style.add_modifier(Modifier::BOLD)),
            Span::styled(content, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items);
    f.render_widget(list, chunks[0]);

    // Render sources
    if !state.archivist_sources.is_empty() {
        let source_items: Vec<ListItem> = state.archivist_sources.iter().map(|src| {
            let icon = entry_type_icon(""); // Generic
            Line::from(vec![
                Span::styled(format!("{} ", icon), Style::default().fg(theme.dim)),
                Span::styled(&src.title, Style::default().fg(theme.cyan)),
                Span::styled(format!(" ({:.0}%)", src.relevance * 100.0), Style::default().fg(theme.dim)),
            ])
        }).map(ListItem::new).collect();

        let source_list = List::new(source_items)
            .block(Block::default()
                .title("Sources")
                .borders(Borders::TOP)
                .border_style(Style::default().fg(theme.border)));
        f.render_widget(source_list, chunks[1]);
    }
}
