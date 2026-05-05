use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

/// Kantor mode state
#[derive(Debug, Clone, Default)]
pub struct KantorState {
    // Contract
    pub contract_state: String,
    pub pending_contract: Option<Contract>,
    pub contract_title: String,
    pub todos: Vec<TodoItem>,
    pub revision_count: u32,

    // Workers
    pub worker_events: VecDeque<WorkerEvent>,
    pub active_tab: WorkersTab,

    // Manager chat
    pub manager_messages: Vec<ChatMessage>,
    pub input_text: String,
    pub input_history: Vec<String>,
    pub input_history_pos: usize,
    pub multiline_mode: bool,

    // Briefing
    pub briefing_messages: Vec<BriefingMessage>,

    // DAG
    pub dag_nodes: Vec<DagNode>,

    // Event log
    pub event_log: VecDeque<LogEvent>,
    pub event_filter: Option<String>,

    // Flags
    pub focus_mode: bool,
    pub auto_accept_pending: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum WorkersTab {
    Workers,
    Briefing,
    Dag,
    Events,
}

impl Default for WorkersTab {
    fn default() -> Self {
        WorkersTab::Workers
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Contract {
    pub title: String,
    pub description: String,
    pub todos: Vec<TodoItem>,
    pub estimated_cost: Option<f64>,
    pub workers: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TodoItem {
    pub title: String,
    pub done: bool,
    pub worker_id: Option<String>,
}

#[derive(Debug, Clone)]
pub struct WorkerEvent {
    pub worker_id: String,
    pub event_type: String,
    pub content: String,
    pub task_id: Option<String>,
    pub timestamp: String,
}

#[derive(Debug, Clone)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    pub timestamp: String,
}

#[derive(Debug, Clone)]
pub struct BriefingMessage {
    pub worker_id: String,
    pub content: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DagNode {
    pub title: String,
    pub worker_id: String,
    pub status: String,
    pub children: Vec<DagNode>,
}

#[derive(Debug, Clone)]
pub struct LogEvent {
    pub event_type: String,
    pub content: String,
    pub timestamp: String,
    pub severity: String,
}

/// Contract states matching Python ContractState enum
pub mod contract_states {
    pub const IDLE: &str = "idle";
    pub const MANAGER_THINKING: &str = "manager_thinking";
    pub const CLARIFYING: &str = "clarifying";
    pub const CONTRACT_PRESENTED: &str = "contract_presented";
    pub const AWAITING_REVISION: &str = "awaiting_revision";
    pub const TEAM_REVIEW: &str = "team_review";
    pub const TODO_REVIEW: &str = "todo_review";
    pub const CLIENT_FEEDBACK: &str = "client_feedback";
    pub const WORKING: &str = "working";
    pub const VERIFYING: &str = "verifying";
    pub const ACCEPTED: &str = "accepted";
    pub const DONE: &str = "done";
    pub const FAILED: &str = "failed";
}
