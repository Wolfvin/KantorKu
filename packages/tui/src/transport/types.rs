use serde::Deserialize;

use crate::state::office_state::Contract;
use crate::state::library_state::{LibraryEntry, LibraryEntryBrief, SourceRef};

/// All events from Python backend via WebSocket.
/// Field names MUST match Python EventBus payloads.
/// New TUI-specific events are added for async action feedback.
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
#[allow(dead_code)] // Fields used for serde deserialization
pub enum BackendEvent {
    // === OFFICE EVENTS ===
    WsConnected,
    WsConnecting,
    WsDisconnected,
    WsError { message: String },
    ManagerQuestion { content: String, session_id: String },
    ManagerBrainstorming { content: String, session_id: String },
    ContractReady { contract: Contract, session_id: String },
    RevisionRequested { feedback: String, session_id: String },
    BriefingOpened { workers: Vec<String>, session_id: String },
    WorkerSpeakUp { worker_id: String, content: String, msg_type: String },
    PlanDrafted { plan: String, session_id: String },
    PlanRevised { plan: String, round: u32, session_id: String },
    TaskAssigned { worker_id: String, task: String, session_id: String },
    TaskStarted { worker_id: String, task_id: String },
    TaskDone { worker_id: String, task_id: String, output: String },
    TaskFailed { worker_id: String, task_id: String, error: String },
    TaskRecovered { worker_id: String, task_id: String },
    TaskTimeout { worker_id: String, task_id: String },
    LlmStreamStart { worker_id: String, task_id: String },
    LlmStreamChunk { worker_id: String, task_id: String, chunk: String },
    LlmStreamDone { worker_id: String, task_id: String },
    WorkerDm { from_id: String, to_id: String, message: String },
    WorkerBroadcast { from_id: String, message: String },
    DelegationRequest { from: String, to: String, instruction: String },
    DelegationResult { from: String, to: String, status: String, output: String },
    ContractStateChange { state: String, session_id: String },
    ManagerMessage { content: String, session_id: String },
    ContractAccepted { session_id: String },
    WorkStarted { session_id: String },
    WorkDone { result: serde_json::Value, session_id: String },
    Error { message: String },
    ContextFetchStart { worker_id: String },
    ContextFetchDone { worker_id: String },
    VerifyDesignStart { worker_id: String },
    VerifyDesignDone { worker_id: String },
    VerifyEngineerStart { worker_id: String },
    VerifyEngineerDone { worker_id: String },
    ErrorLogged { message: String, severity: String },
    CircuitOpen { worker_id: String },
    CircuitClosed { worker_id: String },
    RateLimitHit { worker_id: String },
    CostWarning { current: f64, limit: f64 },
    WorkerHired { worker_id: String },
    WorkerFired { worker_id: String },
    CheckpointSaved { session_id: String },
    CrashRecovered { session_id: String },
    SkillUpdated { worker_id: String, skill: String },

    // === LIBRARY EVENTS ===
    LibraryIngestStarted { entry_id: String },
    LibraryIngestDone { entry: Box<LibraryEntry> },
    LibraryIngestFailed { error: String },
    LibraryShelfCreated { shelf_path: Vec<String> },
    LibraryQueryStarted { query_id: String },
    LibraryQueryChunk { query_id: String, chunk: String },
    LibraryQueryDone { query_id: String, sources: Vec<SourceRef> },

    // === TUI-SPECIFIC FEEDBACK EVENTS (not from Python, from async actions) ===
    /// Internal event: shelf entries loaded from HTTP GET
    #[serde(skip)]
    ShelfEntriesLoaded { path: Vec<String>, entries: Vec<LibraryEntryBrief> },
    /// Internal event: single entry loaded from HTTP GET
    #[serde(skip)]
    EntryLoaded { entry: Box<LibraryEntry> },
    /// Internal event: search results loaded
    #[serde(skip)]
    SearchResultsLoaded { query: String, results: Vec<LibraryEntryBrief> },
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: WsConnected deserializes from JSON
    #[test]
    fn test_backend_event_deserialization_ws_connected() {
        let json = r#"{"type": "ws_connected"}"#;
        let event: Result<BackendEvent, _> = serde_json::from_str(json);
        assert!(event.is_ok(), "AI Agent: ws_connected must deserialize successfully");
        match event.unwrap() {
            BackendEvent::WsConnected => {},
            other => panic!("AI Agent: expected WsConnected, got {:?}", other),
        }
    }

    // AI Agent verifies: TaskStarted deserializes with fields from JSON
    #[test]
    fn test_backend_event_deserialization_task_started() {
        let json = r#"{"type": "task_started", "worker_id": "coder_backend", "task_id": "task_abc123"}"#;
        let event: Result<BackendEvent, _> = serde_json::from_str(json);
        assert!(event.is_ok(), "AI Agent: task_started must deserialize successfully");
        match event.unwrap() {
            BackendEvent::TaskStarted { worker_id, task_id } => {
                assert_eq!(worker_id, "coder_backend", "AI Agent: worker_id must be preserved");
                assert_eq!(task_id, "task_abc123", "AI Agent: task_id must be preserved");
            }
            other => panic!("AI Agent: expected TaskStarted, got {:?}", other),
        }
    }

    // AI Agent verifies: unknown type fails deserialization
    #[test]
    fn test_backend_event_deserialization_unknown_type() {
        let json = r#"{"type": "completely_unknown_event", "data": "test"}"#;
        let event: Result<BackendEvent, _> = serde_json::from_str(json);
        assert!(event.is_err(),
            "AI Agent invariant: unknown event type must fail deserialization");
    }

    // AI Agent verifies: ManagerMessage deserializes with all fields
    #[test]
    fn test_backend_event_deserialization_manager_message() {
        let json = r#"{"type": "manager_message", "content": "Hello!", "session_id": "sess_001"}"#;
        let event: Result<BackendEvent, _> = serde_json::from_str(json);
        assert!(event.is_ok());
        match event.unwrap() {
            BackendEvent::ManagerMessage { content, session_id } => {
                assert_eq!(content, "Hello!");
                assert_eq!(session_id, "sess_001");
            }
            other => panic!("AI Agent: expected ManagerMessage, got {:?}", other),
        }
    }

    // AI Agent verifies: Error event deserializes
    #[test]
    fn test_backend_event_deserialization_error() {
        let json = r#"{"type": "error", "message": "connection refused"}"#;
        let event: Result<BackendEvent, _> = serde_json::from_str(json);
        assert!(event.is_ok());
        match event.unwrap() {
            BackendEvent::Error { message } => {
                assert_eq!(message, "connection refused");
            }
            other => panic!("AI Agent: expected Error, got {:?}", other),
        }
    }

    // AI Agent verifies: ShelfEntriesLoaded is skipped by serde (internal event)
    #[test]
    fn test_backend_event_skip_deserialization() {
        // TUI-specific events use #[serde(skip)] and can't be deserialized from JSON
        let json = r#"{"type": "shelf_entries_loaded", "path": [], "entries": []}"#;
        let event: Result<BackendEvent, _> = serde_json::from_str(json);
        assert!(event.is_err(),
            "AI Agent: serde(skip) events must not deserialize from external JSON");
    }
}
