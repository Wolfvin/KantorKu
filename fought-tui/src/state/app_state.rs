use crate::state::kantor_state::ContractState;
use crate::state::SettingsTab;
use crate::transport::types::BackendEvent;

/// Global application state
#[derive(Debug, Clone)]
#[allow(dead_code)] // State fields accessed by render methods
pub struct AppState {
    pub kantor_state: crate::state::kantor_state::KantorState,
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
    pub notification_tick: u64,
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
    Kantor,
    Library,
}

impl AppState {
    pub fn all_commands() -> Vec<CommandEntry> {
        vec![
            CommandEntry { label: "Switch to Kantor".into(), description: "Go to Kantor mode".into(), action: "switch_kantor".into(), mode: CommandMode::Global },
            CommandEntry { label: "Switch to Library".into(), description: "Go to Library mode".into(), action: "switch_library".into(), mode: CommandMode::Global },
            CommandEntry { label: "Toggle Theme".into(), description: "Cycle through themes".into(), action: "toggle_theme".into(), mode: CommandMode::Global },
            CommandEntry { label: "Open Settings".into(), description: "Configure workers, theme, keybindings".into(), action: "open_settings".into(), mode: CommandMode::Global },
            CommandEntry { label: "Clear Chat".into(), description: "Clear manager chat history".into(), action: "clear_chat".into(), mode: CommandMode::Kantor },
            CommandEntry { label: "Focus Mode".into(), description: "Toggle focus mode".into(), action: "focus_mode".into(), mode: CommandMode::Kantor },
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
        self.notification_tick = tick;
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            kantor_state: crate::state::kantor_state::KantorState::default(),
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
            notification_tick: 0,
        }
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

            // === Contract lifecycle ===
            BackendEvent::ContractReady { contract, session_id } => {
                self.kantor_state.pending_contract = Some(contract.clone());
                self.kantor_state.contract_state = ContractState::ContractPresented;
                self.session_id = Some(session_id.clone());
            }
            BackendEvent::ContractStateChange { state, session_id } => {
                self.kantor_state.contract_state = ContractState::from_str_lossy(state);
                if self.session_id.is_none() {
                    self.session_id = Some(session_id.clone());
                }
            }
            BackendEvent::ContractAccepted { session_id: _ } => {
                self.kantor_state.contract_state = ContractState::Accepted;
            }
            BackendEvent::WorkStarted { session_id } => {
                self.kantor_state.contract_state = ContractState::Working;
                if self.session_id.is_none() {
                    self.session_id = Some(session_id.clone());
                }
            }
            BackendEvent::WorkDone { result: _, session_id: _ } => {
                self.kantor_state.contract_state = ContractState::Done;
            }

            // === Manager messages ===
            BackendEvent::ManagerMessage { content, session_id: _ }
            | BackendEvent::ManagerQuestion { content, session_id: _ } => {
                self.kantor_state.push_manager_message("manager", content);
            }
            BackendEvent::ManagerBrainstorming { content, session_id: _ } => {
                self.kantor_state.push_manager_message("thinking", content);
            }
            BackendEvent::RevisionRequested { feedback, session_id: _ } => {
                self.kantor_state.contract_state = ContractState::AwaitingRevision;
                self.kantor_state.push_manager_message("manager", &format!("Revision requested: {feedback}"));
            }

            // === Worker events ===
            BackendEvent::TaskAssigned { worker_id, task, session_id: _ } => {
                self.kantor_state.push_worker_event(worker_id, "task_assigned", task, None);
            }
            BackendEvent::TaskStarted { worker_id, task_id } => {
                self.active_workers = self.active_workers.saturating_add(1);
                self.kantor_state.push_worker_event(worker_id, "task_started", "", Some(task_id));
                self.kantor_state.add_dag_node_if_needed(worker_id, task_id);
            }
            BackendEvent::TaskDone { worker_id, task_id, output } => {
                self.active_workers = self.active_workers.saturating_sub(1);
                let short = if output.len() > 120 { format!("{}...", &output[..117]) } else { output.clone() };
                self.kantor_state.push_worker_event(worker_id, "task_done", &short, Some(task_id));
                self.kantor_state.update_dag_status(task_id, "done");
            }
            BackendEvent::TaskFailed { worker_id, task_id, error } => {
                self.active_workers = self.active_workers.saturating_sub(1);
                self.kantor_state.push_worker_event(worker_id, "task_failed", error, Some(task_id));
                self.kantor_state.update_dag_status(task_id, "failed");
            }
            BackendEvent::TaskRecovered { worker_id, task_id } => {
                self.kantor_state.push_worker_event(worker_id, "task_recovered", "recovered", Some(task_id));
                self.kantor_state.update_dag_status(task_id, "working");
            }
            BackendEvent::TaskTimeout { worker_id, task_id } => {
                self.kantor_state.push_worker_event(worker_id, "task_timeout", "timed out", Some(task_id));
                self.kantor_state.update_dag_status(task_id, "failed");
            }

            // === LLM streaming ===
            BackendEvent::LlmStreamStart { worker_id, task_id } => {
                self.kantor_state.push_worker_event(worker_id, "llm_start", "streaming...", Some(task_id));
                self.kantor_state.update_dag_status(task_id, "working");
            }
            BackendEvent::LlmStreamChunk { worker_id, task_id: _, chunk } => {
                self.kantor_state.append_llm_chunk(worker_id, chunk);
            }
            BackendEvent::LlmStreamDone { worker_id, task_id: _ } => {
                self.kantor_state.push_worker_event(worker_id, "llm_done", "", None);
            }

            // === Briefing ===
            BackendEvent::BriefingOpened { workers, session_id: _ } => {
                self.kantor_state.briefing_active = true;
                self.kantor_state.briefing_workers = workers.clone();
                self.kantor_state.add_briefing_msg("system", &format!("Briefing opened: {}", workers.join(", ")));
            }
            BackendEvent::WorkerSpeakUp { worker_id, content, msg_type: _ } => {
                self.kantor_state.add_briefing_msg(worker_id, content);
                self.kantor_state.push_worker_event(worker_id, "speak_up", content, None);
            }
            BackendEvent::PlanDrafted { plan, session_id: _ } => {
                self.kantor_state.add_briefing_msg("system", &format!("Plan drafted:\n{plan}"));
            }
            BackendEvent::PlanRevised { plan, round, session_id: _ } => {
                self.kantor_state.add_briefing_msg("system", &format!("Plan revised (round {round}):\n{plan}"));
            }

            // === Delegation ===
            BackendEvent::DelegationRequest { from, to, instruction } => {
                self.kantor_state.push_worker_event(from, "delegation_request", &format!("{to}: {instruction}"), None);
            }
            BackendEvent::DelegationResult { from, to: _, status, output } => {
                self.kantor_state.push_worker_event(from, "delegation_result", &format!("{status}: {output}"), None);
            }
            BackendEvent::WorkerDm { from_id, to_id: _, message } => {
                self.kantor_state.push_worker_event(from_id, "dm", message, None);
            }
            BackendEvent::WorkerBroadcast { from_id, message } => {
                self.kantor_state.push_worker_event(from_id, "broadcast", message, None);
            }

            // === Cost/Rate/Circuit ===
            BackendEvent::CostWarning { current, limit: _ } => {
                self.cost_usd = *current;
                self.total_calls += 1;
            }
            BackendEvent::RateLimitHit { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "rate_limit", "rate limited", None);
            }
            BackendEvent::CircuitOpen { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "circuit_open", "circuit breaker opened", None);
            }
            BackendEvent::CircuitClosed { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "circuit_closed", "circuit breaker closed", None);
            }

            // === Misc ===
            BackendEvent::WorkerHired { worker_id } => {
                self.kantor_state.workers_list.push(worker_id.clone());
            }
            BackendEvent::WorkerFired { worker_id } => {
                self.kantor_state.workers_list.retain(|w| w != worker_id);
            }
            BackendEvent::CheckpointSaved { session_id: _ } => {}
            BackendEvent::CrashRecovered { session_id: _ } => {}
            BackendEvent::SkillUpdated { worker_id, skill: _ } => {
                self.kantor_state.push_worker_event(worker_id, "skill_updated", "", None);
            }
            BackendEvent::VerifyDesignStart { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "verify_design_start", "verifying design...", None);
            }
            BackendEvent::VerifyDesignDone { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "verify_design_done", "design verified", None);
            }
            BackendEvent::VerifyEngineerStart { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "verify_engineer_start", "verifying engineering...", None);
            }
            BackendEvent::VerifyEngineerDone { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "verify_engineer_done", "engineering verified", None);
            }
            BackendEvent::ContextFetchStart { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "context_fetch_start", "fetching context...", None);
            }
            BackendEvent::ContextFetchDone { worker_id } => {
                self.kantor_state.push_worker_event(worker_id, "context_fetch_done", "context fetched", None);
            }
            BackendEvent::ErrorLogged { message, severity } => {
                self.kantor_state.push_log_event("error_logged", message, severity);
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
