use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, Paragraph, Wrap},
    Frame,
};

use crate::state::library_state::{entry_type_icon, LibraryState};
use crate::ui::components::{quality_color, render_quality_gauge};
use crate::ui::theme::Theme;

/// Render the Reader Panel (right column in Library mode, Browse content mode)
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme, _tick: u64) {
    let Some(entry) = &state.current_entry else {
        let placeholder = Paragraph::new(
            "Pilih entry dari rak buku di sebelah kiri.\n\n\
             Navigate with ↑↓, expand shelves with Enter/→,\n\
             go back with ←/Backspace."
        )
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

    // Layout: metadata + quality + keywords + content + actions
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),   // Metadata
            Constraint::Length(1),   // Quality bar
            Constraint::Length(1),   // Keywords
            Constraint::Min(0),      // Content
            Constraint::Length(1),   // Action hints
        ])
        .split(inner);

    // Metadata
    let shelf_path = if entry.shelf_path.is_empty() { "Uncategorized".to_string() } else { entry.shelf_path.join(" → ") };
    let verified_str = if entry.verified { "✓ Verified" } else { "○ Unverified" };
    let source_str = match entry.source.as_str() {
        "manual" => "Manual",
        "kantorku" => "KantorKu",
        "import" => "Import",
        "archivist" => "Archivist",
        _ => &entry.source,
    };
    let meta = format!(
        "{}\n{} | {} | {}x used | {} | {}",
        shelf_path,
        verified_str,
        source_str,
        entry.usage_count,
        entry.updated_at.chars().take(10).collect::<String>(),
        entry.lang,
    );
    f.render_widget(
        Paragraph::new(meta).style(Style::default().fg(theme.dim)),
        chunks[0],
    );

    // Quality bar
    render_quality_gauge(f, chunks[1], entry.quality_score, theme);

    // Keywords
    if !entry.keywords.is_empty() {
        let keywords = entry.keywords.iter().map(|k| format!("#{k}")).collect::<Vec<_>>().join(" ");
        f.render_widget(
            Paragraph::new(keywords).style(Style::default().fg(theme.cyan)),
            chunks[2],
        );
    } else {
        f.render_widget(
            Paragraph::new("No keywords").style(Style::default().fg(theme.dim)),
            chunks[2],
        );
    }

    // Content — markdown rendering
    let content_lines = render_markdown(&entry.content, chunks[3].width as usize, theme);
    let content = Paragraph::new(content_lines)
        .scroll((state.reader_scroll, 0));
    f.render_widget(content, chunks[3]);

    // Action hints
    let hints = Line::from(vec![
        Span::styled("[h] Helpful ", Style::default().fg(theme.green)),
        Span::styled("[u] Unhelpful ", Style::default().fg(theme.red)),
        Span::styled("[r] Related ", Style::default().fg(theme.cyan)),
        Span::styled("[a] Ask about this ", Style::default().fg(theme.dim)),
    ]);
    f.render_widget(Paragraph::new(hints), chunks[4]);
}

/// Simple markdown → ratatui Line conversion
fn render_markdown(content: &str, _width: usize, theme: &Theme) -> Vec<Line<'static>> {
    let mut lines = Vec::new();
    let mut in_code_block = false;

    for raw_line in content.lines() {
        if raw_line.starts_with("```") {
            in_code_block = !in_code_block;
            lines.push(Line::from(Span::styled(
                raw_line.to_string(),
                Style::default().fg(theme.code_fg).bg(theme.code_bg),
            )));
            continue;
        }

        if in_code_block {
            lines.push(Line::from(Span::styled(
                raw_line.to_string(),
                Style::default().fg(theme.code_fg).bg(theme.code_bg),
            )));
            continue;
        }

        if raw_line.starts_with("# ") {
            lines.push(Line::from(Span::styled(
                raw_line[2..].to_string(),
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD),
            )));
        } else if raw_line.starts_with("## ") {
            lines.push(Line::from(Span::styled(
                raw_line[3..].to_string(),
                Style::default().fg(theme.fg).add_modifier(Modifier::BOLD),
            )));
        } else if raw_line.starts_with("### ") {
            lines.push(Line::from(Span::styled(
                raw_line[4..].to_string(),
                Style::default().fg(theme.fg).add_modifier(Modifier::BOLD),
            )));
        } else if raw_line.starts_with("- ") || raw_line.starts_with("* ") {
            lines.push(Line::from(Span::styled(
                format!("  • {}", &raw_line[2..]),
                Style::default().fg(theme.fg),
            )));
        } else if raw_line.starts_with("> ") {
            lines.push(Line::from(Span::styled(
                format!("  │ {}", &raw_line[2..]),
                Style::default().fg(theme.dim),
            )));
        } else if raw_line.trim().is_empty() {
            lines.push(Line::from(""));
        } else {
            lines.push(parse_inline(raw_line, theme));
        }
    }

    lines
}

/// Parse inline markdown markers
fn parse_inline(line: &str, theme: &Theme) -> Line<'static> {
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
                // Handle **bold** markers simply
                spans.push(Span::styled(remaining.to_string(), Style::default().fg(theme.fg)));
            }
            break;
        }
    }

    if spans.is_empty() {
        spans.push(Span::raw(""));
    }
    Line::from(spans)
}
