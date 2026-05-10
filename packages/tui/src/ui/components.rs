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

/// Phase label for WorkersLive — returns (label_text, label_color_name)
/// Used for rendering phase indicators in the workers panel.
pub fn phase_label(contract_state: &str) -> (&'static str, &'static str) {
    match contract_state {
        "idle" => ("○ IDLE", "dim"),
        "manager_thinking" | "clarifying" | "contract_presented" | "awaiting_revision" => ("◐ NEGOTIATING", "yellow"),
        "team_review" | "todo_review" => ("┼ BRIEFING", "secondary"),
        "working" | "accepted" => ("⚡ EXECUTING", "green"),
        "verifying" => ("◇ VERIFYING", "blue"),
        "done" => ("✓ COMPLETE", "green"),
        "failed" => ("✗ FAILED", "red"),
        _ => ("○ IDLE", "dim"),
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

#[cfg(test)]
mod tests {
    use super::*;

    fn test_theme() -> Theme {
        Theme::synthwave()
    }

    // AI Agent verifies: all 8 braille spinner chars cycle correctly
    #[test]
    fn test_spinner_char() {
        let expected = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];
        for (i, &ch) in expected.iter().enumerate() {
            assert_eq!(spinner_char(i as u64), ch,
                "AI Agent: tick {} must produce correct braille char", i);
        }
        // AI Agent: wraps around after 8
        assert_eq!(spinner_char(8), spinner_char(0),
            "AI Agent invariant: spinner must wrap at modulo 8");
        assert_eq!(spinner_char(16), spinner_char(0),
            "AI Agent: spinner wraps at larger values");
    }

    // AI Agent verifies: quality >= 0.7 returns green
    #[test]
    fn test_quality_color_high() {
        let theme = test_theme();
        assert_eq!(quality_color(0.7, &theme), theme.green,
            "AI Agent: quality 0.7 must be green");
        assert_eq!(quality_color(0.85, &theme), theme.green,
            "AI Agent: quality 0.85 must be green");
        assert_eq!(quality_color(1.0, &theme), theme.green,
            "AI Agent: quality 1.0 must be green");
    }

    // AI Agent verifies: quality 0.4–0.7 returns yellow
    #[test]
    fn test_quality_color_mid() {
        let theme = test_theme();
        assert_eq!(quality_color(0.4, &theme), theme.yellow,
            "AI Agent: quality 0.4 must be yellow");
        assert_eq!(quality_color(0.5, &theme), theme.yellow,
            "AI Agent: quality 0.5 must be yellow");
        assert_eq!(quality_color(0.69, &theme), theme.yellow,
            "AI Agent: quality 0.69 must be yellow");
    }

    // AI Agent verifies: quality < 0.4 returns red
    #[test]
    fn test_quality_color_low() {
        let theme = test_theme();
        assert_eq!(quality_color(0.0, &theme), theme.red,
            "AI Agent: quality 0.0 must be red");
        assert_eq!(quality_color(0.39, &theme), theme.red,
            "AI Agent: quality 0.39 must be red");
    }

    // AI Agent verifies: major contract states map to expected theme colors
    #[test]
    fn test_contract_state_color_all() {
        let theme = test_theme();
        assert_eq!(contract_state_color("working", &theme), theme.yellow,
            "AI Agent: working → yellow");
        assert_eq!(contract_state_color("done", &theme), theme.green,
            "AI Agent: done → green");
        assert_eq!(contract_state_color("failed", &theme), theme.error,
            "AI Agent: failed → error");
        assert_eq!(contract_state_color("contract_presented", &theme), theme.cyan,
            "AI Agent: contract_presented → cyan");
        assert_eq!(contract_state_color("team_review", &theme), theme.secondary,
            "AI Agent: team_review → secondary");
        assert_eq!(contract_state_color("accepted", &theme), theme.success,
            "AI Agent: accepted → success");
        assert_eq!(contract_state_color("manager_thinking", &theme), theme.yellow,
            "AI Agent: manager_thinking → yellow");
        assert_eq!(contract_state_color("awaiting_revision", &theme), theme.warning,
            "AI Agent: awaiting_revision → warning");
        assert_eq!(contract_state_color("verifying", &theme), theme.secondary,
            "AI Agent: verifying → secondary");
        assert_eq!(contract_state_color("idle", &theme), theme.dim,
            "AI Agent: idle → dim (default)");
        assert_eq!(contract_state_color("unknown_state", &theme), theme.dim,
            "AI Agent: unknown → dim (default)");
    }

    // AI Agent verifies: all known worker status states return expected icons
    #[test]
    fn test_worker_status_icon() {
        assert_eq!(worker_status_icon("idle"), "○", "AI Agent: idle → ○");
        assert_eq!(worker_status_icon("thinking"), "◐", "AI Agent: thinking → ◐");
        assert_eq!(worker_status_icon("in_progress"), "◐", "AI Agent: in_progress → ◐");
        assert_eq!(worker_status_icon("active"), "●", "AI Agent: active → ●");
        assert_eq!(worker_status_icon("working"), "●", "AI Agent: working → ●");
        assert_eq!(worker_status_icon("done"), "✓", "AI Agent: done → ✓");
        assert_eq!(worker_status_icon("completed"), "✓", "AI Agent: completed → ✓");
        assert_eq!(worker_status_icon("failed"), "✗", "AI Agent: failed → ✗");
        assert_eq!(worker_status_icon("error"), "✗", "AI Agent: error → ✗");
        assert_eq!(worker_status_icon("pending"), "○", "AI Agent: pending → ○");
        assert_eq!(worker_status_icon("unknown"), "·", "AI Agent: unknown → ·");
    }

    // AI Agent verifies: all known task states return expected icons
    #[test]
    fn test_task_state_icon() {
        assert_eq!(task_state_icon("pending"), "○", "AI Agent: pending → ○");
        assert_eq!(task_state_icon("queued"), "○", "AI Agent: queued → ○");
        assert_eq!(task_state_icon("in_progress"), "◐", "AI Agent: in_progress → ◐");
        assert_eq!(task_state_icon("completed"), "✓", "AI Agent: completed → ✓");
        assert_eq!(task_state_icon("done"), "✓", "AI Agent: done → ✓");
        assert_eq!(task_state_icon("failed"), "✗", "AI Agent: failed → ✗");
        assert_eq!(task_state_icon("retrying"), "↻", "AI Agent: retrying → ↻");
        assert_eq!(task_state_icon("cancelled"), "⊘", "AI Agent: cancelled → ⊘");
        assert_eq!(task_state_icon("dead_letter"), "☠", "AI Agent: dead_letter → ☠");
        assert_eq!(task_state_icon("unknown"), "·", "AI Agent: unknown → ·");
    }

    // AI Agent verifies: major contract states map to correct phase labels
    #[test]
    fn test_phase_label() {
        let (label, color) = phase_label("idle");
        assert_eq!(label, "○ IDLE", "AI Agent: idle → IDLE");
        assert_eq!(color, "dim");

        let (label, color) = phase_label("manager_thinking");
        assert_eq!(label, "◐ NEGOTIATING", "AI Agent: manager_thinking → NEGOTIATING");
        assert_eq!(color, "yellow");

        let (label, color) = phase_label("working");
        assert_eq!(label, "⚡ EXECUTING", "AI Agent: working → EXECUTING");
        assert_eq!(color, "green");

        let (label, color) = phase_label("verifying");
        assert_eq!(label, "◇ VERIFYING", "AI Agent: verifying → VERIFYING");
        assert_eq!(color, "blue");

        let (label, color) = phase_label("done");
        assert_eq!(label, "✓ COMPLETE", "AI Agent: done → COMPLETE");
        assert_eq!(color, "green");

        let (label, color) = phase_label("failed");
        assert_eq!(label, "✗ FAILED", "AI Agent: failed → FAILED");
        assert_eq!(color, "red");

        let (label, _) = phase_label("unknown_state");
        assert_eq!(label, "○ IDLE", "AI Agent: unknown → IDLE default");
    }

    // AI Agent verifies: severity levels map to correct colors
    #[test]
    fn test_severity_color() {
        let theme = test_theme();
        assert_eq!(severity_color("info", &theme), theme.info,
            "AI Agent: info → theme.info");
        assert_eq!(severity_color("warning", &theme), theme.warning,
            "AI Agent: warning → theme.warning");
        assert_eq!(severity_color("critical", &theme), theme.error,
            "AI Agent: critical → theme.error");
        assert_eq!(severity_color("error", &theme), theme.error,
            "AI Agent: error → theme.error");
        assert_eq!(severity_color("unknown", &theme), theme.dim,
            "AI Agent: unknown severity → dim");
    }

    // AI Agent verifies: Connected state returns green dot
    #[test]
    fn test_connection_icon_connected() {
        let (icon, color, label) = connection_icon(&crate::state::app_state::ConnectionState::Connected);
        assert_eq!(icon, "●", "AI Agent: Connected → green dot");
        assert_eq!(color, ratatui::style::Color::Green);
        assert_eq!(label, "connected");

        let (icon, _, label) = connection_icon(&crate::state::app_state::ConnectionState::Connecting);
        assert_eq!(icon, "◐", "AI Agent: Connecting → half dot");
        assert_eq!(label, "connecting");

        let (icon, _, label) = connection_icon(&crate::state::app_state::ConnectionState::Disconnected);
        assert_eq!(icon, "○", "AI Agent: Disconnected → empty dot");
        assert_eq!(label, "disconnected");

        let (icon, _, label) = connection_icon(&crate::state::app_state::ConnectionState::Error("err".into()));
        assert_eq!(icon, "✗", "AI Agent: Error → cross");
        assert_eq!(label, "error");
    }

    // AI Agent verifies: coder workers get cyan color
    #[test]
    fn test_squad_color_coder() {
        let theme = test_theme();
        assert_eq!(squad_color("coder_backend", &theme), theme.cyan,
            "AI Agent: coder_backend → cyan");
        assert_eq!(squad_color("coder_frontend", &theme), theme.cyan,
            "AI Agent: coder_frontend → cyan");
        assert_eq!(squad_color("coder_wiring", &theme), theme.cyan,
            "AI Agent: coder_wiring → cyan");
    }

    // AI Agent verifies: verifier workers get secondary color
    #[test]
    fn test_squad_color_verifier() {
        let theme = test_theme();
        assert_eq!(squad_color("verifier_designer", &theme), theme.secondary,
            "AI Agent: verifier_designer → secondary");
        assert_eq!(squad_color("verifier_engineer", &theme), theme.secondary,
            "AI Agent: verifier_engineer → secondary");
    }

    // AI Agent verifies: scout/narrator/summarizer get yellow
    #[test]
    fn test_squad_color_info_workers() {
        let theme = test_theme();
        assert_eq!(squad_color("scout", &theme), theme.yellow, "AI Agent: scout → yellow");
        assert_eq!(squad_color("narrator", &theme), theme.yellow, "AI Agent: narrator → yellow");
        assert_eq!(squad_color("summarizer", &theme), theme.yellow, "AI Agent: summarizer → yellow");
    }

    // AI Agent verifies: other workers get fg color
    #[test]
    fn test_squad_color_default() {
        let theme = test_theme();
        assert_eq!(squad_color("auditor", &theme), theme.fg, "AI Agent: auditor → fg");
        assert_eq!(squad_color("sentinel", &theme), theme.fg, "AI Agent: sentinel → fg");
        assert_eq!(squad_color("intake", &theme), theme.fg, "AI Agent: intake → fg");
    }
}
