use crossterm::event::{Event as CrosstermEvent, KeyEvent};
use ratatui::{backend::Backend, Frame, Terminal};
use tokio::sync::mpsc;

use crate::modes::Mode;
use crate::state::AppState;
use crate::state::config::AppConfig;
use crate::transport::http::BackendClient;
use crate::transport::types::BackendEvent;
use crate::ui::theme::Theme;

/// Actions dispatched from UI to async handlers.
#[derive(Debug, Clone)]
pub enum Action {
    // Kantor actions
    SendMessage { session_id: String, content: String },
    AcceptContract { session_id: String },
    ReviseContract { session_id: String, feedback: String },
    Interrupt { session_id: String, reason: String },
    // Library actions
    LibraryQuery { query: String },
    LibraryIngest { content: String, title: String },
    NavigateShelf { path: Vec<String> },
    OpenEntry { entry_id: String },
    MarkHelpful { entry_id: String },
    MarkUnhelpful { entry_id: String },
    // App actions
    CycleTheme,
    SaveConfig,
    Quit,
}

/// Events coming into the app from various sources.
#[derive(Debug)]
pub enum AppEvent {
    Crossterm(CrosstermEvent),
    Backend(BackendEvent),
}

pub struct App {
    pub state: AppState,
    pub mode: Mode,
    pub theme: Theme,
    pub theme_index: usize,
    pub should_quit: bool,
    pub event_rx: mpsc::UnboundedReceiver<AppEvent>,
    pub action_rx: mpsc::UnboundedReceiver<Action>,
    pub action_tx: mpsc::UnboundedSender<Action>,
    pub backend: BackendClient,
    pub tick: u64,
    pub config: AppConfig,
}

impl App {
    pub fn new(
        config: AppConfig,
        backend: BackendClient,
        event_rx: mpsc::UnboundedReceiver<AppEvent>,
        action_rx: mpsc::UnboundedReceiver<Action>,
        action_tx: mpsc::UnboundedSender<Action>,
    ) -> Self {
        let theme_index = config.ui.default_theme_index();
        let theme = Theme::all()[theme_index].clone();
        Self {
            state: AppState::default(),
            mode: Mode::Kantor,
            theme,
            theme_index,
            should_quit: false,
            event_rx,
            action_rx,
            action_tx,
            backend,
            tick: 0,
            config,
        }
    }

    pub fn run<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> anyhow::Result<()> {
        while !self.should_quit {
            // Drain events
            while let Ok(event) = self.event_rx.try_recv() {
                match event {
                    AppEvent::Crossterm(ev) => self.handle_crossterm_event(ev),
                    AppEvent::Backend(ev) => self.state.handle_backend_event(ev),
                }
            }

            // Drain actions
            while let Ok(action) = self.action_rx.try_recv() {
                // Actions are fire-and-forget; we spawn them to not block the render loop
                let backend = self.backend.clone();
                let atx = self.action_tx.clone();
                tokio::spawn(async move {
                    Self::execute_action(action, &backend, &atx).await;
                });
            }

            // Render
            terminal.draw(|f| self.render(f))?;

            // ~60 fps target
            std::thread::sleep(std::time::Duration::from_millis(16));
            self.tick = self.tick.wrapping_add(1);
        }

        Ok(())
    }

    fn handle_crossterm_event(&mut self, event: CrosstermEvent) {
        match event {
            CrosstermEvent::Key(key) => self.handle_key_event(key),
            CrosstermEvent::Mouse(mouse) => self.handle_mouse_event(mouse),
            CrosstermEvent::Resize(_, _) => {} // Handled by terminal.draw
            _ => {}
        }
    }

    fn handle_key_event(&mut self, key: KeyEvent) {
        use crossterm::event::{KeyCode, KeyModifiers};

        // Global keybindings — always take precedence
        match key.code {
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.should_quit = true;
                return;
            }
            KeyCode::Char('k') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.mode = Mode::Kantor;
                self.state.kantor_state.input_focused = true;
                self.state.library_state.input_focused = false;
                return;
            }
            KeyCode::Char('b') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.mode = Mode::Library;
                self.state.kantor_state.input_focused = false;
                self.state.library_state.input_focused = true;
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
                self.state.command_palette_open = !self.state.command_palette_open;
                return;
            }
            KeyCode::Char('T') if key.modifiers.contains(KeyModifiers::CONTROL | KeyModifiers::SHIFT) => {
                let _ = self.action_tx.send(Action::CycleTheme);
                return;
            }
            KeyCode::Char(',') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.state.settings_open = !self.state.settings_open;
                return;
            }
            KeyCode::Esc => {
                if self.state.command_palette_open {
                    self.state.command_palette_open = false;
                    return;
                }
                if self.state.settings_open {
                    self.state.settings_open = false;
                    return;
                }
                // Otherwise delegate to mode
            }
            _ => {}
        }

        // Modal overlays take precedence over mode handlers
        if self.state.command_palette_open {
            self.handle_command_palette_key(key);
            return;
        }
        if self.state.settings_open {
            self.handle_settings_key(key);
            return;
        }

        // Mode-specific keybindings
        match self.mode {
            Mode::Kantor => crate::modes::kantor::handle_key(&mut self.state, key, &self.action_tx),
            Mode::Library => crate::modes::library::handle_key(&mut self.state, key, &self.action_tx),
        }
    }

    fn handle_mouse_event(&mut self, mouse: crossterm::event::MouseEvent) {
        use crossterm::event::MouseEventKind;
        match mouse.kind {
            MouseEventKind::ScrollUp => {
                match self.mode {
                    Mode::Kantor => self.state.kantor_state.scroll_up(),
                    Mode::Library => self.state.library_state.scroll_up(),
                }
            }
            MouseEventKind::ScrollDown => {
                match self.mode {
                    Mode::Kantor => self.state.kantor_state.scroll_down(),
                    Mode::Library => self.state.library_state.scroll_down(),
                }
            }
            _ => {}
        }
    }

    fn handle_command_palette_key(&mut self, key: KeyEvent) {
        use crossterm::event::KeyCode;
        match key.code {
            KeyCode::Up => {
                if self.state.command_palette_selection > 0 {
                    self.state.command_palette_selection -= 1;
                }
            }
            KeyCode::Down => {
                let max = self.state.filtered_commands().len().saturating_sub(1);
                if self.state.command_palette_selection < max {
                    self.state.command_palette_selection += 1;
                }
            }
            KeyCode::Enter => {
                let commands = self.state.filtered_commands();
                if let Some(cmd) = commands.get(self.state.command_palette_selection) {
                    self.execute_command(cmd.action.clone());
                }
                self.state.command_palette_open = false;
                self.state.command_palette_query.clear();
                self.state.command_palette_selection = 0;
            }
            KeyCode::Esc => {
                self.state.command_palette_open = false;
                self.state.command_palette_query.clear();
                self.state.command_palette_selection = 0;
            }
            KeyCode::Backspace => {
                self.state.command_palette_query.pop();
                self.state.command_palette_selection = 0;
            }
            KeyCode::Char(c) => {
                self.state.command_palette_query.push(c);
                self.state.command_palette_selection = 0;
            }
            _ => {}
        }
    }

    fn handle_settings_key(&mut self, key: KeyEvent) {
        use crossterm::event::KeyCode;
        match key.code {
            KeyCode::Esc => {
                self.state.settings_open = false;
            }
            KeyCode::Tab => {
                self.state.settings_tab = self.state.settings_tab.next();
            }
            KeyCode::Up => {
                if self.state.settings_selection > 0 {
                    self.state.settings_selection -= 1;
                }
            }
            KeyCode::Down => {
                let max = match self.state.settings_tab {
                    crate::state::SettingsTab::Workers => self.state.kantor_state.workers_list.len().saturating_sub(1),
                    crate::state::SettingsTab::Theme => Theme::all().len().saturating_sub(1),
                    crate::state::SettingsTab::Keybindings => 0,
                };
                if self.state.settings_selection < max {
                    self.state.settings_selection += 1;
                }
            }
            KeyCode::Enter => {
                if let crate::state::SettingsTab::Theme = self.state.settings_tab {
                    let themes = Theme::all();
                    if self.state.settings_selection < themes.len() {
                        self.theme = themes[self.state.settings_selection].clone();
                        self.theme_index = self.state.settings_selection;
                    }
                }
            }
            _ => {}
        }
    }

    fn execute_command(&mut self, action: String) {
        match action.as_str() {
            "switch_kantor" => self.mode = Mode::Kantor,
            "switch_library" => self.mode = Mode::Library,
            "toggle_theme" => {
                let _ = self.action_tx.send(Action::CycleTheme);
            }
            "open_settings" => self.state.settings_open = true,
            "clear_chat" => self.state.kantor_state.manager_messages.clear(),
            "focus_mode" => self.state.kantor_state.focus_mode = !self.state.kantor_state.focus_mode,
            "ingest" => self.state.library_state.content_mode = crate::state::library_state::ContentMode::Ingest,
            "ask" => self.state.library_state.content_mode = crate::state::library_state::ContentMode::Ask,
            "browse" => self.state.library_state.content_mode = crate::state::library_state::ContentMode::Browse,
            "quit" => self.should_quit = true,
            _ => tracing::warn!("Unknown command: {action}"),
        }
    }

    async fn execute_action(action: Action, backend: &BackendClient, _atx: &mpsc::UnboundedSender<Action>) {
        match action {
            Action::SendMessage { session_id, content } => {
                if let Err(e) = backend.send_message(&session_id, &content).await {
                    tracing::error!("Failed to send message: {e}");
                }
            }
            Action::AcceptContract { session_id } => {
                if let Err(e) = backend.accept_contract(&session_id).await {
                    tracing::error!("Failed to accept contract: {e}");
                }
            }
            Action::ReviseContract { session_id, feedback } => {
                if let Err(e) = backend.revise_contract(&session_id, &feedback).await {
                    tracing::error!("Failed to revise contract: {e}");
                }
            }
            Action::Interrupt { session_id, reason } => {
                let msg = format!("[INTERRUPT] {reason}");
                if let Err(e) = backend.send_message(&session_id, &msg).await {
                    tracing::error!("Failed to interrupt: {e}");
                }
            }
            Action::LibraryQuery { query } => {
                if let Err(e) = backend.ask_archivist(&query).await {
                    tracing::error!("Failed to query archivist: {e}");
                }
            }
            Action::LibraryIngest { title, content } => {
                if let Err(e) = backend.ingest_entry(&title, &content).await {
                    tracing::error!("Failed to ingest entry: {e}");
                }
            }
            Action::NavigateShelf { path } => {
                if let Ok(entries) = backend.get_entries(&path).await {
                    tracing::info!("Loaded {} entries for shelf", entries.len());
                    let _ = entries; // State updates via BackendEvent
                }
            }
            Action::OpenEntry { entry_id } => {
                if let Ok(entry) = backend.get_entry(&entry_id).await {
                    tracing::info!("Loaded entry: {}", entry.title);
                    let _ = entry; // State updates via BackendEvent
                }
            }
            Action::MarkHelpful { entry_id } => {
                let _ = backend.mark_helpful(&entry_id).await;
            }
            Action::MarkUnhelpful { entry_id } => {
                let _ = backend.mark_unhelpful(&entry_id).await;
            }
            Action::CycleTheme => {
                // Handled synchronously in the main loop
            }
            Action::SaveConfig => {
                // Config is saved on quit
            }
            Action::Quit => {}
        }
    }

    fn render(&self, f: &mut Frame) {
        let area = f.area();
        match self.mode {
            Mode::Kantor => crate::modes::kantor::render(f, area, &self.state, &self.theme, self.tick),
            Mode::Library => crate::modes::library::render(f, area, &self.state, &self.theme, self.tick),
        }

        // Overlay: Command palette
        if self.state.command_palette_open {
            crate::panels::overlays::command_palette::render(f, &self.state, &self.theme);
        }

        // Overlay: Settings
        if self.state.settings_open {
            crate::panels::overlays::settings::render(f, &self.state, &self.theme, self.theme_index);
        }
    }
}
