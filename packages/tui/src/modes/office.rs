use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    Frame,
};
use tokio::sync::mpsc;

use crate::app::Action;
use crate::panels::office;
use crate::state::AppState;
use crate::state::office_state::{ContractState, WorkersTab};
use crate::ui::components::{connection_icon, render_status_bar};
use crate::ui::theme::Theme;

/// Handle key events in Office mode
pub fn handle_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    // If settings or command palette are open, don't process office keys
    if state.settings_open || state.command_palette_open {
        return;
    }

    match key.code {
        // Enter — send message
        KeyCode::Enter => {
            if state.office_state.multiline_mode {
                // In multiline mode, Ctrl+Enter sends (handled below), plain Enter adds newline
                state.office_state.input_text.push('\n');
                return;
            }
            let input = state.office_state.input_text.clone();
            if input.is_empty() {
                return;
            }

            // Check for slash commands
            if input.starts_with('/') {
                handle_slash_command(&input, state, action_tx);
                state.office_state.input_text.clear();
                return;
            }

            // NL action parsing when contract is presented
            if state.office_state.contract_state == ContractState::ContractPresented {
                if let Some(action) = crate::ui::keybindings::parse_nl_action(&input) {
                    let session_id = state.session_id.clone().unwrap_or_default();
                    match action {
                        "accept" => { let _ = action_tx.send(Action::AcceptContract { session_id }); }
                        "revise" => { let _ = action_tx.send(Action::ReviseContract { session_id, feedback: input.clone() }); }
                        "interrupt" => { let _ = action_tx.send(Action::Interrupt { session_id, reason: input.clone() }); }
                        _ => {}
                    }
                    state.office_state.push_manager_message("user", &input);
                    state.office_state.input_text.clear();
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
            state.office_state.input_history.push(input.clone());
            state.office_state.input_history_pos = state.office_state.input_history.len();
            state.office_state.push_manager_message("user", &input);
            state.office_state.input_text.clear();
        }
        // Ctrl+M — toggle multiline
        KeyCode::Char('m') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.office_state.multiline_mode = !state.office_state.multiline_mode;
        }
        // Ctrl+L — clear chat
        KeyCode::Char('l') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.office_state.manager_messages.clear();
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
            state.office_state.focus_mode = !state.office_state.focus_mode;
        }
        // Ctrl+Tab — switch middle panel tab (reverse)
        KeyCode::BackTab => {
            state.office_state.active_tab = match state.office_state.active_tab {
                WorkersTab::Workers => WorkersTab::Events,
                WorkersTab::Briefing => WorkersTab::Workers,
                WorkersTab::Dag => WorkersTab::Briefing,
                WorkersTab::Events => WorkersTab::Dag,
            };
        }
        KeyCode::Char('\t') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.office_state.active_tab = match state.office_state.active_tab {
                WorkersTab::Workers => WorkersTab::Briefing,
                WorkersTab::Briefing => WorkersTab::Dag,
                WorkersTab::Dag => WorkersTab::Events,
                WorkersTab::Events => WorkersTab::Workers,
            };
        }
        // Number keys 1-4 for tab switching
        KeyCode::Char('1') if key.modifiers.contains(KeyModifiers::ALT) => { state.office_state.active_tab = WorkersTab::Workers; }
        KeyCode::Char('2') if key.modifiers.contains(KeyModifiers::ALT) => { state.office_state.active_tab = WorkersTab::Briefing; }
        KeyCode::Char('3') if key.modifiers.contains(KeyModifiers::ALT) => { state.office_state.active_tab = WorkersTab::Dag; }
        KeyCode::Char('4') if key.modifiers.contains(KeyModifiers::ALT) => { state.office_state.active_tab = WorkersTab::Events; }
        // Escape — cancel
        KeyCode::Esc => {
            state.office_state.input_text.clear();
        }
        // Backspace
        KeyCode::Backspace => {
            state.office_state.input_text.pop();
        }
        // History — allow navigation even when input is not empty
        KeyCode::Up if state.office_state.input_text.is_empty()
            && state.office_state.input_history_pos > 0 => {
                state.office_state.input_history_pos -= 1;
                if let Some(prev) = state.office_state.input_history.get(state.office_state.input_history_pos) {
                    state.office_state.input_text = prev.clone();
                }
            }
        KeyCode::Down if state.office_state.input_text.is_empty()
            && state.office_state.input_history_pos < state.office_state.input_history.len() => {
                state.office_state.input_history_pos += 1;
                if state.office_state.input_history_pos < state.office_state.input_history.len() {
                    if let Some(next) = state.office_state.input_history.get(state.office_state.input_history_pos) {
                        state.office_state.input_text = next.clone();
                    }
                } else {
                    state.office_state.input_text.clear();
                }
            }
        // Character input
        KeyCode::Char(c) => {
            state.office_state.input_text.push(c);
        }
        _ => {}
    }
}

/// Handle slash commands in office mode
fn handle_slash_command(input: &str, state: &mut AppState, action_tx: &mpsc::UnboundedSender<Action>) {
    let parts: Vec<&str> = input[1..].splitn(2, ' ').collect();
    let cmd = parts[0];
    let args = parts.get(1).copied().unwrap_or("");

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
                    feedback: args.to_string(),
                });
            }
        }
        "disrupt" | "interrupt" => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::Interrupt {
                    session_id: session_id.clone(),
                    reason: args.to_string(),
                });
            }
        }
        "clear" => {
            state.office_state.manager_messages.clear();
        }
        "focus" => {
            state.office_state.focus_mode = !state.office_state.focus_mode;
        }
        "settings" => {
            state.settings_open = true;
        }
        "theme" => {
            let _ = action_tx.send(Action::CycleTheme);
        }
        "save" => {
            let _ = action_tx.send(Action::SaveConfig);
        }
        "help" => {
            state.office_state.push_manager_message("system", "Commands: /accept, /revise, /disrupt, /clear, /focus, /settings, /theme, /save, /help");
        }
        _ => {
            // Check if this is a destructive command requiring confirmation
            if crate::ui::keybindings::DESTRUCTIVE_COMMANDS.contains(&cmd) {
                state.office_state.push_manager_message("system", &format!("⚠ Destructive command /{cmd} requires confirmation. Type /{cmd} confirm to proceed."));
            } else {
                state.office_state.push_manager_message("system", &format!("Unknown command: /{cmd}"));
            }
        }
    }
}

/// Render Office mode layout
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
        "OFFICE",
        theme.accent,
        &format!(" Fought [OFFICE]  {session_info}"),
        " Tab: Next  Ctrl+1-5: Modes  Ctrl+P: Commands ",
        theme,
    );

    // Main area layout depends on focus mode
    let main_chunks = if state.office_state.focus_mode {
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

    if state.office_state.focus_mode {
        office::manager_chat::render(f, main_chunks[0], &state.office_state, theme);
    } else {
        office::contract::render(f, main_chunks[0], &state.office_state, theme);
        office::workers_live::render(f, main_chunks[1], &state.office_state, theme, tick);
        office::manager_chat::render(f, main_chunks[2], &state.office_state, theme);
    }

    // Input bar
    let multiline_hint = if state.office_state.multiline_mode { "Ctrl+M: Single-line" } else { "Ctrl+M: Multi-line" };
    let contract_hint = if state.office_state.contract_state == ContractState::ContractPresented {
        "Ctrl+A: Accept  Ctrl+R: Revise"
    } else {
        multiline_hint
    };
    crate::ui::components::render_input_bar(
        f,
        chunks[2],
        &state.office_state.input_text,
        contract_hint,
        theme,
    );
}
