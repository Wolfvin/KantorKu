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
use crate::panels::library;
use crate::state::library_state::ContentMode;
use crate::state::AppState;
use crate::ui::theme::Theme;

/// Handle key events in Library mode
pub fn handle_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    // Route to content-mode-specific handler first
    match state.library_state.content_mode {
        ContentMode::Browse => handle_browse_key(state, key, action_tx),
        ContentMode::Ask => handle_ask_key(state, key, action_tx),
        ContentMode::Ingest => handle_ingest_key(state, key, action_tx),
    }
}

fn handle_browse_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    match key.code {
        // Navigation
        KeyCode::Up => {
            if state.library_state.shelf_selection > 0 {
                state.library_state.shelf_selection -= 1;
            }
        }
        KeyCode::Down => {
            let max = state.library_state.visible_items.len().saturating_sub(1);
            if state.library_state.shelf_selection < max {
                state.library_state.shelf_selection += 1;
            }
        }
        KeyCode::Enter | KeyCode::Right => {
            // Toggle expand shelf or open entry
            let idx = state.library_state.shelf_selection;
            if let Some(item) = state.library_state.visible_items.get(idx).cloned() {
                match item {
                    crate::state::library_state::ShelfItem::Shelf { full_path, .. } => {
                        let path_key = full_path.join("/");
                        if state.library_state.shelf_expanded.contains(&path_key) {
                            state.library_state.shelf_expanded.remove(&path_key);
                        } else {
                            state.library_state.shelf_expanded.insert(path_key);
                        }
                    }
                    crate::state::library_state::ShelfItem::Entry { entry, .. } => {
                        let _ = action_tx.send(Action::OpenEntry { entry_id: entry.id });
                    }
                }
            }
        }
        KeyCode::Left | KeyCode::Backspace => {
            // Navigate up one level
            if state.library_state.shelf_breadcrumb.len() > 1 {
                state.library_state.shelf_breadcrumb.pop();
            }
        }
        KeyCode::Char('/') => {
            state.library_state.search_mode = true;
            state.library_state.search_query.clear();
        }
        KeyCode::Char('g') => {
            state.library_state.shelf_selection = 0;
            state.library_state.shelf_scroll = 0;
        }
        KeyCode::Char('G') => {
            let max = state.library_state.visible_items.len().saturating_sub(1);
            state.library_state.shelf_selection = max;
        }
        // Mode switches
        KeyCode::Char('i') => {
            state.library_state.content_mode = ContentMode::Ingest;
        }
        KeyCode::Char('a') => {
            state.library_state.content_mode = ContentMode::Ask;
        }
        KeyCode::Char('h') => {
            // Mark helpful
            if let Some(entry) = &state.library_state.current_entry {
                let _ = action_tx.send(Action::MarkHelpful { entry_id: entry.id.clone() });
            }
        }
        KeyCode::Char('u') => {
            // Mark unhelpful
            if let Some(entry) = &state.library_state.current_entry {
                let _ = action_tx.send(Action::MarkUnhelpful { entry_id: entry.id.clone() });
            }
        }
        _ => {}
    }
}

fn handle_ask_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    match key.code {
        KeyCode::Enter => {
            let query = state.library_state.ask_input.clone();
            if !query.is_empty() {
                let _ = action_tx.send(Action::LibraryQuery { query: query.clone() });
                state.library_state.ask_history.push(crate::state::library_state::AskMessage {
                    role: "user".to_string(),
                    content: query,
                    sources: vec![],
                    timestamp: chrono::Local::now().to_rfc3339(),
                });
                state.library_state.ask_input.clear();
            }
        }
        KeyCode::Backspace => {
            state.library_state.ask_input.pop();
        }
        KeyCode::Char('b') => {
            state.library_state.content_mode = ContentMode::Browse;
        }
        KeyCode::Char(c) => {
            state.library_state.ask_input.push(c);
        }
        KeyCode::Esc => {
            state.library_state.content_mode = ContentMode::Browse;
        }
        _ => {}
    }
}

fn handle_ingest_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    use crate::state::library_state::IngestStep;

    match state.library_state.ingest_step {
        IngestStep::Input => {
            match key.code {
                KeyCode::Enter => {
                    // Move to confirm step
                    if !state.library_state.ingest_title.is_empty() && !state.library_state.ingest_content.is_empty() {
                        state.library_state.ingest_step = IngestStep::Confirm;
                    }
                }
                KeyCode::Backspace => {
                    state.library_state.ingest_content.pop();
                }
                KeyCode::Char('b') => {
                    state.library_state.content_mode = ContentMode::Browse;
                }
                KeyCode::Char(c) => {
                    state.library_state.ingest_content.push(c);
                }
                KeyCode::Esc => {
                    state.library_state.content_mode = ContentMode::Browse;
                }
                _ => {}
            }
        }
        IngestStep::Confirm => {
            match key.code {
                KeyCode::Char('y') | KeyCode::Enter => {
                    let title = state.library_state.ingest_title.clone();
                    let content = state.library_state.ingest_content.clone();
                    let _ = action_tx.send(Action::LibraryIngest { title, content });
                    state.library_state.ingest_step = IngestStep::Done;
                }
                KeyCode::Char('n') | KeyCode::Esc => {
                    state.library_state.ingest_step = IngestStep::Input;
                }
                _ => {}
            }
        }
        IngestStep::Done => {
            match key.code {
                KeyCode::Enter | KeyCode::Esc => {
                    state.library_state.ingest_step = IngestStep::Input;
                    state.library_state.ingest_title.clear();
                    state.library_state.ingest_content.clear();
                    state.library_state.content_mode = ContentMode::Browse;
                }
                _ => {}
            }
        }
        IngestStep::Analyzing => {
            // Wait for backend event, ignore input
        }
    }
}

/// Render Library mode layout
pub fn render(f: &mut Frame, size: Rect, state: &AppState, theme: &Theme) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1),   // Status bar
            Constraint::Min(0),      // Main area
            Constraint::Length(3),   // Ask bar
        ])
        .split(size);

    // Status bar
    let lib_theme = Theme::library();
    let session_info = format!(
        "{} shelves | {} entries",
        state.library_state.shelf_count,
        state.library_state.entry_count,
    );
    let right = " Tab: Kantor  Ctrl+F: Search ";
    crate::ui::components::render_status_bar(
        f,
        chunks[0],
        "LIBRARY",
        lib_theme.accent,
        &session_info,
        right,
        &lib_theme,
    );

    // Main area: 2 columns
    let main_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(30),   // Shelf panel
            Constraint::Percentage(70),   // Content panel
        ])
        .split(chunks[1]);

    library::shelf::render(f, main_chunks[0], &state.library_state, &lib_theme);

    match state.library_state.content_mode {
        ContentMode::Browse => library::reader::render(f, main_chunks[1], &state.library_state, &lib_theme),
        ContentMode::Ask => library::ask::render(f, main_chunks[1], &state.library_state, &lib_theme),
        ContentMode::Ingest => library::ingest::render(f, main_chunks[1], &state.library_state, &lib_theme),
    }

    // Ask bar at bottom
    let ask_hint = match state.library_state.content_mode {
        ContentMode::Browse => "a: Ask  i: Ingest  /: Search",
        ContentMode::Ask => "Enter: Send  Esc: Back",
        ContentMode::Ingest => "Enter: Submit  Esc: Back",
    };
    let ask_input = match state.library_state.content_mode {
        ContentMode::Ask => &state.library_state.ask_input,
        ContentMode::Ingest => &state.library_state.ingest_content,
        _ => &state.library_state.ask_input,
    };
    crate::ui::components::render_input_bar(
        f,
        chunks[2],
        ask_input,
        ask_input.len(),
        ask_hint,
        &lib_theme,
    );
}
