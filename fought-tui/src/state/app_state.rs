use super::KantorState;
use super::LibraryState;
use crate::transport::types::BackendEvent;

/// Global application state
#[derive(Debug, Clone)]
pub struct AppState {
    pub kantor_state: KantorState,
    pub library_state: LibraryState,
    pub connection_state: ConnectionState,
    pub session_id: Option<String>,
    pub active_workers: usize,
    pub cost_usd: f64,
    pub current_theme_name: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Error,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            kantor_state: KantorState::default(),
            library_state: LibraryState::default(),
            connection_state: ConnectionState::Disconnected,
            session_id: None,
            active_workers: 0,
            cost_usd: 0.0,
            current_theme_name: "office_dark".to_string(),
        }
    }
}

impl AppState {
    pub fn handle_backend_event(&mut self, event: BackendEvent) {
        match &event {
            BackendEvent::ContractStateChange { state, session_id } => {
                self.kantor_state.contract_state = state.clone();
                if self.session_id.is_none() {
                    self.session_id = Some(session_id.clone());
                }
            }
            BackendEvent::ContractReady { contract, session_id } => {
                self.kantor_state.pending_contract = Some(contract.clone());
                self.kantor_state.contract_state = "contract_presented".to_string();
                self.session_id = Some(session_id.clone());
            }
            BackendEvent::ContractAccepted { session_id } => {
                self.kantor_state.contract_state = "accepted".to_string();
            }
            BackendEvent::WorkStarted { session_id } => {
                self.kantor_state.contract_state = "working".to_string();
            }
            BackendEvent::WorkDone { session_id, .. } => {
                self.kantor_state.contract_state = "done".to_string();
            }
            BackendEvent::ManagerMessage { content, .. }
            | BackendEvent::ManagerQuestion { content, .. } => {
                self.kantor_state.manager_messages.push(crate::state::kantor_state::ChatMessage {
                    role: "manager".to_string(),
                    content: content.clone(),
                    timestamp: chrono::Local::now().to_rfc3339(),
                });
            }
            BackendEvent::ManagerBrainstorming { content, .. } => {
                self.kantor_state.manager_messages.push(crate::state::kantor_state::ChatMessage {
                    role: "manager_brainstorm".to_string(),
                    content: content.clone(),
                    timestamp: chrono::Local::now().to_rfc3339(),
                });
            }
            BackendEvent::TaskStarted { worker_id, .. } => {
                self.active_workers = self.active_workers.saturating_add(1);
                let _ = worker_id;
            }
            BackendEvent::TaskDone { worker_id, task_id, output } => {
                self.active_workers = self.active_workers.saturating_sub(1);
                self.kantor_state
                    .worker_events
                    .push_back(crate::state::kantor_state::WorkerEvent {
                        worker_id: worker_id.clone(),
                        event_type: "task_done".to_string(),
                        content: output.clone(),
                        task_id: Some(task_id.clone()),
                        timestamp: chrono::Local::now().to_rfc3339(),
                    });
                if self.kantor_state.worker_events.len() > 500 {
                    self.kantor_state.worker_events.pop_front();
                }
            }
            BackendEvent::TaskFailed { worker_id, task_id, error } => {
                self.kantor_state
                    .worker_events
                    .push_back(crate::state::kantor_state::WorkerEvent {
                        worker_id: worker_id.clone(),
                        event_type: "task_failed".to_string(),
                        content: error.clone(),
                        task_id: Some(task_id.clone()),
                        timestamp: chrono::Local::now().to_rfc3339(),
                    });
                if self.kantor_state.worker_events.len() > 500 {
                    self.kantor_state.worker_events.pop_front();
                }
            }
            BackendEvent::LlmStreamChunk { worker_id, chunk, .. } => {
                self.kantor_state
                    .worker_events
                    .push_back(crate::state::kantor_state::WorkerEvent {
                        worker_id: worker_id.clone(),
                        event_type: "llm_chunk".to_string(),
                        content: chunk.clone(),
                        task_id: None,
                        timestamp: chrono::Local::now().to_rfc3339(),
                    });
            }
            BackendEvent::WorkerSpeakUp { worker_id, content, msg_type } => {
                self.kantor_state
                    .worker_events
                    .push_back(crate::state::kantor_state::WorkerEvent {
                        worker_id: worker_id.clone(),
                        event_type: format!("speak_up_{msg_type}"),
                        content: content.clone(),
                        task_id: None,
                        timestamp: chrono::Local::now().to_rfc3339(),
                    });
                if self.kantor_state.worker_events.len() > 500 {
                    self.kantor_state.worker_events.pop_front();
                }
            }
            BackendEvent::CostWarning { current, limit: _ } => {
                self.cost_usd = *current;
            }
            // Library events
            BackendEvent::LibraryIngestDone { entry } => {
                self.library_state.current_entry = Some(entry.clone());
                self.library_state.entry_count += 1;
            }
            BackendEvent::LibraryShelfCreated { shelf_path } => {
                self.library_state.shelf_count += 1;
            }
            BackendEvent::LibraryQueryChunk { query_id, chunk } => {
                self.library_state
                    .archivist_chunks
                    .push((query_id.clone(), chunk.clone()));
            }
            BackendEvent::LibraryQueryDone { query_id, sources } => {
                self.library_state.archivist_sources = sources.clone();
            }
            _ => {}
        }
    }
}
