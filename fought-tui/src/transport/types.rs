use serde::Deserialize;

use crate::state::kantor_state::{Contract, TodoItem};
use crate::state::library_state::{LibraryEntry, LibraryEntryBrief, Shelf, SourceRef};

/// All events that can come from the Python backend via WebSocket.
/// Field names MUST match the Python EventBus event payloads.
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum BackendEvent {
    // === KANTOR EVENTS ===
    ManagerQuestion { content: String, session_id: String },
    ManagerBrainstorming { content: String, session_id: String },
    ContractReady { contract: Contract, session_id: String },
    RevisionRequested { feedback: String, session_id: String },
    BriefingOpened { workers: Vec<String>, session_id: String },
    WorkerSpeakUp {
        worker_id: String,
        content: String,
        msg_type: String,
    },
    PlanDrafted { plan: String, session_id: String },
    PlanRevised { plan: String, round: u32, session_id: String },
    TaskAssigned {
        worker_id: String,
        task: String,
        session_id: String,
    },
    TaskStarted { worker_id: String, task_id: String },
    TaskDone {
        worker_id: String,
        task_id: String,
        output: String,
    },
    TaskFailed {
        worker_id: String,
        task_id: String,
        error: String,
    },
    LlmStreamStart { worker_id: String, task_id: String },
    LlmStreamChunk { worker_id: String, task_id: String, chunk: String },
    LlmStreamDone { worker_id: String, task_id: String },
    WorkerDm {
        from_id: String,
        to_id: String,
        message: String,
    },
    WorkerBroadcast { from_id: String, message: String },
    DelegationRequest {
        from: String,
        to: String,
        instruction: String,
    },
    DelegationResult {
        from: String,
        to: String,
        status: String,
        output: String,
    },
    ContractStateChange { state: String, session_id: String },
    ManagerMessage { content: String, session_id: String },
    ContractAccepted { session_id: String },
    WorkStarted { session_id: String },
    WorkDone { result: serde_json::Value, session_id: String },
    Error { message: String },
    TaskRecovered { worker_id: String, task_id: String },
    TaskTimeout { worker_id: String, task_id: String },
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
    LibraryIngestDone { entry: LibraryEntry },
    LibraryIngestFailed { error: String },
    LibraryShelfCreated { shelf_path: Vec<String> },
    LibraryQueryStarted { query_id: String },
    LibraryQueryChunk { query_id: String, chunk: String },
    LibraryQueryDone { query_id: String, sources: Vec<SourceRef> },
}
