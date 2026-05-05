use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, Paragraph},
    Frame,
};

use super::theme::Theme;

/// Render a spinner character based on tick count
/// Uses braille spinner: ⣾⣽⣻⢿⡿⣟⣯⣷
pub fn spinner_char(tick: u64) -> char {
    const BRAILLE: &[char] = &['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];
    BRAILLE[(tick % 8) as usize]
}

/// Render a status bar at the top of the screen
pub fn render_status_bar(
    f: &mut Frame,
    area: Rect,
    mode_label: &str,
    mode_color: ratatui::style::Color,
    session_info: &str,
    right_text: &str,
    theme: &Theme,
) {
    let left = format!(" ⚡ Fought [{}]  {}", mode_label, session_info);
    let spacing = (area.width as usize).saturating_sub(left.len()).saturating_sub(right_text.len());
    let line = Line::from(vec![
        Span::styled(left, Style::default().fg(mode_color).add_modifier(Modifier::BOLD)),
        Span::raw(" ".repeat(spacing)),
        Span::styled(right_text.to_string(), Style::default().fg(theme.dim)),
    ]);
    f.render_widget(Paragraph::new(line), area);
}

/// Render an input bar at the bottom of the screen
pub fn render_input_bar(
    f: &mut Frame,
    area: Rect,
    input_text: &str,
    cursor_pos: usize,
    hint: &str,
    theme: &Theme,
) {
    let block = Block::default()
        .borders(Borders::TOP)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    let prompt = Span::styled("> ", Style::default().fg(theme.accent));
    let input = Span::styled(input_text, Style::default().fg(theme.fg));
    let cursor = Span::styled("█", Style::default().fg(theme.accent));
    let hint_span = Span::styled(format!("  {hint}"), Style::default().fg(theme.dim));

    let line = Line::from(vec![prompt, input, cursor, hint_span]);
    f.render_widget(Paragraph::new(line), inner);
}

/// Render a quality gauge bar
pub fn render_quality_gauge(
    f: &mut Frame,
    area: Rect,
    quality: f32,
    theme: &Theme,
) {
    let color = if quality >= 0.7 {
        theme.green
    } else if quality >= 0.4 {
        theme.yellow
    } else {
        theme.red
    };

    let gauge = Gauge::default()
        .ratio(quality as f64)
        .gauge_style(Style::default().fg(color))
        .label(format!("Quality: {:.0}%", quality * 100.0));
    f.render_widget(gauge, area);
}

/// Render a progress gauge
pub fn render_progress(
    f: &mut Frame,
    area: Rect,
    done: usize,
    total: usize,
    color: ratatui::style::Color,
) {
    let ratio = if total > 0 {
        done as f64 / total as f64
    } else {
        0.0
    };
    let gauge = Gauge::default()
        .ratio(ratio)
        .gauge_style(Style::default().fg(color))
        .label(format!("{}/{}", done, total));
    f.render_widget(gauge, area);
}

/// Contract state color mapping
pub fn contract_state_color(state: &str, theme: &Theme) -> ratatui::style::Color {
    match state {
        "working" | "in_progress" => theme.yellow,
        "done" | "completed" => theme.green,
        "contract_presented" => theme.cyan,
        "team_review" => theme.secondary,
        "accepted" => theme.green,
        "failed" | "error" => theme.red,
        "manager_thinking" | "clarifying" => theme.yellow,
        "awaiting_revision" => theme.warning,
        "verifying" => theme.secondary,
        _ => theme.dim,
    }
}

/// Worker status icon
pub fn worker_status_icon(status: &str) -> &'static str {
    match status {
        "idle" => "○",
        "thinking" | "in_progress" => "◐",
        "active" | "working" => "●",
        "done" | "completed" => "✓",
        "failed" | "error" => "✗",
        "pending" => "○",
        _ => "·",
    }
}

/// Task state icon
pub fn task_state_icon(state: &str) -> &'static str {
    match state {
        "pending" | "queued" => "○",
        "in_progress" => "◐",
        "completed" | "done" => "✓",
        "failed" => "✗",
        "retrying" => "↻",
        "cancelled" => "⊘",
        _ => "·",
    }
}

/// Severity color
pub fn severity_color(severity: &str, theme: &Theme) -> ratatui::style::Color {
    match severity {
        "info" => theme.info,
        "warning" => theme.warning,
        "critical" | "error" => theme.error,
        _ => theme.dim,
    }
}
