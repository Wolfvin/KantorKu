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
            Constraint::Length(2),   // Title
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

    // Title field
    let title_display = if state.ingest_title.is_empty() {
        Paragraph::new("Title: (type to set)").style(Style::default().fg(theme.dim))
    } else {
        Paragraph::new(format!("Title: {}", state.ingest_title))
            .style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD))
    };
    f.render_widget(title_display, chunks[1]);

    // Separator
    f.render_widget(
        Paragraph::new("─".repeat(area.width as usize))
            .style(Style::default().fg(theme.border)),
        chunks[2],
    );

    // Content preview
    let content_display = if state.ingest_content.is_empty() {
        Paragraph::new("Content: Start typing below...")
            .style(Style::default().fg(theme.dim))
    } else {
        Paragraph::new(format!("Content (Markdown):\n{}", state.ingest_content))
            .style(Style::default().fg(theme.fg))
            .wrap(Wrap { trim: false })
    };
    f.render_widget(content_display, chunks[3]);

    // Hints
    let char_count = state.ingest_content.len();
    let can_submit = !state.ingest_title.is_empty() && !state.ingest_content.is_empty();
    let submit_hint = if can_submit { "Enter: Submit" } else { "Fill title and content first" };
    f.render_widget(
        Paragraph::new(format!("{} chars | {} | Esc: Cancel", char_count, submit_hint))
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
        format!("{}...", &state.ingest_content[..397])
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
    let content = format!(
        "✓ Entry ingested successfully!\n\n\
         The entry has been categorized and added to the Library.\n\
         You can find it on the shelf or search for it.\n\n\
         The Knowledge Flywheel is now stronger:\n\
         Workers can find this solution next time they\n\
         encounter a similar problem.\n\n\
         Press Enter to return to browsing."
    );
    f.render_widget(
        Paragraph::new(content)
            .style(Style::default().fg(theme.green))
            .wrap(Wrap { trim: true }),
        area,
    );
}
