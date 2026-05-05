use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, Paragraph},
    Frame,
};

use super::theme::Theme;

/// Braille spinner frames
const BRAILLE: &[char] = &['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];

/// Get spinner character for a given tick
pub fn spinner_char(tick: u64) -> char {
    BRAILLE[(tick % 8) as usize]
}

/// Render the top status bar
pub fn render_status_bar(
    f: &mut Frame,
    area: Rect,
    _mode_label: &str,
    mode_color: ratatui::style::Color,
    left_content: &str,
    right_content: &str,
    theme: &Theme,
) {
    let spacing_len = (area.width as usize).saturating_sub(left_content.len()).saturating_sub(right_content.len());
    let line = Line::from(vec![
        Span::styled(left_content.to_string(), Style::default().fg(mode_color).add_modifier(Modifier::BOLD)),
        Span::raw(" ".repeat(spacing_len)),
        Span::styled(right_content.to_string(), Style::default().fg(theme.dim)),
    ]);
    f.render_widget(Paragraph::new(line), area);
}

/// Render the bottom input bar
pub fn render_input_bar(
    f: &mut Frame,
    area: Rect,
    input_text: &str,
    hint: &str,
    theme: &Theme,
) {
    let block = Block::default()
        .borders(Borders::TOP)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    let prompt = Span::styled("> ", Style::default().fg(theme.accent));
    let input = Span::styled(input_text.to_string(), Style::default().fg(theme.fg));
    let cursor = Span::styled("█", Style::default().fg(theme.accent).add_modifier(Modifier::SLOW_BLINK));
    let hint_span = Span::styled(format!("  {hint}"), Style::default().fg(theme.dim));

    let line = Line::from(vec![prompt, input, cursor, hint_span]);
    f.render_widget(Paragraph::new(line), inner);
}

/// Render a quality gauge bar
pub fn render_quality_gauge(f: &mut Frame, area: Rect, quality: f32, theme: &Theme) {
    let color = quality_color(quality, theme);
    let gauge = Gauge::default()
        .ratio(quality as f64)
        .gauge_style(Style::default().fg(color))
        .label(format!("Quality: {:.0}%", quality * 100.0));
    f.render_widget(gauge, area);
}

/// Render a progress gauge
pub fn render_progress(f: &mut Frame, area: Rect, done: usize, total: usize, color: ratatui::style::Color) {
    let ratio = if total > 0 { done as f64 / total as f64 } else { 0.0 };
    let gauge = Gauge::default()
        .ratio(ratio)
        .gauge_style(Style::default().fg(color))
        .label(format!("{}/{}", done, total));
    f.render_widget(gauge, area);
}

/// Quality score → color mapping
pub fn quality_color(quality: f32, theme: &Theme) -> ratatui::style::Color {
    if quality >= 0.7 { theme.green }
    else if quality >= 0.4 { theme.yellow }
    else { theme.red }
}

/// Contract state → color mapping (matching Python CONTRACT_STATE_COLORS)
pub fn contract_state_color(state: &str, theme: &Theme) -> ratatui::style::Color {
    match state {
        "working" | "in_progress" => theme.yellow,
        "done" | "completed" => theme.green,
        "contract_presented" | "proposed" => theme.cyan,
        "team_review" => theme.secondary,
        "accepted" => theme.success,
        "failed" | "error" => theme.error,
        "manager_thinking" | "clarifying" | "drafting" | "negotiating" => theme.yellow,
        "awaiting_revision" => theme.warning,
        "verifying" => theme.secondary,
        "todo_review" | "client_feedback" => theme.info,
        _ => theme.dim,
    }
}

/// Worker status icon (matching Python STATUS_ICONS)
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

/// Task state icon (matching Python TASK_STATE_ICONS)
pub fn task_state_icon(state: &str) -> &'static str {
    match state {
        "pending" | "queued" => "○",
        "in_progress" => "◐",
        "completed" | "done" => "✓",
        "failed" => "✗",
        "retrying" => "↻",
        "cancelled" => "⊘",
        "dead_letter" => "☠",
        _ => "·",
    }
}

/// Phase label for WorkersLive (matching Python WORKERS_PHASE_STYLES)
pub fn phase_label(contract_state: &str) -> (&'static str, &'static str) {
    match contract_state {
        "idle" => ("dim", "○ IDLE"),
        "manager_thinking" | "clarifying" | "contract_presented" | "awaiting_revision" => ("yellow bold", "◐ NEGOTIATING"),
        "team_review" | "todo_review" => ("magenta bold", "┼ BRIEFING"),
        "working" | "accepted" => ("green bold", "⚡ EXECUTING"),
        "verifying" => ("blue bold", "◇ VERIFYING"),
        "done" => ("green", "✓ COMPLETE"),
        "failed" => ("red bold", "✗ FAILED"),
        _ => ("dim", "○ IDLE"),
    }
}

/// Severity → color
pub fn severity_color(severity: &str, theme: &Theme) -> ratatui::style::Color {
    match severity {
        "info" => theme.info,
        "warning" => theme.warning,
        "critical" | "error" => theme.error,
        _ => theme.dim,
    }
}

/// Connection state indicator
pub fn connection_icon(state: &crate::state::app_state::ConnectionState) -> (&'static str, ratatui::style::Color, &'static str) {
    match state {
        crate::state::app_state::ConnectionState::Connected => ("●", ratatui::style::Color::Green, "connected"),
        crate::state::app_state::ConnectionState::Connecting => ("◐", ratatui::style::Color::Yellow, "connecting"),
        crate::state::app_state::ConnectionState::Disconnected => ("○", ratatui::style::Color::Red, "disconnected"),
        crate::state::app_state::ConnectionState::Error(_) => ("✗", ratatui::style::Color::Red, "error"),
    }
}

/// Squad color for worker grouping (matching Python SQUAD_COLORS)
pub fn squad_color(worker_id: &str, theme: &Theme) -> ratatui::style::Color {
    if worker_id.contains("coder") {
        theme.cyan
    } else if worker_id.contains("verifier") {
        theme.secondary
    } else if worker_id.contains("scout") || worker_id.contains("narrator") || worker_id.contains("summarizer") {
        theme.yellow
    } else {
        theme.fg
    }
}
