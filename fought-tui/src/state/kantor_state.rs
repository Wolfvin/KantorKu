use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

/// Contract state enum — replaces stringly-typed state tracking.
/// Values MUST match Python ContractState enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum ContractState {
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

impl Default for ContractState {
    fn default() -> Self { Self::Idle }
}

impl std::fmt::Display for ContractState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Kantor mode state
#[derive(Debug, Clone)]
#[allow(dead_code)] // State fields accessed by render methods
pub struct KantorState {
    // Contract
    pub contract_state: ContractState,
    pub pending_contract: Option<Contract>,
    pub todos: Vec<TodoItem>,
    pub revision_count: u32,

    // Workers
    pub worker_events: VecDeque<WorkerEvent>,
    pub active_tab: WorkersTab,
    pub workers_list: Vec<String>,

    // Manager chat — VecDeque for O(1) front removal
    pub manager_messages: VecDeque<ChatMessage>,
    pub manager_scroll: usize,
    pub input_text: String,
    pub input_cursor: usize,
    pub input_history: Vec<String>,
    pub input_history_pos: usize,
    pub multiline_mode: bool,
    pub input_focused: bool,

    // Briefing
    pub briefing_active: bool,
    pub briefing_workers: Vec<String>,
    pub briefing_messages: Vec<BriefingMessage>,

    // DAG
    pub dag_nodes: Vec<DagNode>,

    // Event log
    pub event_log: VecDeque<LogEvent>,
    pub event_filter: Option<String>,

    // LLM streaming state
    pub llm_streaming_worker: Option<String>,
    pub llm_stream_buffer: String,

    // Flags
    pub focus_mode: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkersTab {
    Workers,
    Briefing,
    Dag,
    Events,
}

impl Default for WorkersTab {
    fn default() -> Self { WorkersTab::Workers }
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

#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct WorkerEvent {
    pub worker_id: String,
    pub event_type: String,
    pub content: String,
    pub task_id: Option<String>,
    pub timestamp: String,
}

#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    pub timestamp: String,
}

#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct BriefingMessage {
    pub speaker: String,
    pub content: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[allow(dead_code)] // Fields used for serde deserialization
pub struct DagNode {
    pub title: String,
    pub worker_id: String,
    pub task_id: Option<String>,
    pub status: String,
    pub children: Vec<DagNode>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct LogEvent {
    pub event_type: String,
    pub content: String,
    pub timestamp: String,
    pub severity: String,
}

impl KantorState {
    pub fn push_manager_message(&mut self, role: &str, content: &str) {
        self.manager_messages.push_back(ChatMessage {
            role: role.to_string(),
            content: content.to_string(),
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
        });
        // Keep max 500 messages — O(1) front removal with VecDeque
        while self.manager_messages.len() > 500 {
            self.manager_messages.pop_front();
        }
    }

    pub fn push_worker_event(&mut self, worker_id: &str, event_type: &str, content: &str, task_id: Option<&str>) {
        self.worker_events.push_back(WorkerEvent {
            worker_id: worker_id.to_string(),
            event_type: event_type.to_string(),
            content: content.to_string(),
            task_id: task_id.map(|s| s.to_string()),
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
        });
        while self.worker_events.len() > 500 {
            self.worker_events.pop_front();
        }

        // Also push to event log
        let severity = match event_type {
            "task_failed" | "circuit_open" | "rate_limit" => "critical",
            "task_timeout" => "warning",
            _ => "info",
        };
        self.event_log.push_back(LogEvent {
            event_type: event_type.to_string(),
            content: if content.is_empty() { worker_id.to_string() } else { content.to_string() },
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
            severity: severity.to_string(),
        });
        while self.event_log.len() > 1000 {
            self.event_log.pop_front();
        }
    }

    pub fn push_log_event(&mut self, event_type: &str, content: &str, severity: &str) {
        self.event_log.push_back(LogEvent {
            event_type: event_type.to_string(),
            content: content.to_string(),
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
            severity: severity.to_string(),
        });
        while self.event_log.len() > 1000 {
            self.event_log.pop_front();
        }
    }

    pub fn add_briefing_msg(&mut self, speaker: &str, content: &str) {
        self.briefing_messages.push(BriefingMessage {
            speaker: speaker.to_string(),
            content: content.to_string(),
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
        });
    }

    pub fn append_llm_chunk(&mut self, worker_id: &str, chunk: &str) {
        if self.llm_streaming_worker.as_deref() != Some(worker_id) {
            self.llm_streaming_worker = Some(worker_id.to_string());
            self.llm_stream_buffer.clear();
        }
        self.llm_stream_buffer.push_str(chunk);
    }

    /// Add a DAG node if it doesn't already exist (searches recursively).
    pub fn add_dag_node_if_needed(&mut self, worker_id: &str, task_id: &str) {
        if self.find_dag_node_by_task(task_id).is_some() {
            return;
        }
        self.dag_nodes.push(DagNode {
            title: format!("Task {}", &task_id[..7.min(task_id.len())]),
            worker_id: worker_id.to_string(),
            task_id: Some(task_id.to_string()),
            status: "working".to_string(),
            children: vec![],
        });
    }

    pub fn update_dag_status(&mut self, task_id: &str, status: &str) {
        if let Some(node) = self.find_dag_node_by_task_mut(task_id) {
            node.status = status.to_string();
        }
    }

    /// Recursive search for a DAG node by task_id.
    fn find_dag_node_by_task(&self, task_id: &str) -> Option<&DagNode> {
        fn search<'a>(nodes: &'a [DagNode], task_id: &str) -> Option<&'a DagNode> {
            for node in nodes {
                if node.task_id.as_deref() == Some(task_id) {
                    return Some(node);
                }
                if let Some(found) = search(&node.children, task_id) {
                    return Some(found);
                }
            }
            None
        }
        search(&self.dag_nodes, task_id)
    }

    /// Recursive mutable search for a DAG node by task_id.
    fn find_dag_node_by_task_mut(&mut self, task_id: &str) -> Option<&mut DagNode> {
        fn search<'a>(nodes: &'a mut [DagNode], task_id: &str) -> Option<&'a mut DagNode> {
            for node in nodes.iter_mut() {
                if node.task_id.as_deref() == Some(task_id) {
                    return Some(node);
                }
                if let Some(found) = search(&mut node.children, task_id) {
                    return Some(found);
                }
            }
            None
        }
        search(&mut self.dag_nodes, task_id)
    }

    pub fn scroll_up(&mut self) {
        match self.active_tab {
            WorkersTab::Workers => {}
            WorkersTab::Briefing => {}
            WorkersTab::Dag => {}
            WorkersTab::Events => {}
        }
    }

    pub fn scroll_down(&mut self) {
        // Mouse scroll is handled via visible window offset
    }
}

impl Default for KantorState {
    fn default() -> Self {
        Self {
            contract_state: ContractState::Idle,
            pending_contract: None,
            todos: vec![],
            revision_count: 0,
            worker_events: VecDeque::new(),
            active_tab: WorkersTab::Workers,
            workers_list: vec![
                "auditor".into(), "coder_backend".into(), "coder_frontend".into(),
                "coder_wiring".into(), "debugger".into(), "intake".into(),
                "narrator".into(), "scout".into(), "scribe".into(),
                "sentinel".into(), "summarizer".into(), "verifier_designer".into(),
                "verifier_engineer".into(),
            ],
            manager_messages: VecDeque::new(),
            manager_scroll: 0,
            input_text: String::new(),
            input_cursor: 0,
            input_history: vec![],
            input_history_pos: 0,
            multiline_mode: false,
            input_focused: true,
            briefing_active: false,
            briefing_workers: vec![],
            briefing_messages: vec![],
            dag_nodes: vec![],
            event_log: VecDeque::new(),
            event_filter: None,
            llm_streaming_worker: None,
            llm_stream_buffer: String::new(),
            focus_mode: false,
        }
    }
}
