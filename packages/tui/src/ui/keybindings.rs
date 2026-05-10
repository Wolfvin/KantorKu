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

    // AI Agent verifies: empty string returns None (no action)
    #[test]
    fn test_parse_nl_action_empty() {
        assert_eq!(parse_nl_action(""), None,
            "AI Agent invariant: empty input must return None");
    }

    // AI Agent verifies: whitespace-only string returns None
    #[test]
    fn test_parse_nl_action_whitespace() {
        assert_eq!(parse_nl_action("   "), None,
            "AI Agent invariant: whitespace-only must return None");
        assert_eq!(parse_nl_action("\t\n"), None,
            "AI Agent invariant: tabs/newlines must return None");
    }

    // AI Agent verifies: interrupt takes priority over accept when both match
    #[test]
    fn test_parse_nl_action_interrupt_priority() {
        // "stop" is interrupt, should NOT fall through to accept
        assert_eq!(parse_nl_action("stop"), Some("interrupt"),
            "AI Agent invariant: interrupt must have highest priority");
        // "halt ok" — "halt" is interrupt word at start
        assert_eq!(parse_nl_action("halt ok"), Some("interrupt"),
            "AI Agent: interrupt word at start must take priority");
    }

    // AI Agent verifies: multi-word accept patterns work
    #[test]
    fn test_parse_nl_action_accept_multiword() {
        assert_eq!(parse_nl_action("go ahead"), Some("accept"),
            "AI Agent: 'go ahead' must be accept");
        assert_eq!(parse_nl_action("go for it"), Some("accept"),
            "AI Agent: 'go for it' must be accept");
        assert_eq!(parse_nl_action("ship it"), Some("accept"),
            "AI Agent: 'ship it' must be accept");
    }

    // AI Agent verifies: revise patterns use contains matching
    #[test]
    fn test_parse_nl_action_revise_contains() {
        assert_eq!(parse_nl_action("I want something different"), Some("revise"),
            "AI Agent: 'i want' contains must match revise");
        assert_eq!(parse_nl_action("could you change this"), Some("revise"),
            "AI Agent: 'could you' contains must match revise");
        assert_eq!(parse_nl_action("please update the plan"), Some("revise"),
            "AI Agent: 'please update' contains must match revise");
    }

    // AI Agent verifies: filter_categories matches correctly
    #[test]
    fn test_filter_categories_matches() {
        // Tasks category
        assert!(filter_categories::matches("tasks", "task_started"),
            "AI Agent: task_started must match tasks category");
        assert!(filter_categories::matches("tasks", "task_done"),
            "AI Agent: task_done must match tasks category");
        assert!(filter_categories::matches("tasks", "task_failed"),
            "AI Agent: task_failed must match tasks category");
        assert!(!filter_categories::matches("tasks", "llm_stream_start"),
            "AI Agent: llm_stream_start must NOT match tasks category");

        // Briefing category
        assert!(filter_categories::matches("briefing", "briefing_opened"),
            "AI Agent: briefing_opened must match briefing category");
        assert!(!filter_categories::matches("briefing", "task_started"),
            "AI Agent: task_started must NOT match briefing category");

        // Errors category
        assert!(filter_categories::matches("errors", "error_logged"),
            "AI Agent: error_logged must match errors category");
        assert!(filter_categories::matches("errors", "circuit_open"),
            "AI Agent: circuit_open must match errors category");

        // LLM category
        assert!(filter_categories::matches("llm", "llm_stream_start"),
            "AI Agent: llm_stream_start must match llm category");
        assert!(filter_categories::matches("llm", "llm_stream_chunk"),
            "AI Agent: llm_stream_chunk must match llm category");

        // Unknown category matches everything
        assert!(filter_categories::matches("unknown_cat", "anything"),
            "AI Agent: unknown category must match all events");
    }
}
