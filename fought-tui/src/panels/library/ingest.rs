use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

use crate::state::library_state::{IngestStep, LibraryState};
use crate::ui::components::spinner_char;
use crate::ui::theme::Theme;

/// Render the Ingest Panel (right column in Library mode, Ingest content mode)
/// Interface for adding new entries to the Library
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let block = Block::default()
        .title("INGEST — Add to Library")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    match state.ingest_step {
        IngestStep::Input => render_input_step(f, inner, state, theme),
        IngestStep::Analyzing => render_analyzing_step(f, inner, state, theme),
        IngestStep::Confirm => render_confirm_step(f, inner, state, theme),
        IngestStep::Done => render_done_step(f, inner, state, theme),
    }
}

fn render_input_step(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),   // Title input
            Constraint::Length(1),   // Separator
            Constraint::Min(0),      // Content input
            Constraint::Length(1),   // Hints
        ])
        .split(area);

    // Title
    let title_label = Paragraph::new("Title:")
        .style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));
    f.render_widget(title_label, chunks[0]);

    let title_value = if state.ingest_title.is_empty() {
        Paragraph::new("(type title here)")
            .style(Style::default().fg(theme.dim))
    } else {
        Paragraph::new(state.ingest_title.as_str())
            .style(Style::default().fg(theme.fg))
    };
    f.render_widget(title_value, chunks[0]); // Overwrite for simplicity

    // Separator
    let sep = Paragraph::new("─".repeat(area.width as usize))
        .style(Style::default().fg(theme.border));
    f.render_widget(sep, chunks[1]);

    // Content
    let content_label = Paragraph::new("Content (Markdown):")
        .style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));
    f.render_widget(content_label, chunks[2]);

    // Hints
    let hints = Paragraph::new("Enter: Submit  Esc: Cancel")
        .style(Style::default().fg(theme.dim));
    f.render_widget(hints, chunks[3]);
}

fn render_analyzing_step(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let spinner = spinner_char(0); // Will be dynamic in real impl with tick

    let analyzing = Paragraph::new(format!(
        "{} Analyzing entry...\n\n\
         The Librarian is categorizing your entry,\n\
         generating metadata, and assigning to a shelf.",
        spinner
    ))
    .style(Style::default().fg(theme.yellow))
    .wrap(Wrap { trim: true });
    f.render_widget(analyzing, area);
}

fn render_confirm_step(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Min(0),      // Preview
            Constraint::Length(3),   // Confirm prompt
        ])
        .split(area);

    // Preview
    let preview = Paragraph::new(format!(
        "Title: {}\n\n{}\n\n\
         ─────────────────────────────\n\
         The Librarian suggests the following:",
        state.ingest_title,
        if state.ingest_content.len() > 200 {
            format!("{}...", &state.ingest_content[..197])
        } else {
            state.ingest_content.clone()
        }
    ))
    .style(Style::default().fg(theme.fg))
    .wrap(Wrap { trim: true });
    f.render_widget(preview, chunks[0]);

    // Confirm prompt
    let prompt = Paragraph::new("Confirm ingest? [y/n]")
        .style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));
    f.render_widget(prompt, chunks[1]);
}

fn render_done_step(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let done = Paragraph::new(
        "✓ Entry ingested successfully!\n\n\
         The entry has been categorized and added to the Library.\n\
         You can find it on the shelf or search for it.\n\n\
         Press Enter to return to browsing."
    )
    .style(Style::default().fg(theme.green))
    .wrap(Wrap { trim: true });
    f.render_widget(done, area);
}
