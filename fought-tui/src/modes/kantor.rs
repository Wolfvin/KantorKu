use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    Frame,
};
use tokio::sync::mpsc;

use crate::app::Action;
use crate::panels::kantor;
use crate::state::AppState;
use crate::state::kantor_state::WorkersTab;
use crate::ui::components::{connection_icon, contract_state_color, render_progress, render_status_bar};
use crate::ui::theme::Theme;

/// Handle key events in Kantor mode
pub fn handle_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    // If settings or command palette are open, don't process kantor keys
    if state.settings_open || state.command_palette_open {
        return;
    }

    match key.code {
        // Enter — send message
        KeyCode::Enter => {
            if state.kantor_state.multiline_mode {
                // In multiline mode, Enter adds newline (Shift+Enter to send)
                // For simplicity, Ctrl+Enter sends in multiline mode
                return;
            }
            let input = state.kantor_state.input_text.clone();
            if input.is_empty() {
                return;
            }

            // Check for slash commands
            if input.starts_with('/') {
                handle_slash_command(&input, state, action_tx);
                state.kantor_state.input_text.clear();
                return;
            }

            // NL action parsing when contract is presented
            if state.kantor_state.contract_state == "contract_presented" {
                if let Some(action) = crate::ui::keybindings::parse_nl_action(&input) {
                    let session_id = state.session_id.clone().unwrap_or_default();
                    match action {
                        "accept" => { let _ = action_tx.send(Action::AcceptContract { session_id }); }
                        "revise" => { let _ = action_tx.send(Action::ReviseContract { session_id, feedback: input.clone() }); }
                        "interrupt" => { let _ = action_tx.send(Action::Interrupt { session_id, reason: input.clone() }); }
                        _ => {}
                    }
                    state.kantor_state.input_text.clear();
                    state.kantor_state.push_manager_message("user", &input);
                    return;
                }
            }

            // Normal message send
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::SendMessage {
                    session_id: session_id.clone(),
                    content: input.clone(),
                });
            }
            state.kantor_state.input_history.push(input.clone());
            state.kantor_state.input_history_pos = state.kantor_state.input_history.len();
            state.kantor_state.push_manager_message("user", &input);
            state.kantor_state.input_text.clear();
        }
        // Ctrl+M — toggle multiline
        KeyCode::Char('m') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.kantor_state.multiline_mode = !state.kantor_state.multiline_mode;
        }
        // Ctrl+L — clear chat
        KeyCode::Char('l') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.kantor_state.manager_messages.clear();
        }
        // Ctrl+A — accept contract
        KeyCode::Char('a') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::AcceptContract { session_id: session_id.clone() });
            }
        }
        // Ctrl+R — revise contract
        KeyCode::Char('r') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::ReviseContract {
                    session_id: session_id.clone(),
                    feedback: String::new(),
                });
            }
        }
        // Ctrl+I — disrupt
        KeyCode::Char('i') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::Interrupt {
                    session_id: session_id.clone(),
                    reason: "User disrupt".to_string(),
                });
            }
        }
        // Ctrl+F — focus mode
        KeyCode::Char('f') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.kantor_state.focus_mode = !state.kantor_state.focus_mode;
        }
        // Ctrl+Tab — switch middle panel tab
        KeyCode::BackTab => {
            state.kantor_state.active_tab = match state.kantor_state.active_tab {
                WorkersTab::Workers => WorkersTab::Events,
                WorkersTab::Briefing => WorkersTab::Workers,
                WorkersTab::Dag => WorkersTab::Briefing,
                WorkersTab::Events => WorkersTab::Dag,
            };
        }
        KeyCode::Char('\t') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.kantor_state.active_tab = match state.kantor_state.active_tab {
                WorkersTab::Workers => WorkersTab::Briefing,
                WorkersTab::Briefing => WorkersTab::Dag,
                WorkersTab::Dag => WorkersTab::Events,
                WorkersTab::Events => WorkersTab::Workers,
            };
        }
        // Number keys 1-4 for tab switching
        KeyCode::Char('1') if key.modifiers.contains(KeyModifiers::ALT) => { state.kantor_state.active_tab = WorkersTab::Workers; }
        KeyCode::Char('2') if key.modifiers.contains(KeyModifiers::ALT) => { state.kantor_state.active_tab = WorkersTab::Briefing; }
        KeyCode::Char('3') if key.modifiers.contains(KeyModifiers::ALT) => { state.kantor_state.active_tab = WorkersTab::Dag; }
        KeyCode::Char('4') if key.modifiers.contains(KeyModifiers::ALT) => { state.kantor_state.active_tab = WorkersTab::Events; }
        // Escape — cancel
        KeyCode::Esc => {
            state.kantor_state.input_text.clear();
        }
        // Backspace
        KeyCode::Backspace => {
            state.kantor_state.input_text.pop();
        }
        // History
        KeyCode::Up if state.kantor_state.input_text.is_empty() => {
            if state.kantor_state.input_history_pos > 0 {
                state.kantor_state.input_history_pos -= 1;
                if let Some(prev) = state.kantor_state.input_history.get(state.kantor_state.input_history_pos) {
                    state.kantor_state.input_text = prev.clone();
                }
            }
        }
        KeyCode::Down if state.kantor_state.input_text.is_empty() => {
            if state.kantor_state.input_history_pos < state.kantor_state.input_history.len() {
                state.kantor_state.input_history_pos += 1;
                if state.kantor_state.input_history_pos < state.kantor_state.input_history.len() {
                    if let Some(next) = state.kantor_state.input_history.get(state.kantor_state.input_history_pos) {
                        state.kantor_state.input_text = next.clone();
                    }
                } else {
                    state.kantor_state.input_text.clear();
                }
            }
        }
        // Character input
        KeyCode::Char(c) => {
            state.kantor_state.input_text.push(c);
        }
        _ => {}
    }
}

/// Handle slash commands in kantor mode
fn handle_slash_command(input: &str, state: &mut AppState, action_tx: &mpsc::UnboundedSender<Action>) {
    let parts: Vec<&str> = input[1..].splitn(2, ' ').collect();
    let cmd = parts[0];
    let _args = parts.get(1).unwrap_or(&"");

    match cmd {
        "accept" => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::AcceptContract { session_id: session_id.clone() });
            }
        }
        "revise" => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::ReviseContract {
                    session_id: session_id.clone(),
                    feedback: _args.to_string(),
                });
            }
        }
        "disrupt" | "interrupt" => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::Interrupt {
                    session_id: session_id.clone(),
                    reason: _args.to_string(),
                });
            }
        }
        "clear" => {
            state.kantor_state.manager_messages.clear();
        }
        "focus" => {
            state.kantor_state.focus_mode = !state.kantor_state.focus_mode;
        }
        "settings" => {
            state.settings_open = true;
        }
        "theme" => {
            let _ = action_tx.send(Action::CycleTheme);
        }
        "help" => {
            state.kantor_state.push_manager_message("system", "Commands: /accept, /revise, /disrupt, /clear, /focus, /settings, /theme, /help");
        }
        _ => {
            state.kantor_state.push_manager_message("system", &format!("Unknown command: /{cmd}"));
        }
    }
}

/// Render Kantor mode layout
pub fn render(f: &mut Frame, size: Rect, state: &AppState, theme: &Theme, tick: u64) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1),    // Status bar
            Constraint::Min(0),       // Main area
            Constraint::Length(3),    // Input bar
        ])
        .split(size);

    // Status bar
    let (conn_icon, _conn_color, conn_label) = connection_icon(&state.connection_state);
    let session_info = format!(
        " {} {} | {} | {} workers | ${:.3}",
        conn_icon,
        conn_label,
        state.session_id.as_deref().unwrap_or("no session"),
        state.active_workers,
        state.cost_usd,
    );
    render_status_bar(
        f,
        chunks[0],
        "KANTOR",
        theme.accent,
        &format!(" ⚡ Fought [KANTOR]  {session_info}"),
        " Tab: Library  Ctrl+P: Commands ",
        theme,
    );

    // Main area layout depends on focus mode
    let main_chunks = if state.kantor_state.focus_mode {
        // Focus mode: just manager chat (full width)
        Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(100)])
            .split(chunks[1])
    } else {
        // Normal: 3 columns
        Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(25),   // Contract
                Constraint::Percentage(45),   // Workers Live
                Constraint::Percentage(30),   // Manager Chat
            ])
            .split(chunks[1])
    };

    if state.kantor_state.focus_mode {
        kantor::manager_chat::render(f, main_chunks[0], &state.kantor_state, theme);
    } else {
        kantor::contract::render(f, main_chunks[0], &state.kantor_state, theme);
        kantor::workers_live::render(f, main_chunks[1], &state.kantor_state, theme, tick);
        kantor::manager_chat::render(f, main_chunks[2], &state.kantor_state, theme);
    }

    // Input bar
    let multiline_hint = if state.kantor_state.multiline_mode { "Ctrl+M: Single-line" } else { "Ctrl+M: Multi-line" };
    let contract_hint = if state.kantor_state.contract_state == "contract_presented" {
        "Ctrl+A: Accept  Ctrl+R: Revise"
    } else {
        multiline_hint
    };
    crate::ui::components::render_input_bar(
        f,
        chunks[2],
        &state.kantor_state.input_text,
        contract_hint,
        theme,
    );
}
