// Re-export all public types from sub-modules so existing code doesn't break
pub use super::contract_state::{Contract, ContractState, TodoItem};
pub use super::worker_state::{BriefingMessage, ChatMessage, DagNode, LogEvent, WorkerEvent, WorkersTab};

use std::collections::VecDeque;

/// Office mode state — the main state container for the Office (office) mode.
/// Split into sub-modules for maintainability:
/// - contract_state.rs: ContractState enum, Contract, TodoItem
/// - worker_state.rs: DagNode, WorkerEvent, LogEvent, ChatMessage, BriefingMessage, WorkersTab
#[derive(Debug, Clone)]
#[allow(dead_code)] // State fields accessed by render methods
pub struct OfficeState {
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
    pub event_scroll: usize,

    // LLM streaming state
    pub llm_streaming_worker: Option<String>,
    pub llm_stream_buffer: String,

    // Flags
    pub focus_mode: bool,
}

impl OfficeState {
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

    /// Search all DAG nodes for a given task_id
    fn find_dag_node_by_task(&self, task_id: &str) -> Option<&DagNode> {
        for node in &self.dag_nodes {
            if let Some(found) = node.find_by_task(task_id) {
                return Some(found);
            }
        }
        None
    }

    /// Search all DAG nodes for a given task_id (mutable)
    fn find_dag_node_by_task_mut(&mut self, task_id: &str) -> Option<&mut DagNode> {
        for node in &mut self.dag_nodes {
            if let Some(found) = node.find_by_task_mut(task_id) {
                return Some(found);
            }
        }
        None
    }

    pub fn scroll_up(&mut self) {
        match self.active_tab {
            WorkersTab::Workers | WorkersTab::Briefing | WorkersTab::Dag => {
                self.manager_scroll = self.manager_scroll.saturating_sub(3);
            }
            WorkersTab::Events => {
                self.event_scroll = self.event_scroll.saturating_sub(3);
            }
        }
    }

    pub fn scroll_down(&mut self) {
        match self.active_tab {
            WorkersTab::Workers | WorkersTab::Briefing | WorkersTab::Dag => {
                self.manager_scroll = self.manager_scroll.saturating_add(3);
            }
            WorkersTab::Events => {
                self.event_scroll = self.event_scroll.saturating_add(3);
            }
        }
    }
}

impl Default for OfficeState {
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
            event_scroll: 0,
            llm_streaming_worker: None,
            llm_stream_buffer: String::new(),
            focus_mode: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: every ContractState variant roundtrips through as_str → from_str_lossy
    #[test]
    fn test_contract_state_as_str_roundtrip() {
        let variants = [
            ContractState::Idle,
            ContractState::ManagerThinking,
            ContractState::Clarifying,
            ContractState::ContractPresented,
            ContractState::AwaitingRevision,
            ContractState::TeamReview,
            ContractState::TodoReview,
            ContractState::ClientFeedback,
            ContractState::Working,
            ContractState::Verifying,
            ContractState::Accepted,
            ContractState::Done,
            ContractState::Failed,
        ];
        for v in variants {
            let s = v.as_str();
            assert_eq!(ContractState::from_str_lossy(s), v,
                "AI Agent invariant: as_str→from_str_lossy must roundtrip for {:?}", v);
        }
    }

    // AI Agent verifies: unknown string gracefully falls back to Idle
    #[test]
    fn test_contract_state_from_str_lossy_unknown() {
        assert_eq!(ContractState::from_str_lossy("nonexistent_state"), ContractState::Idle,
            "AI Agent invariant: unknown state strings must default to Idle");
        assert_eq!(ContractState::from_str_lossy(""), ContractState::Idle,
            "AI Agent invariant: empty string must default to Idle");
        assert_eq!(ContractState::from_str_lossy("IDLE"), ContractState::Idle,
            "AI Agent invariant: case-sensitive mismatch must default to Idle (not crash)");
    }

    // AI Agent verifies: Display impl is consistent with as_str
    #[test]
    fn test_contract_state_display() {
        let variants = [
            ContractState::Idle,
            ContractState::ManagerThinking,
            ContractState::Working,
            ContractState::Done,
            ContractState::Failed,
        ];
        for v in variants {
            assert_eq!(format!("{}", v), v.as_str(),
                "AI Agent invariant: Display must match as_str for {:?}", v);
        }
    }

    // AI Agent verifies: default OfficeState has all expected initial values
    #[test]
    fn test_office_state_default() {
        let state = OfficeState::default();
        assert_eq!(state.contract_state, ContractState::Idle, "AI Agent: default contract must be Idle");
        assert!(state.pending_contract.is_none(), "AI Agent: no pending contract at start");
        assert!(state.todos.is_empty(), "AI Agent: no todos at start");
        assert_eq!(state.revision_count, 0, "AI Agent: zero revisions at start");
        assert!(state.worker_events.is_empty(), "AI Agent: no worker events at start");
        assert_eq!(state.active_tab, WorkersTab::Workers, "AI Agent: default tab is Workers");
        assert_eq!(state.workers_list.len(), 13, "AI Agent: default workers list has 13 entries");
        assert!(state.manager_messages.is_empty(), "AI Agent: no messages at start");
        assert_eq!(state.manager_scroll, 0, "AI Agent: scroll starts at 0");
        assert!(state.input_text.is_empty(), "AI Agent: input text starts empty");
        assert_eq!(state.input_cursor, 0, "AI Agent: cursor starts at 0");
        assert!(!state.multiline_mode, "AI Agent: multiline off by default");
        assert!(state.input_focused, "AI Agent: input focused by default");
        assert!(!state.briefing_active, "AI Agent: briefing off by default");
        assert!(state.briefing_workers.is_empty(), "AI Agent: no briefing workers at start");
        assert!(state.briefing_messages.is_empty(), "AI Agent: no briefing messages at start");
        assert!(state.dag_nodes.is_empty(), "AI Agent: no dag nodes at start");
        assert!(state.event_log.is_empty(), "AI Agent: no event log at start");
        assert!(state.event_filter.is_none(), "AI Agent: no event filter at start");
        assert_eq!(state.event_scroll, 0, "AI Agent: event scroll starts at 0");
        assert!(state.llm_streaming_worker.is_none(), "AI Agent: no streaming worker at start");
        assert!(state.llm_stream_buffer.is_empty(), "AI Agent: stream buffer empty at start");
        assert!(!state.focus_mode, "AI Agent: focus mode off by default");
    }

    // AI Agent verifies: manager messages are capped at 500 (invariant: bounded queue)
    #[test]
    fn test_push_manager_message_cap() {
        let mut state = OfficeState::default();
        for i in 0..600 {
            state.push_manager_message("manager", &format!("msg {}", i));
        }
        assert!(state.manager_messages.len() <= 500,
            "AI Agent invariant: manager_messages must be capped at 500, got {}", state.manager_messages.len());
        assert_eq!(state.manager_messages.len(), 500,
            "AI Agent invariant: after 600 pushes, exactly 500 remain (oldest evicted)");
    }

    // AI Agent verifies: worker events are capped at 500 (invariant: bounded queue)
    #[test]
    fn test_push_worker_event_cap() {
        let mut state = OfficeState::default();
        for i in 0..600 {
            state.push_worker_event("worker_1", "task_done", &format!("output {}", i), None);
        }
        assert!(state.worker_events.len() <= 500,
            "AI Agent invariant: worker_events must be capped at 500, got {}", state.worker_events.len());
        assert_eq!(state.worker_events.len(), 500,
            "AI Agent invariant: after 600 pushes, exactly 500 remain");
    }

    // AI Agent verifies: event log is capped at 1000 (invariant: bounded log)
    #[test]
    fn test_push_log_event_cap() {
        let mut state = OfficeState::default();
        for i in 0..1100 {
            state.push_log_event("test", &format!("content {}", i), "info");
        }
        assert!(state.event_log.len() <= 1000,
            "AI Agent invariant: event_log must be capped at 1000, got {}", state.event_log.len());
        assert_eq!(state.event_log.len(), 1000,
            "AI Agent invariant: after 1100 pushes, exactly 1000 remain");
    }

    // AI Agent verifies: severity mapping follows business rules
    #[test]
    fn test_push_worker_event_severity() {
        let mut state = OfficeState::default();

        state.push_worker_event("w", "task_failed", "err", None);
        assert_eq!(state.event_log.back().unwrap().severity, "critical",
            "AI Agent: task_failed → critical severity");

        state.push_worker_event("w", "circuit_open", "err", None);
        assert_eq!(state.event_log.back().unwrap().severity, "critical",
            "AI Agent: circuit_open → critical severity");

        state.push_worker_event("w", "rate_limit", "err", None);
        assert_eq!(state.event_log.back().unwrap().severity, "critical",
            "AI Agent: rate_limit → critical severity");

        state.push_worker_event("w", "task_timeout", "err", None);
        assert_eq!(state.event_log.back().unwrap().severity, "warning",
            "AI Agent: task_timeout → warning severity");

        state.push_worker_event("w", "task_started", "ok", None);
        assert_eq!(state.event_log.back().unwrap().severity, "info",
            "AI Agent: task_started → info severity");

        state.push_worker_event("w", "task_done", "done", None);
        assert_eq!(state.event_log.back().unwrap().severity, "info",
            "AI Agent: task_done → info severity (default)");
    }

    // AI Agent verifies: DAG node deduplication (invariant: no duplicate task_ids)
    #[test]
    fn test_add_dag_node_if_needed() {
        let mut state = OfficeState::default();
        state.add_dag_node_if_needed("coder_backend", "task_abc12345");
        assert_eq!(state.dag_nodes.len(), 1, "AI Agent: first add creates a node");

        state.add_dag_node_if_needed("coder_frontend", "task_abc12345");
        assert_eq!(state.dag_nodes.len(), 1, "AI Agent invariant: duplicate task_id must not create a second node");

        state.add_dag_node_if_needed("coder_frontend", "task_def67890");
        assert_eq!(state.dag_nodes.len(), 2, "AI Agent: different task_id creates a new node");

        // Verify node content
        assert_eq!(state.dag_nodes[0].task_id.as_deref(), Some("task_abc12345"));
        assert_eq!(state.dag_nodes[0].worker_id, "coder_backend");
        assert_eq!(state.dag_nodes[0].status, "working");
    }

    // AI Agent verifies: DAG status updates correctly transition state
    #[test]
    fn test_update_dag_status() {
        let mut state = OfficeState::default();
        state.add_dag_node_if_needed("coder_backend", "task_abc12345");
        assert_eq!(state.dag_nodes[0].status, "working", "AI Agent: initial status is working");

        state.update_dag_status("task_abc12345", "done");
        assert_eq!(state.dag_nodes[0].status, "done", "AI Agent: status updated to done");

        state.update_dag_status("task_abc12345", "failed");
        assert_eq!(state.dag_nodes[0].status, "failed", "AI Agent: status updated to failed");

        // Nonexistent task_id should not panic
        state.update_dag_status("nonexistent_task", "done");
        assert_eq!(state.dag_nodes.len(), 1, "AI Agent: updating nonexistent task does not add nodes");
    }

    // AI Agent verifies: LLM streaming state transitions (worker switch → buffer reset)
    #[test]
    fn test_append_llm_chunk() {
        let mut state = OfficeState::default();

        // First chunk for worker A starts streaming
        state.append_llm_chunk("worker_a", "Hello ");
        assert_eq!(state.llm_streaming_worker.as_deref(), Some("worker_a"));
        assert_eq!(state.llm_stream_buffer, "Hello ");

        // Same worker: chunk appends
        state.append_llm_chunk("worker_a", "World");
        assert_eq!(state.llm_stream_buffer, "Hello World",
            "AI Agent invariant: same worker appends to buffer");

        // Switch to worker B: buffer resets
        state.append_llm_chunk("worker_b", "New");
        assert_eq!(state.llm_streaming_worker.as_deref(), Some("worker_b"),
            "AI Agent: streaming worker switches");
        assert_eq!(state.llm_stream_buffer, "New",
            "AI Agent invariant: switching workers resets the buffer");
    }

    // AI Agent verifies: briefing messages accumulate correctly
    #[test]
    fn test_add_briefing_msg() {
        let mut state = OfficeState::default();
        assert!(state.briefing_messages.is_empty());

        state.add_briefing_msg("system", "Briefing opened");
        assert_eq!(state.briefing_messages.len(), 1);
        assert_eq!(state.briefing_messages[0].speaker, "system");
        assert_eq!(state.briefing_messages[0].content, "Briefing opened");

        state.add_briefing_msg("coder_backend", "I'll handle the API");
        assert_eq!(state.briefing_messages.len(), 2);
        assert_eq!(state.briefing_messages[1].speaker, "coder_backend");
    }

    // AI Agent verifies: WorkersTab default is Workers
    #[test]
    fn test_workers_tab_default() {
        assert_eq!(WorkersTab::default(), WorkersTab::Workers,
            "AI Agent: default WorkersTab must be Workers");
    }

    // AI Agent verifies: scroll_up/scroll_down changes offset per tab
    #[test]
    fn test_scroll_offsets() {
        let mut state = OfficeState::default();

        // Workers tab → manager_scroll
        state.active_tab = WorkersTab::Workers;
        state.scroll_down();
        assert_eq!(state.manager_scroll, 3, "AI Agent: scroll_down on Workers tab increments manager_scroll");
        state.scroll_up();
        assert_eq!(state.manager_scroll, 0, "AI Agent: scroll_up on Workers tab decrements manager_scroll");

        // Events tab → event_scroll
        state.active_tab = WorkersTab::Events;
        state.scroll_down();
        assert_eq!(state.event_scroll, 3, "AI Agent: scroll_down on Events tab increments event_scroll");
        state.scroll_down();
        assert_eq!(state.event_scroll, 6, "AI Agent: second scroll_down increments to 6");
        state.scroll_up();
        assert_eq!(state.event_scroll, 3, "AI Agent: scroll_up on Events tab decrements event_scroll");
    }

    // AI Agent verifies: DagNode::find_by_task works recursively
    #[test]
    fn test_dag_node_find_by_task() {
        let node = DagNode {
            title: "Root".into(),
            worker_id: "w1".into(),
            task_id: Some("task_001".into()),
            status: "working".into(),
            children: vec![
                DagNode {
                    title: "Child".into(),
                    worker_id: "w2".into(),
                    task_id: Some("task_002".into()),
                    status: "done".into(),
                    children: vec![],
                },
            ],
        };
        assert!(node.find_by_task("task_001").is_some(), "AI Agent: find root task");
        assert!(node.find_by_task("task_002").is_some(), "AI Agent: find child task recursively");
        assert!(node.find_by_task("task_999").is_none(), "AI Agent: nonexistent task returns None");
    }
}
