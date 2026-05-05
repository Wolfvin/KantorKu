//! Keyboard shortcuts reference and NL action parsing

/// Destructive commands requiring confirmation (matching Python)
pub const DESTRUCTIVE_COMMANDS: &[&str] = &["fire", "reset", "queue-purge"];

/// Accept patterns for NL action parsing
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

/// Interrupt patterns for NL action parsing — use word-boundary matching to avoid false positives
pub const INTERRUPT_WORDS: &[&str] = &[
    "stop", "halt", "pause", "wait", "hold on", "hold up", "interrupt",
    "disrupt", "cancel",
];

/// Parse natural language input to determine user intent.
/// Returns: "accept" | "revise" | "interrupt" | None
pub fn parse_nl_action(input: &str) -> Option<&'static str> {
    let lower = input.to_lowercase();
    let trimmed = lower.trim();

    // Check interrupt first (highest priority) — exact word or starts/ends with word + space
    for word in INTERRUPT_WORDS {
        if trimmed == *word
            || trimmed.starts_with(&format!("{word} "))
            || trimmed.ends_with(&format!(" {word}"))
            || trimmed.contains(&format!(" {word} "))
        {
            return Some("interrupt");
        }
    }

    // Check accept — precise matching to avoid false positives (e.g., "look" matching "ok")
    for word in ACCEPT_WORDS {
        if trimmed == *word || trimmed.starts_with(&format!("{word} ")) || trimmed.ends_with(&format!(" {word}")) {
            return Some("accept");
        }
    }

    // Check revise — broader matching since revise intent is the fallback
    for word in REVISE_WORDS {
        if trimmed.contains(word) {
            return Some("revise");
        }
    }

    None
}

/// Filter categories for event log (matching Python FILTER_CATEGORIES)
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

    pub fn matches(category: &str, event_type: &str) -> bool {
        let list = match category {
            "tasks" => TASKS,
            "briefing" => BRIEFING,
            "errors" => ERRORS,
            "llm" => LLM,
            _ => return true,
        };
        list.contains(&event_type)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_accept_words() {
        assert_eq!(parse_nl_action("ok"), Some("accept"));
        assert_eq!(parse_nl_action("yes"), Some("accept"));
        assert_eq!(parse_nl_action("accept"), Some("accept"));
        assert_eq!(parse_nl_action("sounds good"), Some("accept"));
        assert_eq!(parse_nl_action("go ahead"), Some("accept"));
    }

    #[test]
    fn test_revise_words() {
        assert_eq!(parse_nl_action("no"), Some("revise"));
        assert_eq!(parse_nl_action("revise it"), Some("revise"));
        assert_eq!(parse_nl_action("change the plan"), Some("revise"));
    }

    #[test]
    fn test_interrupt_words() {
        assert_eq!(parse_nl_action("stop"), Some("interrupt"));
        assert_eq!(parse_nl_action("halt"), Some("interrupt"));
        assert_eq!(parse_nl_action("please stop"), Some("interrupt"));
        assert_eq!(parse_nl_action("wait"), Some("interrupt"));
    }

    #[test]
    fn test_no_false_positives() {
        // "look" should NOT match "ok" anymore
        assert_eq!(parse_nl_action("look at this"), None);
        // "broke" should not match interrupt
        assert_eq!(parse_nl_action("broke"), None);
    }
}
