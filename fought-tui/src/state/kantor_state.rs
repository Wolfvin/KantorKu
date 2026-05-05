use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

/// Kantor mode state
#[derive(Debug, Clone)]
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
    pub workers_list: Vec<String>,

    // Manager chat
    pub manager_messages: Vec<ChatMessage>,
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
    pub auto_accept_pending: bool,
}

#[derive(Debug, Clone, Copy, PartialEq)]
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
    pub speaker: String,
    pub content: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DagNode {
    pub title: String,
    pub worker_id: String,
    pub task_id: Option<String>,
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

impl KantorState {
    pub fn push_manager_message(&mut self, role: &str, content: &str) {
        self.manager_messages.push(ChatMessage {
            role: role.to_string(),
            content: content.to_string(),
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
        });
        // Keep max 500 messages
        if self.manager_messages.len() > 500 {
            self.manager_messages.remove(0);
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
        if self.worker_events.len() > 500 {
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
            content: if content.is_empty() { format!("{worker_id}") } else { content.to_string() },
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
            severity: severity.to_string(),
        });
        if self.event_log.len() > 1000 {
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
        if self.event_log.len() > 1000 {
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

    pub fn add_dag_node_if_needed(&mut self, worker_id: &str, task_id: &str) {
        // Check if task_id already exists
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

    fn find_dag_node_by_task(&self, task_id: &str) -> Option<&DagNode> {
        self.dag_nodes.iter().find(|n| n.task_id.as_deref() == Some(task_id))
    }

    fn find_dag_node_by_task_mut(&mut self, task_id: &str) -> Option<&mut DagNode> {
        self.dag_nodes.iter_mut().find(|n| n.task_id.as_deref() == Some(task_id))
    }

    pub fn scroll_up(&mut self) {
        match self.active_tab {
            WorkersTab::Workers => { /* handled by list widget */ }
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
            contract_state: "idle".to_string(),
            pending_contract: None,
            contract_title: String::new(),
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
            manager_messages: vec![],
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
            auto_accept_pending: false,
        }
    }
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
