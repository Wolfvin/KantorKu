use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use tokio::sync::mpsc;

use crate::app::Action;
use crate::panels::kantor;
use crate::state::AppState;
use crate::ui::theme::Theme;

/// Handle key events in Kantor mode
pub fn handle_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    use crossterm::event::KeyCode;

    match key.code {
        // Enter — send message
        KeyCode::Enter => {
            let input = state.kantor_state.input_text.clone();
            if !input.is_empty() {
                // Check for NL action parsing when contract is presented
                if state.kantor_state.contract_state == "contract_presented" {
                    if let Some(action) = crate::ui::keybindings::parse_nl_action(&input) {
                        let session_id = state.session_id.clone().unwrap_or_default();
                        match action {
                            "accept" => {
                                let _ = action_tx.send(Action::AcceptContract { session_id });
                            }
                            "revise" => {
                                let _ = action_tx.send(Action::ReviseContract {
                                    session_id,
                                    feedback: input,
                                });
                            }
                            "interrupt" => {
                                let _ = action_tx.send(Action::Interrupt {
                                    session_id,
                                    reason: input,
                                });
                            }
                            _ => {}
                        }
                        state.kantor_state.input_text.clear();
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
                state.kantor_state.input_text.clear();

                // Add to local chat display
                state.kantor_state.manager_messages.push(crate::state::kantor_state::ChatMessage {
                    role: "user".to_string(),
                    content: input,
                    timestamp: chrono::Local::now().to_rfc3339(),
                });
            }
        }
        // Ctrl+M — toggle multiline mode
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
                let _ = action_tx.send(Action::AcceptContract {
                    session_id: session_id.clone(),
                });
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
        // Ctrl+I — disrupt/interrupt
        KeyCode::Char('i') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            if let Some(session_id) = &state.session_id {
                let _ = action_tx.send(Action::Interrupt {
                    session_id: session_id.clone(),
                    reason: "User disrupt".to_string(),
                });
            }
        }
        // Ctrl+F — toggle focus mode
        KeyCode::Char('f') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.kantor_state.focus_mode = !state.kantor_state.focus_mode;
        }
        // Escape — cancel
        KeyCode::Esc => {
            state.kantor_state.input_text.clear();
        }
        // Backspace — delete character
        KeyCode::Backspace => {
            state.kantor_state.input_text.pop();
        }
        // Up — history up
        KeyCode::Up => {
            if state.kantor_state.input_history_pos > 0 {
                state.kantor_state.input_history_pos -= 1;
                if let Some(prev) = state.kantor_state.input_history.get(state.kantor_state.input_history_pos) {
                    state.kantor_state.input_text = prev.clone();
                }
            }
        }
        // Down — history down
        KeyCode::Down => {
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
        // Ctrl+Tab — switch middle panel tab
        KeyCode::Tab if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.kantor_state.active_tab = match state.kantor_state.active_tab {
                crate::state::kantor_state::WorkersTab::Workers => crate::state::kantor_state::WorkersTab::Briefing,
                crate::state::kantor_state::WorkersTab::Briefing => crate::state::kantor_state::WorkersTab::Dag,
                crate::state::kantor_state::WorkersTab::Dag => crate::state::kantor_state::WorkersTab::Events,
                crate::state::kantor_state::WorkersTab::Events => crate::state::kantor_state::WorkersTab::Workers,
            };
        }
        // Character input
        KeyCode::Char(c) => {
            state.kantor_state.input_text.push(c);
        }
        _ => {}
    }
}

/// Render Kantor mode layout
pub fn render(f: &mut Frame, size: Rect, state: &AppState, theme: &Theme) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1),    // Status bar
            Constraint::Min(0),       // Main area
            Constraint::Length(3),    // Input bar
        ])
        .split(size);

    // Status bar
    let session_info = format!(
        "{} | {} workers | ${:.3}",
        state.session_id.as_deref().unwrap_or("no session"),
        state.active_workers,
        state.cost_usd
    );
    let right = " Tab: Library  Ctrl+P: Commands ";
    crate::ui::components::render_status_bar(
        f,
        chunks[0],
        "KANTOR",
        theme.accent,
        &session_info,
        right,
        theme,
    );

    // Main area: 3 columns
    let main_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(25),   // Left: Contract
            Constraint::Percentage(45),   // Middle: Workers Live (tabbed)
            Constraint::Percentage(30),   // Right: Manager Chat
        ])
        .split(chunks[1]);

    kantor::contract::render(f, main_chunks[0], &state.kantor_state, theme);
    kantor::workers_live::render(f, main_chunks[1], &state.kantor_state, theme);
    kantor::manager_chat::render(f, main_chunks[2], &state.kantor_state, theme);

    // Input bar
    let multiline_hint = if state.kantor_state.multiline_mode { "Ctrl+M: Single-line" } else { "Ctrl+M: Multi-line" };
    crate::ui::components::render_input_bar(
        f,
        chunks[2],
        &state.kantor_state.input_text,
        state.kantor_state.input_text.len(),
        multiline_hint,
        theme,
    );
}
