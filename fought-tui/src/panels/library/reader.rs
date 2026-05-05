use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, Paragraph, Wrap},
    Frame,
};

use crate::state::library_state::{entry_type_icon, LibraryState};
use crate::ui::components::render_quality_gauge;
use crate::ui::theme::Theme;

/// Render the Reader Panel (right column in Library mode, Browse content mode)
/// Displays full entry content with markdown rendering in terminal
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let Some(entry) = &state.current_entry else {
        // Placeholder when no entry is selected
        let placeholder = Paragraph::new("Pilih entry dari rak buku di sebelah kiri.")
            .style(Style::default().fg(theme.dim))
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(placeholder, area);
        return;
    };

    let icon = entry_type_icon(&entry.entry_type);
    let block = Block::default()
        .title(format!(" {} {} ", icon, entry.title))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Layout: metadata header + quality bar + content + action hints
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),   // Metadata
            Constraint::Length(1),   // Quality bar
            Constraint::Min(0),      // Content
            Constraint::Length(1),   // Action hints
        ])
        .split(inner);

    // Metadata
    let shelf_path = entry.shelf_path.join(" → ");
    let verified_str = if entry.verified { "✓ Verified" } else { "○ Unverified" };
    let meta = format!(
        "{}\n{} | Quality {:.2} | {}x used | {}",
        shelf_path,
        verified_str,
        entry.quality_score,
        entry.usage_count,
        entry.updated_at.chars().take(10).collect::<String>()
    );
    f.render_widget(
        Paragraph::new(meta).style(Style::default().fg(theme.dim)),
        chunks[0],
    );

    // Quality bar
    render_quality_gauge(f, chunks[1], entry.quality_score, theme);

    // Content — simple markdown rendering
    let content_lines = render_markdown_to_lines(&entry.content, chunks[2].width as usize, theme);
    let content = Paragraph::new(content_lines)
        .scroll((state.reader_scroll, 0));
    f.render_widget(content, chunks[2]);

    // Action hints
    let hints = Line::from(vec![
        Span::styled("[h] Helpful ", Style::default().fg(theme.green)),
        Span::styled("[u] Unhelpful ", Style::default().fg(theme.red)),
        Span::styled("[s] Save source ", Style::default().fg(theme.cyan)),
        Span::styled("[r] Related ", Style::default().fg(theme.dim)),
    ]);
    f.render_widget(Paragraph::new(hints), chunks[3]);
}

/// Simple markdown → ratatui Line conversion
/// Supports: # headings, ## sub-headings, ``` code blocks, **bold**, *italic*, `inline code`
fn render_markdown_to_lines(content: &str, _width: usize, theme: &Theme) -> Vec<Line<'static>> {
    let mut lines = Vec::new();
    let mut in_code_block = false;

    for line in content.lines() {
        if line.starts_with("```") {
            in_code_block = !in_code_block;
            let style = Style::default().fg(theme.code_fg).bg(theme.code_bg);
            lines.push(Line::from(Span::styled(line.to_string(), style)));
            continue;
        }

        if in_code_block {
            let style = Style::default().fg(theme.code_fg).bg(theme.code_bg);
            lines.push(Line::from(Span::styled(line.to_string(), style)));
            continue;
        }

        if line.starts_with("# ") {
            lines.push(Line::from(Span::styled(
                line[2..].to_string(),
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD),
            )));
        } else if line.starts_with("## ") {
            lines.push(Line::from(Span::styled(
                line[3..].to_string(),
                Style::default().fg(theme.fg).add_modifier(Modifier::BOLD),
            )));
        } else if line.starts_with("### ") {
            lines.push(Line::from(Span::styled(
                line[4..].to_string(),
                Style::default().fg(theme.fg).add_modifier(Modifier::BOLD),
            )));
        } else if line.starts_with("- ") || line.starts_with("* ") {
            // List items
            lines.push(Line::from(Span::styled(
                format!("  • {}", &line[2..]),
                Style::default().fg(theme.fg),
            )));
        } else {
            // Regular line — parse inline markers
            lines.push(parse_inline_markdown(line, theme));
        }
    }

    lines
}

/// Parse inline markdown markers (bold, italic, code)
fn parse_inline_markdown(line: &str, theme: &Theme) -> Line<'static> {
    // Simple inline parsing: `code`, **bold**
    let mut spans = Vec::new();
    let mut remaining = line;
    let mut in_code = false;

    while !remaining.is_empty() {
        if let Some(pos) = remaining.find('`') {
            if pos > 0 {
                let before = &remaining[..pos];
                if in_code {
                    spans.push(Span::styled(before.to_string(), Style::default().fg(theme.code_fg).bg(theme.code_bg)));
                } else {
                    spans.push(Span::styled(before.to_string(), Style::default().fg(theme.fg)));
                }
            }
            in_code = !in_code;
            remaining = &remaining[pos + 1..];
        } else {
            if in_code {
                spans.push(Span::styled(remaining.to_string(), Style::default().fg(theme.code_fg).bg(theme.code_bg)));
            } else {
                spans.push(Span::styled(remaining.to_string(), Style::default().fg(theme.fg)));
            }
            break;
        }
    }

    Line::from(spans)
}
