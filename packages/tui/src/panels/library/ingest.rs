use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

use crate::state::library_state::{IngestField, IngestStep, LibraryState};
use crate::ui::components::spinner_char;
use crate::ui::theme::Theme;

/// Render the Ingest Panel (right column in Library mode, Ingest content mode)
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme, tick: u64) {
    let block = Block::default()
        .title(" INGEST — Add to Library ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    match state.ingest_step {
        IngestStep::Input => render_input_step(f, inner, state, theme),
        IngestStep::Analyzing => render_analyzing_step(f, inner, theme, tick),
        IngestStep::Confirm => render_confirm_step(f, inner, state, theme),
        IngestStep::Done => render_done_step(f, inner, theme),
    }
}

fn render_input_step(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),   // Instructions
            Constraint::Length(2),   // Title field
            Constraint::Length(1),   // Separator
            Constraint::Min(0),      // Content preview
            Constraint::Length(2),   // Status + hints
        ])
        .split(area);

    // Instructions
    f.render_widget(
        Paragraph::new("Add a new entry to the Library.\nThe Librarian will categorize and assign it to a shelf.")
            .style(Style::default().fg(theme.dim)),
        chunks[0],
    );

    // Title field — show cursor indicator if active
    let title_active = state.ingest_field_active == IngestField::Title;
    let title_cursor = if title_active && state.ingest_title.is_empty() { "█" } else { "" };
    let title_display = if state.ingest_title.is_empty() {
        Paragraph::new(format!("Title: {}(type to set)", title_cursor))
            .style(if title_active { Style::default().fg(theme.accent) } else { Style::default().fg(theme.dim) })
    } else {
        let cursor = if title_active { "█" } else { "" };
        Paragraph::new(format!("Title: {}{}", state.ingest_title, cursor))
            .style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD))
    };
    f.render_widget(title_display, chunks[1]);

    // Separator
    f.render_widget(
        Paragraph::new("─".repeat(area.width as usize))
            .style(Style::default().fg(theme.border)),
        chunks[2],
    );

    // Content preview — show cursor indicator if active
    let content_active = state.ingest_field_active == IngestField::Content;
    let content_display = if state.ingest_content.is_empty() {
        let cursor = if content_active { "█" } else { "" };
        Paragraph::new(format!("Content: {}Start typing below...", cursor))
            .style(if content_active { Style::default().fg(theme.fg) } else { Style::default().fg(theme.dim) })
    } else {
        let cursor = if content_active { "█" } else { "" };
        Paragraph::new(format!("Content (Markdown):\n{}{}", state.ingest_content, cursor))
            .style(Style::default().fg(theme.fg))
            .wrap(Wrap { trim: false })
    };
    f.render_widget(content_display, chunks[3]);

    // Hints
    let char_count = state.ingest_content.len();
    let can_submit = !state.ingest_title.is_empty() && !state.ingest_content.is_empty();
    let field_hint = match state.ingest_field_active {
        IngestField::Title => "Tab: Switch to Content",
        IngestField::Content => if can_submit { "Tab: Switch to Title  Enter: Submit" } else { "Tab: Switch to Title" },
    };
    f.render_widget(
        Paragraph::new(format!("{} chars | {} | Esc: Cancel", char_count, field_hint))
            .style(Style::default().fg(theme.dim)),
        chunks[4],
    );
}

fn render_analyzing_step(f: &mut Frame, area: Rect, theme: &Theme, tick: u64) {
    let spinner = spinner_char(tick);

    let content = format!(
        "{} Analyzing entry...\n\n\
         The Librarian is:\n\
         • Reading and summarizing your content\n\
         • Generating keywords and metadata\n\
         • Determining the best shelf location\n\
         • Calculating quality score\n\n\
         This usually takes a few seconds...",
        spinner
    );
    f.render_widget(
        Paragraph::new(content)
            .style(Style::default().fg(theme.yellow))
            .wrap(Wrap { trim: true }),
        area,
    );
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
    let content_preview = if state.ingest_content.len() > 400 {
        crate::truncate_str(&state.ingest_content, 397)
    } else {
        state.ingest_content.clone()
    };

    let preview = Paragraph::new(vec![
        Line::from(Span::styled(
            format!("Title: {}", state.ingest_title),
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from(Span::styled(content_preview, Style::default().fg(theme.fg))),
        Line::from(""),
        Line::from(Span::styled(
            "─────────────────────────────",
            Style::default().fg(theme.border),
        )),
        Line::from(Span::styled(
            "The Librarian suggests the following classification:",
            Style::default().fg(theme.dim),
        )),
    ])
    .wrap(Wrap { trim: true });
    f.render_widget(preview, chunks[0]);

    // Confirm prompt
    f.render_widget(
        Paragraph::new(vec![
            Line::from(""),
            Line::from(Span::styled(
                "Confirm ingest?  [y] Yes  [n] No",
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD),
            )),
        ]),
        chunks[1],
    );
}

fn render_done_step(f: &mut Frame, area: Rect, theme: &Theme) {
    let content = "✓ Entry ingested successfully!\n\n\
         The entry has been categorized and added to the Library.\n\
         You can find it on the shelf or search for it.\n\n\
         The Knowledge Flywheel is now stronger:\n\
         Workers can find this solution next time they\n\
         encounter a similar problem.\n\n\
         Press Enter to return to browsing.".to_string();
    f.render_widget(
        Paragraph::new(content)
            .style(Style::default().fg(theme.green))
            .wrap(Wrap { trim: true }),
        area,
    );
}
