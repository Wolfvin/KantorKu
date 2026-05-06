/// Contract state enum — replaces stringly-typed state tracking.
/// Values MUST match Python ContractState enum.
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[derive(Default)]
pub enum ContractState {
    #[default]
    Idle,
    ManagerThinking,
    Clarifying,
    ContractPresented,
    AwaitingRevision,
    TeamReview,
    TodoReview,
    ClientFeedback,
    Working,
    Verifying,
    Accepted,
    Done,
    Failed,
}

impl ContractState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::ManagerThinking => "manager_thinking",
            Self::Clarifying => "clarifying",
            Self::ContractPresented => "contract_presented",
            Self::AwaitingRevision => "awaiting_revision",
            Self::TeamReview => "team_review",
            Self::TodoReview => "todo_review",
            Self::ClientFeedback => "client_feedback",
            Self::Working => "working",
            Self::Verifying => "verifying",
            Self::Accepted => "accepted",
            Self::Done => "done",
            Self::Failed => "failed",
        }
    }

    /// Parse from the string the Python backend sends.
    pub fn from_str_lossy(s: &str) -> Self {
        match s {
            "idle" => Self::Idle,
            "manager_thinking" => Self::ManagerThinking,
            "clarifying" => Self::Clarifying,
            "contract_presented" => Self::ContractPresented,
            "awaiting_revision" => Self::AwaitingRevision,
            "team_review" => Self::TeamReview,
            "todo_review" => Self::TodoReview,
            "client_feedback" => Self::ClientFeedback,
            "working" => Self::Working,
            "verifying" => Self::Verifying,
            "accepted" => Self::Accepted,
            "done" => Self::Done,
            "failed" => Self::Failed,
            _ => Self::Idle,
        }
    }
}

impl std::fmt::Display for ContractState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[allow(dead_code)] // Fields used for serde deserialization
pub struct Contract {
    pub title: String,
    pub description: String,
    pub todos: Vec<TodoItem>,
    pub estimated_cost: Option<f64>,
    pub workers: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[allow(dead_code)] // Fields used for serde deserialization
pub struct TodoItem {
    pub title: String,
    pub done: bool,
    pub worker_id: Option<String>,
}
