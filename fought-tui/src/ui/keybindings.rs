//! Keyboard shortcuts reference for Fought TUI
//!
//! Global (all modes):
//!   Tab             → Switch mode (Kantor ↔ Library)
//!   Ctrl+K          → Force Kantor mode
//!   Ctrl+B          → Force Library mode (b = buku)
//!   Ctrl+P          → Command palette
//!   Ctrl+C          → Quit
//!   Ctrl+Shift+T    → Toggle theme
//!
//! Kantor mode:
//!   Enter           → Send message
//!   Ctrl+M          → Multi-line input mode
//!   Ctrl+L          → Clear chat
//!   Up/Down         → History input
//!   Ctrl+Tab        → Switch tab (Workers/Briefing/DAG/Events)
//!   Escape          → Cancel current action
//!   Ctrl+A          → Accept contract
//!   Ctrl+R          → Revise contract
//!   Ctrl+I          → Interrupt/disrupt
//!   Ctrl+F          → Toggle focus mode
//!
//! Library mode:
//!   Tab (in mode)   → Cycle content mode (Browse/Ask/Ingest)
//!   Up/Down         → Navigate shelf
//!   Enter/Right     → Expand shelf / open entry
//!   Left/Backspace  → Navigate up one level
//!   /               → Quick search within shelf
//!   g               → Go to top
//!   G               → Go to bottom
//!   Ctrl+F          → Global search
//!   i               → Switch to Ingest mode
//!   a               → Switch to Ask mode
//!   b               → Switch to Browse mode
//!   h               → Mark helpful (in reader)
//!   u               → Mark unhelpful (in reader)
//!   s               → Save to library (in ask panel)

use crossterm::event::KeyCode;

/// Destructive commands that require confirmation
pub const DESTRUCTIVE_COMMANDS: &[&str] = &["fire", "reset", "queue-purge"];

/// Accept patterns for NL action parsing (matching Python regex patterns)
pub const ACCEPT_WORDS: &[&str] = &[
    "yes", "yeah", "yep", "ok", "okay", "accept", "approve", "go ahead",
    "go for it", "do it", "let's go", "sure", "sounds good", "perfect",
    "lg", "lfg", "ship it", "looks good", "agree", "confirmed", "confirm",
    "proceed", "execute",
];

/// Revise patterns for NL action parsing
pub const REVISE_WORDS: &[&str] = &[
    "no", "nope", "nah", "revise", "change", "modify", "update", "alter",
    "redo", "reject", "deny", "not quite", "not really", "i want", "i need",
    "i prefer", "instead", "could you", "can you", "please change",
    "please update", "but",
];

/// Interrupt patterns for NL action parsing
pub const INTERRUPT_WORDS: &[&str] = &[
    "stop", "halt", "pause", "wait", "hold on", "hold up", "interrupt",
    "disrupt", "break", "cancel",
];

/// Parse natural language input to determine user intent.
/// Returns: "accept" | "revise" | "interrupt" | None
pub fn parse_nl_action(input: &str) -> Option<&'static str> {
    let lower = input.to_lowercase();
    let trimmed = lower.trim();

    // Check interrupt first (highest priority)
    for word in INTERRUPT_WORDS {
        if trimmed.contains(word) {
            return Some("interrupt");
        }
    }

    // Check accept
    for word in ACCEPT_WORDS {
        if trimmed == *word || trimmed.starts_with(&format!("{word} ")) || trimmed.ends_with(&format!(" {word}")) {
            return Some("accept");
        }
    }

    // Check revise
    for word in REVISE_WORDS {
        if trimmed.contains(word) {
            return Some("revise");
        }
    }

    None
}

/// Filter categories for event log
pub mod filter_categories {
    pub const TASKS: &[&str] = &[
        "task_assigned", "task_started", "task_done", "task_failed",
        "task_recovered", "task_timeout",
    ];
    pub const BRIEFING: &[&str] = &[
        "briefing_opened", "plan_drafted", "plan_revised",
        "worker_speak_up", "worker_dm", "worker_broadcast",
    ];
    pub const ERRORS: &[&str] = &[
        "error_logged", "circuit_open", "rate_limit_hit", "cost_warning",
    ];
    pub const LLM: &[&str] = &[
        "llm_stream_start", "llm_stream_chunk", "llm_stream_done",
    ];
}
