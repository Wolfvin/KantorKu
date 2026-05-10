use crate::state::office_state::ContractState;
use crate::state::SettingsTab;
use crate::transport::types::BackendEvent;

/// Global application state
#[derive(Debug, Clone)]
#[allow(dead_code)] // State fields accessed by render methods
pub struct AppState {
    pub office_state: crate::state::office_state::OfficeState,
    pub library_state: crate::state::library_state::LibraryState,
    pub connection_state: ConnectionState,
    pub session_id: Option<String>,
    pub active_workers: usize,
    pub cost_usd: f64,
    pub total_calls: u64,

    // Overlay state
    pub command_palette_open: bool,
    pub command_palette_query: String,
    pub command_palette_selection: usize,
    pub settings_open: bool,
    pub settings_tab: SettingsTab,
    pub settings_selection: usize,

    // Notification
    pub last_notification: Option<Notification>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Error(String),
}

#[derive(Debug, Clone)]
pub struct Notification {
    pub message: String,
    pub severity: NotificationSeverity,
    pub tick: u64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum NotificationSeverity {
    Info,
    Warning,
    Error,
}

/// Command palette command entry
#[derive(Debug, Clone)]
pub struct CommandEntry {
    pub label: String,
    pub description: String,
    pub action: String,
    pub mode: CommandMode,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CommandMode {
    Global,
    Office,
    Library,
    Symbolic,
    Losion,
    Gpu,
}

impl AppState {
    pub fn all_commands() -> Vec<CommandEntry> {
        vec![
            CommandEntry { label: "Switch to Office".into(), description: "Go to Office mode".into(), action: "switch_office".into(), mode: CommandMode::Global },
            CommandEntry { label: "Switch to Library".into(), description: "Go to Library mode".into(), action: "switch_library".into(), mode: CommandMode::Global },
            CommandEntry { label: "Switch to Symbolic".into(), description: "Go to Symbolic mode".into(), action: "switch_symbolic".into(), mode: CommandMode::Global },
            CommandEntry { label: "Switch to Losion".into(), description: "Go to Losion mode".into(), action: "switch_losion".into(), mode: CommandMode::Global },
            CommandEntry { label: "Switch to GPU".into(), description: "Go to GPU mode".into(), action: "switch_gpu".into(), mode: CommandMode::Global },
            CommandEntry { label: "Toggle Theme".into(), description: "Cycle through themes".into(), action: "toggle_theme".into(), mode: CommandMode::Global },
            CommandEntry { label: "Open Settings".into(), description: "Configure workers, theme, keybindings".into(), action: "open_settings".into(), mode: CommandMode::Global },
            CommandEntry { label: "Clear Chat".into(), description: "Clear manager chat history".into(), action: "clear_chat".into(), mode: CommandMode::Office },
            CommandEntry { label: "Focus Mode".into(), description: "Toggle focus mode".into(), action: "focus_mode".into(), mode: CommandMode::Office },
            CommandEntry { label: "Ingest Entry".into(), description: "Add new entry to Library".into(), action: "ingest".into(), mode: CommandMode::Library },
            CommandEntry { label: "Ask Archivist".into(), description: "Query the Library".into(), action: "ask".into(), mode: CommandMode::Library },
            CommandEntry { label: "Browse Library".into(), description: "Browse shelves and entries".into(), action: "browse".into(), mode: CommandMode::Library },
            CommandEntry { label: "Save Config".into(), description: "Save current settings to disk".into(), action: "save_config".into(), mode: CommandMode::Global },
            CommandEntry { label: "Quit".into(), description: "Exit Fought TUI".into(), action: "quit".into(), mode: CommandMode::Global },
        ]
    }

    pub fn filtered_commands(&self) -> Vec<CommandEntry> {
        let query = self.command_palette_query.to_lowercase();
        Self::all_commands().into_iter().filter(|cmd| {
            if query.is_empty() { return true; }
            cmd.label.to_lowercase().contains(&query)
                || cmd.description.to_lowercase().contains(&query)
                || cmd.action.to_lowercase().contains(&query)
        }).collect()
    }

    pub fn notify(&mut self, message: String, severity: NotificationSeverity, tick: u64) {
        self.last_notification = Some(Notification { message, severity, tick });
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            office_state: crate::state::office_state::OfficeState::default(),
            library_state: crate::state::library_state::LibraryState::default(),
            connection_state: ConnectionState::Disconnected,
            session_id: None,
            active_workers: 0,
            cost_usd: 0.0,
            total_calls: 0,
            command_palette_open: false,
            command_palette_query: String::new(),
            command_palette_selection: 0,
            settings_open: false,
            settings_tab: SettingsTab::Workers,
            settings_selection: 0,
            last_notification: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: default AppState has all expected initial values
    #[test]
    fn test_app_state_default() {
        let state = AppState::default();
        assert_eq!(state.connection_state, ConnectionState::Disconnected,
            "AI Agent: default connection is Disconnected");
        assert!(state.session_id.is_none(), "AI Agent: no session at start");
        assert_eq!(state.active_workers, 0, "AI Agent: zero active workers at start");
        assert_eq!(state.cost_usd, 0.0, "AI Agent: zero cost at start");
        assert_eq!(state.total_calls, 0, "AI Agent: zero calls at start");
        assert!(!state.command_palette_open, "AI Agent: command palette closed by default");
        assert!(state.command_palette_query.is_empty(), "AI Agent: query empty at start");
        assert_eq!(state.command_palette_selection, 0, "AI Agent: selection starts at 0");
        assert!(!state.settings_open, "AI Agent: settings closed by default");
        assert_eq!(state.settings_tab, SettingsTab::Workers, "AI Agent: default settings tab is Workers");
        assert_eq!(state.settings_selection, 0, "AI Agent: settings selection starts at 0");
        assert!(state.last_notification.is_none(), "AI Agent: no notification at start");
    }

    // AI Agent verifies: all_commands returns a non-empty list with expected entries
    #[test]
    fn test_all_commands() {
        let cmds = AppState::all_commands();
        assert!(!cmds.is_empty(), "AI Agent: command list must not be empty");
        assert!(cmds.len() >= 10, "AI Agent: at least 10 commands expected, got {}", cmds.len());

        // AI Agent invariant: each command has non-empty label, description, and action
        for cmd in &cmds {
            assert!(!cmd.label.is_empty(), "AI Agent: command label must not be empty");
            assert!(!cmd.description.is_empty(), "AI Agent: command description must not be empty");
            assert!(!cmd.action.is_empty(), "AI Agent: command action must not be empty");
        }

        // Verify key commands exist
        assert!(cmds.iter().any(|c| c.action == "toggle_theme"), "AI Agent: toggle_theme command must exist");
        assert!(cmds.iter().any(|c| c.action == "quit"), "AI Agent: quit command must exist");
        assert!(cmds.iter().any(|c| c.action == "switch_office"), "AI Agent: switch_office must exist");
        assert!(cmds.iter().any(|c| c.action == "switch_library"), "AI Agent: switch_library must exist");
    }

    // AI Agent verifies: empty query returns all commands
    #[test]
    fn test_filtered_commands_empty_query() {
        let mut state = AppState::default();
        state.command_palette_query = String::new();
        let filtered = state.filtered_commands();
        assert_eq!(filtered.len(), AppState::all_commands().len(),
            "AI Agent invariant: empty query must return all commands");
    }

    // AI Agent verifies: query "theme" returns the Toggle Theme command
    #[test]
    fn test_filtered_commands_match() {
        let mut state = AppState::default();
        state.command_palette_query = "theme".to_string();
        let filtered = state.filtered_commands();
        assert!(!filtered.is_empty(), "AI Agent: 'theme' query must return results");
        assert!(filtered.iter().any(|c| c.action == "toggle_theme"),
            "AI Agent: 'theme' query must find Toggle Theme");
    }

    // AI Agent verifies: nonsensical query returns empty
    #[test]
    fn test_filtered_commands_no_match() {
        let mut state = AppState::default();
        state.command_palette_query = "xyzzy_nonexistent".to_string();
        let filtered = state.filtered_commands();
        assert!(filtered.is_empty(),
            "AI Agent invariant: no matching query must return empty list");
    }

    // AI Agent verifies: notify sets the notification correctly
    #[test]
    fn test_notify() {
        let mut state = AppState::default();
        assert!(state.last_notification.is_none(), "AI Agent: no notification initially");

        state.notify("Test message".to_string(), NotificationSeverity::Info, 42);
        let n = state.last_notification.as_ref().unwrap();
        assert_eq!(n.message, "Test message", "AI Agent: notification message preserved");
        assert_eq!(n.severity, NotificationSeverity::Info, "AI Agent: notification severity preserved");
        assert_eq!(n.tick, 42, "AI Agent: notification tick preserved in Notification struct");
    }

    // AI Agent verifies: ConnectionState variants are constructible and PartialEq
    #[test]
    fn test_connection_state() {
        assert_eq!(ConnectionState::Disconnected, ConnectionState::Disconnected);
        assert_eq!(ConnectionState::Connecting, ConnectionState::Connecting);
        assert_eq!(ConnectionState::Connected, ConnectionState::Connected);
        assert_eq!(ConnectionState::Error("err".into()), ConnectionState::Error("err".into()));
        assert_ne!(ConnectionState::Connected, ConnectionState::Disconnected);
    }

    // AI Agent verifies: WsConnected event changes connection state to Connected
    #[test]
    fn test_handle_backend_event_ws_connected() {
        let mut state = AppState::default();
        assert_eq!(state.connection_state, ConnectionState::Disconnected);
        state.handle_backend_event(BackendEvent::WsConnected);
        assert_eq!(state.connection_state, ConnectionState::Connected,
            "AI Agent invariant: WsConnected must set ConnectionState::Connected");
        assert!(state.last_notification.is_some(), "AI Agent: notification should be set on connect");
    }

    // AI Agent verifies: ContractReady event changes contract state
    #[test]
    fn test_handle_backend_event_contract_ready() {
        let mut state = AppState::default();
        let contract = crate::state::office_state::Contract {
            title: "Test Contract".into(),
            description: "A test".into(),
            todos: vec![],
            estimated_cost: Some(0.5),
            workers: vec!["coder_backend".into()],
        };
        state.handle_backend_event(BackendEvent::ContractReady {
            contract: contract.clone(),
            session_id: "sess_123".into(),
        });
        assert_eq!(state.office_state.contract_state, ContractState::ContractPresented,
            "AI Agent invariant: ContractReady must set ContractPresented");
        assert!(state.office_state.pending_contract.is_some(),
            "AI Agent: pending_contract must be set after ContractReady");
        assert_eq!(state.session_id.as_deref(), Some("sess_123"),
            "AI Agent: session_id must be captured from ContractReady");
    }

    // AI Agent verifies: TaskStarted increments and TaskDone decrements active_workers
    #[test]
    fn test_handle_backend_event_task_started_done() {
        let mut state = AppState::default();
        assert_eq!(state.active_workers, 0);

        state.handle_backend_event(BackendEvent::TaskStarted {
            worker_id: "coder_backend".into(),
            task_id: "task_001".into(),
        });
        assert_eq!(state.active_workers, 1,
            "AI Agent invariant: TaskStarted must increment active_workers");

        state.handle_backend_event(BackendEvent::TaskStarted {
            worker_id: "coder_frontend".into(),
            task_id: "task_002".into(),
        });
        assert_eq!(state.active_workers, 2,
            "AI Agent: second TaskStarted increments to 2");

        state.handle_backend_event(BackendEvent::TaskDone {
            worker_id: "coder_backend".into(),
            task_id: "task_001".into(),
            output: "done!".into(),
        });
        assert_eq!(state.active_workers, 1,
            "AI Agent invariant: TaskDone must decrement active_workers");
    }

    // AI Agent verifies: LibraryIngestStarted changes ingest step to Analyzing
    #[test]
    fn test_handle_backend_event_library_ingest() {
        let mut state = AppState::default();
        assert_eq!(state.library_state.ingest_step, crate::state::library_state::IngestStep::Input);

        state.handle_backend_event(BackendEvent::LibraryIngestStarted {
            entry_id: "e1".into(),
        });
        assert_eq!(state.library_state.ingest_step, crate::state::library_state::IngestStep::Analyzing,
            "AI Agent: LibraryIngestStarted must set Analyzing step");

        // LibraryIngestDone sets Done and increments entry_count
        let entry = Box::new(crate::state::library_state::LibraryEntry {
            id: "e1".into(),
            created_at: "2024-01-01".into(),
            updated_at: "2024-01-01".into(),
            source: "test".into(),
            title: "Test Entry".into(),
            content: "Some content".into(),
            summary: "Summary".into(),
            keywords: vec![],
            entry_type: "knowledge".into(),
            domain: "web_text".into(),
            lang: "en".into(),
            shelf_path: vec!["Engineering".into()],
            shelf_confidence: 0.9,
            related_ids: vec![],
            supersedes_id: None,
            solution_for: None,
            quality_score: 0.85,
            verified: false,
            usage_count: 0,
            was_helpful: 0,
            was_unhelpful: 0,
            origin_session_id: None,
            origin_worker_id: None,
            origin_task_id: None,
            problem_description: None,
            failed_attempts: vec![],
            solution_code: None,
            verification_result: None,
            question: None,
            answer: None,
            source_entry_ids: vec![],
            steps: vec![],
        });
        let prev_count = state.library_state.entry_count;
        state.handle_backend_event(BackendEvent::LibraryIngestDone { entry });
        assert_eq!(state.library_state.ingest_step, crate::state::library_state::IngestStep::Done,
            "AI Agent: LibraryIngestDone must set Done step");
        assert_eq!(state.library_state.entry_count, prev_count + 1,
            "AI Agent: LibraryIngestDone must increment entry_count");
        assert!(state.library_state.current_entry.is_some(),
            "AI Agent: current_entry must be set after LibraryIngestDone");

        // LibraryIngestFailed resets to Input
        state.library_state.ingest_step = crate::state::library_state::IngestStep::Analyzing;
        state.handle_backend_event(BackendEvent::LibraryIngestFailed { error: "bad".into() });
        assert_eq!(state.library_state.ingest_step, crate::state::library_state::IngestStep::Input,
            "AI Agent: LibraryIngestFailed must reset to Input step");
    }

    // AI Agent verifies: CommandMode variants exist and are PartialEq
    #[test]
    fn test_command_mode_variants() {
        assert_eq!(CommandMode::Global, CommandMode::Global);
        assert_eq!(CommandMode::Office, CommandMode::Office);
        assert_eq!(CommandMode::Library, CommandMode::Library);
        assert_ne!(CommandMode::Global, CommandMode::Office);
    }

    // AI Agent verifies: NotificationSeverity variants are distinct
    #[test]
    fn test_notification_severity_variants() {
        assert_eq!(NotificationSeverity::Info, NotificationSeverity::Info);
        assert_ne!(NotificationSeverity::Info, NotificationSeverity::Warning);
        assert_ne!(NotificationSeverity::Warning, NotificationSeverity::Error);
    }

    // AI Agent verifies: WsConnecting sets ConnectionState::Connecting
    #[test]
    fn test_handle_backend_event_ws_connecting() {
        let mut state = AppState::default();
        state.handle_backend_event(BackendEvent::WsConnecting);
        assert_eq!(state.connection_state, ConnectionState::Connecting,
            "AI Agent: WsConnecting must set Connecting state");
    }

    // AI Agent verifies: WsDisconnected sets ConnectionState::Disconnected
    #[test]
    fn test_handle_backend_event_ws_disconnected() {
        let mut state = AppState::default();
        state.connection_state = ConnectionState::Connected;
        state.handle_backend_event(BackendEvent::WsDisconnected);
        assert_eq!(state.connection_state, ConnectionState::Disconnected,
            "AI Agent: WsDisconnected must set Disconnected state");
    }

    // AI Agent verifies: Error event sets connection error state
    #[test]
    fn test_handle_backend_event_error() {
        let mut state = AppState::default();
        state.handle_backend_event(BackendEvent::Error { message: "test error".into() });
        assert_eq!(state.connection_state, ConnectionState::Error("test error".into()),
            "AI Agent: Error event must set Error connection state");
    }

    // AI Agent verifies: WsError event sets connection error state with message
    #[test]
    fn test_handle_backend_event_ws_error() {
        let mut state = AppState::default();
        state.handle_backend_event(BackendEvent::WsError { message: "Max reconnect attempts reached".into() });
        assert_eq!(state.connection_state, ConnectionState::Error("Max reconnect attempts reached".into()),
            "AI Agent: WsError must set Error connection state with message");
        assert!(state.last_notification.is_some(),
            "AI Agent: WsError must trigger a notification");
    }
}

impl AppState {
    pub fn handle_backend_event(&mut self, event: BackendEvent) {
        match &event {
            // === Connection events ===
            BackendEvent::Error { message } => {
                self.connection_state = ConnectionState::Error(message.clone());
                self.notify(message.clone(), NotificationSeverity::Error, 0);
            }
            BackendEvent::WsConnected => {
                self.connection_state = ConnectionState::Connected;
                self.notify("Connected to backend".into(), NotificationSeverity::Info, 0);
            }
            BackendEvent::WsConnecting => {
                self.connection_state = ConnectionState::Connecting;
            }
            BackendEvent::WsDisconnected => {
                self.connection_state = ConnectionState::Disconnected;
                self.notify("Disconnected from backend".into(), NotificationSeverity::Warning, 0);
            }
            BackendEvent::WsError { message } => {
                self.connection_state = ConnectionState::Error(message.clone());
                self.notify(format!("WebSocket error: {message}"), NotificationSeverity::Error, 0);
            }

            // === Contract lifecycle ===
            BackendEvent::ContractReady { contract, session_id } => {
                self.office_state.pending_contract = Some(contract.clone());
                self.office_state.contract_state = ContractState::ContractPresented;
                self.session_id = Some(session_id.clone());
            }
            BackendEvent::ContractStateChange { state, session_id } => {
                self.office_state.contract_state = ContractState::from_str_lossy(state);
                if self.session_id.is_none() {
                    self.session_id = Some(session_id.clone());
                }
            }
            BackendEvent::ContractAccepted { session_id: _ } => {
                self.office_state.contract_state = ContractState::Accepted;
            }
            BackendEvent::WorkStarted { session_id } => {
                self.office_state.contract_state = ContractState::Working;
                if self.session_id.is_none() {
                    self.session_id = Some(session_id.clone());
                }
            }
            BackendEvent::WorkDone { result: _, session_id: _ } => {
                self.office_state.contract_state = ContractState::Done;
            }

            // === Manager messages ===
            BackendEvent::ManagerMessage { content, session_id: _ }
            | BackendEvent::ManagerQuestion { content, session_id: _ } => {
                self.office_state.push_manager_message("manager", content);
            }
            BackendEvent::ManagerBrainstorming { content, session_id: _ } => {
                self.office_state.push_manager_message("thinking", content);
            }
            BackendEvent::RevisionRequested { feedback, session_id: _ } => {
                self.office_state.contract_state = ContractState::AwaitingRevision;
                self.office_state.push_manager_message("manager", &format!("Revision requested: {feedback}"));
            }

            // === Worker events ===
            BackendEvent::TaskAssigned { worker_id, task, session_id: _ } => {
                self.office_state.push_worker_event(worker_id, "task_assigned", task, None);
            }
            BackendEvent::TaskStarted { worker_id, task_id } => {
                self.active_workers = self.active_workers.saturating_add(1);
                self.office_state.push_worker_event(worker_id, "task_started", "", Some(task_id));
                self.office_state.add_dag_node_if_needed(worker_id, task_id);
            }
            BackendEvent::TaskDone { worker_id, task_id, output } => {
                self.active_workers = self.active_workers.saturating_sub(1);
                let short = if output.len() > 120 {
                    // Use char-boundary-safe truncation to avoid panicking on multi-byte UTF-8
                    let truncated: String = output.chars().take(117).collect();
                    format!("{}...", truncated)
                } else {
                    output.clone()
                };
                self.office_state.push_worker_event(worker_id, "task_done", &short, Some(task_id));
                self.office_state.update_dag_status(task_id, "done");
            }
            BackendEvent::TaskFailed { worker_id, task_id, error } => {
                self.active_workers = self.active_workers.saturating_sub(1);
                self.office_state.push_worker_event(worker_id, "task_failed", error, Some(task_id));
                self.office_state.update_dag_status(task_id, "failed");
            }
            BackendEvent::TaskRecovered { worker_id, task_id } => {
                self.office_state.push_worker_event(worker_id, "task_recovered", "recovered", Some(task_id));
                self.office_state.update_dag_status(task_id, "working");
            }
            BackendEvent::TaskTimeout { worker_id, task_id } => {
                self.office_state.push_worker_event(worker_id, "task_timeout", "timed out", Some(task_id));
                self.office_state.update_dag_status(task_id, "failed");
            }

            // === LLM streaming ===
            BackendEvent::LlmStreamStart { worker_id, task_id } => {
                self.office_state.push_worker_event(worker_id, "llm_start", "streaming...", Some(task_id));
                self.office_state.update_dag_status(task_id, "working");
            }
            BackendEvent::LlmStreamChunk { worker_id, task_id: _, chunk } => {
                self.office_state.append_llm_chunk(worker_id, chunk);
            }
            BackendEvent::LlmStreamDone { worker_id, task_id: _ } => {
                self.office_state.push_worker_event(worker_id, "llm_done", "", None);
            }

            // === Briefing ===
            BackendEvent::BriefingOpened { workers, session_id: _ } => {
                self.office_state.briefing_active = true;
                self.office_state.briefing_workers = workers.clone();
                self.office_state.add_briefing_msg("system", &format!("Briefing opened: {}", workers.join(", ")));
            }
            BackendEvent::WorkerSpeakUp { worker_id, content, msg_type: _ } => {
                self.office_state.add_briefing_msg(worker_id, content);
                self.office_state.push_worker_event(worker_id, "speak_up", content, None);
            }
            BackendEvent::PlanDrafted { plan, session_id: _ } => {
                self.office_state.add_briefing_msg("system", &format!("Plan drafted:\n{plan}"));
            }
            BackendEvent::PlanRevised { plan, round, session_id: _ } => {
                self.office_state.add_briefing_msg("system", &format!("Plan revised (round {round}):\n{plan}"));
            }

            // === Delegation ===
            BackendEvent::DelegationRequest { from, to, instruction } => {
                self.office_state.push_worker_event(from, "delegation_request", &format!("{to}: {instruction}"), None);
            }
            BackendEvent::DelegationResult { from, to: _, status, output } => {
                self.office_state.push_worker_event(from, "delegation_result", &format!("{status}: {output}"), None);
            }
            BackendEvent::WorkerDm { from_id, to_id: _, message } => {
                self.office_state.push_worker_event(from_id, "dm", message, None);
            }
            BackendEvent::WorkerBroadcast { from_id, message } => {
                self.office_state.push_worker_event(from_id, "broadcast", message, None);
            }

            // === Cost/Rate/Circuit ===
            BackendEvent::CostWarning { current, limit: _ } => {
                self.cost_usd = *current;
                self.total_calls += 1;
            }
            BackendEvent::RateLimitHit { worker_id } => {
                self.office_state.push_worker_event(worker_id, "rate_limit", "rate limited", None);
            }
            BackendEvent::CircuitOpen { worker_id } => {
                self.office_state.push_worker_event(worker_id, "circuit_open", "circuit breaker opened", None);
            }
            BackendEvent::CircuitClosed { worker_id } => {
                self.office_state.push_worker_event(worker_id, "circuit_closed", "circuit breaker closed", None);
            }

            // === Misc ===
            BackendEvent::WorkerHired { worker_id } => {
                self.office_state.workers_list.push(worker_id.clone());
            }
            BackendEvent::WorkerFired { worker_id } => {
                self.office_state.workers_list.retain(|w| w != worker_id);
            }
            BackendEvent::CheckpointSaved { session_id: _ } => {}
            BackendEvent::CrashRecovered { session_id: _ } => {}
            BackendEvent::SkillUpdated { worker_id, skill: _ } => {
                self.office_state.push_worker_event(worker_id, "skill_updated", "", None);
            }
            BackendEvent::VerifyDesignStart { worker_id } => {
                self.office_state.push_worker_event(worker_id, "verify_design_start", "verifying design...", None);
            }
            BackendEvent::VerifyDesignDone { worker_id } => {
                self.office_state.push_worker_event(worker_id, "verify_design_done", "design verified", None);
            }
            BackendEvent::VerifyEngineerStart { worker_id } => {
                self.office_state.push_worker_event(worker_id, "verify_engineer_start", "verifying engineering...", None);
            }
            BackendEvent::VerifyEngineerDone { worker_id } => {
                self.office_state.push_worker_event(worker_id, "verify_engineer_done", "engineering verified", None);
            }
            BackendEvent::ContextFetchStart { worker_id } => {
                self.office_state.push_worker_event(worker_id, "context_fetch_start", "fetching context...", None);
            }
            BackendEvent::ContextFetchDone { worker_id } => {
                self.office_state.push_worker_event(worker_id, "context_fetch_done", "context fetched", None);
            }
            BackendEvent::ErrorLogged { message, severity } => {
                self.office_state.push_log_event("error_logged", message, severity);
            }

            // === Library events ===
            BackendEvent::LibraryIngestStarted { entry_id: _ } => {
                self.library_state.ingest_step = crate::state::library_state::IngestStep::Analyzing;
            }
            BackendEvent::LibraryIngestDone { entry } => {
                self.library_state.current_entry = Some((**entry).clone());
                self.library_state.ingest_step = crate::state::library_state::IngestStep::Done;
                self.library_state.entry_count += 1;
            }
            BackendEvent::LibraryIngestFailed { error } => {
                self.library_state.ingest_step = crate::state::library_state::IngestStep::Input;
                tracing::error!("Library ingest failed: {error}");
            }
            BackendEvent::LibraryShelfCreated { shelf_path: _ } => {
                self.library_state.shelf_count += 1;
            }
            BackendEvent::LibraryQueryStarted { query_id: _ } => {
                // Will stream chunks
            }
            BackendEvent::LibraryQueryChunk { query_id: _, chunk } => {
                self.library_state.archivist_streaming.push(chunk.clone());
            }
            BackendEvent::LibraryQueryDone { query_id: _, sources } => {
                let full_answer = self.library_state.archivist_streaming.drain(..).collect::<Vec<_>>().join("");
                self.library_state.ask_history.push(crate::state::library_state::AskMessage {
                    role: "archivist".to_string(),
                    content: full_answer,
                    sources: sources.clone(),
                    timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                });
                self.library_state.archivist_sources = sources.clone();
                self.library_state.archivist_streaming.clear();
            }

            // === TUI-specific feedback events (from async actions) ===
            BackendEvent::ShelfEntriesLoaded { path: _, entries } => {
                self.library_state.current_entries = entries.clone();
            }
            BackendEvent::EntryLoaded { entry } => {
                self.library_state.current_entry = Some((**entry).clone());
            }
            BackendEvent::SearchResultsLoaded { query: _, results } => {
                self.library_state.search_results = results.clone();
                self.library_state.search_mode = true;
            }
        }
    }
}
