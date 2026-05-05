use std::io;

use crossterm::event::{Event as CrosstermEvent, KeyEvent};
use ratatui::{
    backend::Backend,
    layout::Rect,
    Frame, Terminal,
};
use tokio::sync::mpsc;

use crate::modes::{self, Mode};
use crate::state::AppState;
use crate::transport::http::BackendClient;
use crate::transport::types::BackendEvent;
use crate::ui::theme::Theme;

/// Actions the app can perform (sent from UI to async handlers)
#[derive(Debug, Clone)]
pub enum Action {
    SendMessage { session_id: String, content: String },
    AcceptContract { session_id: String },
    ReviseContract { session_id: String, feedback: String },
    Interrupt { session_id: String, reason: String },
    LibraryQuery { query: String },
    LibraryIngest { content: String, title: String },
    NavigateShelf { path: Vec<String> },
    OpenEntry { entry_id: String },
    MarkHelpful { entry_id: String },
    MarkUnhelpful { entry_id: String },
    Quit,
}

/// Events coming into the app from various sources
#[derive(Debug)]
pub enum AppEvent {
    Crossterm(CrosstermEvent),
    Backend(BackendEvent),
}

pub struct App {
    pub state: AppState,
    pub mode: Mode,
    pub theme: Theme,
    pub should_quit: bool,
    pub event_rx: mpsc::UnboundedReceiver<AppEvent>,
    pub action_rx: mpsc::UnboundedReceiver<Action>,
    pub action_tx: mpsc::UnboundedSender<Action>,
    pub backend: BackendClient,
    pub tick_count: u64,
}

impl App {
    pub fn new(
        backend: BackendClient,
        event_rx: mpsc::UnboundedReceiver<AppEvent>,
        action_rx: mpsc::UnboundedReceiver<Action>,
    ) -> Self {
        let (action_tx, _) = mpsc::unbounded_channel();
        Self {
            state: AppState::default(),
            mode: Mode::Kantor,
            theme: Theme::office_dark(),
            should_quit: false,
            event_rx,
            action_rx,
            action_tx,
            backend,
            tick_count: 0,
        }
    }

    pub async fn run<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> anyhow::Result<()> {
        while !self.should_quit {
            // Process events
            while let Ok(event) = self.event_rx.try_recv() {
                match event {
                    AppEvent::Crossterm(ev) => {
                        self.handle_crossterm_event(ev);
                    }
                    AppEvent::Backend(ev) => {
                        self.state.handle_backend_event(ev);
                    }
                }
            }

            // Process actions
            while let Ok(action) = self.action_rx.try_recv() {
                self.handle_action(action).await;
            }

            // Render
            terminal.draw(|f| self.render(f))?;

            // Small sleep to avoid busy loop
            tokio::time::sleep(std::time::Duration::from_millis(16)).await; // ~60fps
            self.tick_count += 1;
        }

        Ok(())
    }

    fn handle_crossterm_event(&mut self, event: CrosstermEvent) {
        if let CrosstermEvent::Key(key) = event {
            self.handle_key_event(key);
        }
    }

    fn handle_key_event(&mut self, key: KeyEvent) {
        use crossterm::event::{KeyCode, KeyModifiers};

        // Global keybindings (take precedence)
        match key.code {
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.should_quit = true;
                return;
            }
            KeyCode::Char('k') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.mode = Mode::Kantor;
                return;
            }
            KeyCode::Char('b') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.mode = Mode::Library;
                return;
            }
            KeyCode::Tab => {
                self.mode = match self.mode {
                    Mode::Kantor => Mode::Library,
                    Mode::Library => Mode::Kantor,
                };
                return;
            }
            KeyCode::Char('p') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                // TODO: Command palette
                return;
            }
            KeyCode::Char('T') if key.modifiers.contains(KeyModifiers::CONTROL | KeyModifiers::SHIFT) => {
                // Toggle theme
                self.theme = match self.tick_count % 2 {
                    0 => Theme::library(),
                    _ => Theme::office_dark(),
                };
                return;
            }
            _ => {}
        }

        // Mode-specific keybindings
        match self.mode {
            Mode::Kantor => modes::kantor::handle_key(&mut self.state, key, &self.action_tx),
            Mode::Library => modes::library::handle_key(&mut self.state, key, &self.action_tx),
        }
    }

    async fn handle_action(&mut self, action: Action) {
        match action {
            Action::SendMessage { session_id, content } => {
                if let Err(e) = self.backend.send_message(&session_id, &content).await {
                    tracing::error!("Failed to send message: {e}");
                }
            }
            Action::AcceptContract { session_id } => {
                if let Err(e) = self.backend.accept_contract(&session_id).await {
                    tracing::error!("Failed to accept contract: {e}");
                }
            }
            Action::ReviseContract { session_id, feedback } => {
                if let Err(e) = self.backend.revise_contract(&session_id, &feedback).await {
                    tracing::error!("Failed to revise contract: {e}");
                }
            }
            Action::Interrupt { session_id, reason } => {
                let msg = format!("[INTERRUPT] {reason}");
                if let Err(e) = self.backend.send_message(&session_id, &msg).await {
                    tracing::error!("Failed to interrupt: {e}");
                }
            }
            Action::LibraryQuery { query } => {
                if let Err(e) = self.backend.ask_archivist(&query).await {
                    tracing::error!("Failed to query archivist: {e}");
                }
            }
            Action::LibraryIngest { content, title } => {
                if let Err(e) = self.backend.ingest_entry(&title, &content).await {
                    tracing::error!("Failed to ingest entry: {e}");
                }
            }
            Action::NavigateShelf { path } => {
                if let Ok(entries) = self.backend.get_entries(&path).await {
                    self.state.library_state.current_entries = entries;
                    self.state.library_state.shelf_breadcrumb = path;
                }
            }
            Action::OpenEntry { entry_id } => {
                if let Ok(entry) = self.backend.get_entry(&entry_id).await {
                    self.state.library_state.current_entry = Some(entry);
                }
            }
            Action::MarkHelpful { entry_id } => {
                let _ = self.backend.mark_helpful(&entry_id).await;
            }
            Action::MarkUnhelpful { entry_id } => {
                let _ = self.backend.mark_unhelpful(&entry_id).await;
            }
            Action::Quit => {
                self.should_quit = true;
            }
        }
    }

    fn render(&self, f: &mut Frame) {
        let size = f.size();
        match self.mode {
            Mode::Kantor => modes::kantor::render(f, size, &self.state, &self.theme),
            Mode::Library => modes::library::render(f, size, &self.state, &self.theme),
        }
    }
}
