use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    Frame,
};
use tokio::sync::mpsc;

use crate::app::Action;
use crate::panels::library;
use crate::state::library_state::{ContentMode, IngestField, IngestStep};
use crate::state::AppState;
use crate::ui::components::render_status_bar;
use crate::ui::theme::Theme;

/// Handle key events in Library mode
pub fn handle_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    if state.settings_open || state.command_palette_open {
        return;
    }

    match state.library_state.content_mode {
        ContentMode::Browse => handle_browse_key(state, key, action_tx),
        ContentMode::Ask => handle_ask_key(state, key, action_tx),
        ContentMode::Ingest => handle_ingest_key(state, key, action_tx),
    }
}

fn handle_browse_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    // If search mode is active, handle search input
    if state.library_state.search_mode {
        handle_search_key(state, key, action_tx);
        return;
    }

    match key.code {
        KeyCode::Up
            if state.library_state.shelf_selection > 0 => {
                state.library_state.shelf_selection -= 1;
            }
        KeyCode::Down => {
            let max = state.library_state.visible_items.len().saturating_sub(1);
            if state.library_state.shelf_selection < max {
                state.library_state.shelf_selection += 1;
            }
        }
        KeyCode::Enter | KeyCode::Right => {
            let idx = state.library_state.shelf_selection;
            let items = state.library_state.visible_items.clone();
            if let Some(item) = items.get(idx).cloned() {
                match item {
                    crate::state::library_state::ShelfItem::Shelf { full_path, .. } => {
                        let path_key = full_path.join("/");
                        if state.library_state.shelf_expanded.contains(&path_key) {
                            state.library_state.shelf_expanded.remove(&path_key);
                        } else {
                            state.library_state.shelf_expanded.insert(path_key);
                        }
                        // Also request entries from backend
                        let _ = action_tx.send(Action::NavigateShelf { path: full_path });
                        // Rebuild visible items
                        rebuild_visible_items(&mut state.library_state);
                    }
                    crate::state::library_state::ShelfItem::Entry { entry, .. } => {
                        let _ = action_tx.send(Action::OpenEntry { entry_id: entry.id });
                    }
                }
            }
        }
        KeyCode::Left | KeyCode::Backspace
            if state.library_state.shelf_breadcrumb.len() > 1 => {
                state.library_state.shelf_breadcrumb.pop();
                rebuild_visible_items(&mut state.library_state);
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
        KeyCode::Char('i') => {
            state.library_state.content_mode = ContentMode::Ingest;
            state.library_state.ingest_field_active = IngestField::Title;
        }
        KeyCode::Char('a') => {
            state.library_state.content_mode = ContentMode::Ask;
        }
        KeyCode::Char('h') => {
            if let Some(entry) = &state.library_state.current_entry {
                let _ = action_tx.send(Action::MarkHelpful { entry_id: entry.id.clone() });
            }
        }
        KeyCode::Char('u') => {
            if let Some(entry) = &state.library_state.current_entry {
                let _ = action_tx.send(Action::MarkUnhelpful { entry_id: entry.id.clone() });
            }
        }
        KeyCode::Esc => {
            // Nothing to cancel in normal browse mode
        }
        _ => {}
    }
}

/// Handle search mode input — activated by pressing `/` in browse mode
fn handle_search_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    match key.code {
        KeyCode::Enter => {
            let query = state.library_state.search_query.clone();
            if !query.is_empty() {
                let _ = action_tx.send(Action::LibrarySearch { query });
            }
        }
        KeyCode::Esc => {
            state.library_state.search_mode = false;
            state.library_state.search_query.clear();
        }
        KeyCode::Backspace => {
            state.library_state.search_query.pop();
            // If query is empty, exit search mode
            if state.library_state.search_query.is_empty() {
                state.library_state.search_mode = false;
            }
        }
        KeyCode::Char(c) => {
            state.library_state.search_query.push(c);
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
                    timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                });
                state.library_state.ask_input.clear();
            }
        }
        KeyCode::Backspace => {
            state.library_state.ask_input.pop();
        }
        KeyCode::Esc => {
            if state.library_state.ask_input.is_empty() {
                state.library_state.content_mode = ContentMode::Browse;
            } else {
                state.library_state.ask_input.clear();
            }
        }
        KeyCode::Char(c) => {
            state.library_state.ask_input.push(c);
        }
        _ => {}
    }
}

fn handle_ingest_key(state: &mut AppState, key: KeyEvent, action_tx: &mpsc::UnboundedSender<Action>) {
    match state.library_state.ingest_step {
        IngestStep::Input => {
            match key.code {
                KeyCode::Tab => {
                    // Toggle between title and content input fields
                    state.library_state.ingest_field_active = match state.library_state.ingest_field_active {
                        IngestField::Title => IngestField::Content,
                        IngestField::Content => IngestField::Title,
                    };
                }
                KeyCode::Enter => {
                    // In content field, Enter submits. In title field, Tab moves to content.
                    match state.library_state.ingest_field_active {
                        IngestField::Title => {
                            // Move to content field
                            state.library_state.ingest_field_active = IngestField::Content;
                        }
                        IngestField::Content => {
                            if !state.library_state.ingest_title.is_empty() && !state.library_state.ingest_content.is_empty() {
                                state.library_state.ingest_step = IngestStep::Confirm;
                            }
                        }
                    }
                }
                KeyCode::Backspace => {
                    match state.library_state.ingest_field_active {
                        IngestField::Title => { state.library_state.ingest_title.pop(); }
                        IngestField::Content => { state.library_state.ingest_content.pop(); }
                    }
                }
                KeyCode::Esc => {
                    state.library_state.content_mode = ContentMode::Browse;
                    state.library_state.ingest_title.clear();
                    state.library_state.ingest_content.clear();
                    state.library_state.ingest_field_active = IngestField::Title;
                }
                KeyCode::Char(c) => {
                    match state.library_state.ingest_field_active {
                        IngestField::Title => { state.library_state.ingest_title.push(c); }
                        IngestField::Content => { state.library_state.ingest_content.push(c); }
                    }
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
                    state.library_state.ingest_step = IngestStep::Analyzing;
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
                    state.library_state.ingest_field_active = IngestField::Title;
                    state.library_state.content_mode = ContentMode::Browse;
                }
                _ => {}
            }
        }
        IngestStep::Analyzing => {
            // Wait for backend event — but Esc cancels
            if key.code == KeyCode::Esc {
                state.library_state.ingest_step = IngestStep::Input;
            }
        }
    }
}

/// Rebuild the visible_items list from shelves and expanded state
fn rebuild_visible_items(state: &mut crate::state::library_state::LibraryState) {
    state.visible_items = build_visible_items_from_shelves(&state.shelves, &state.shelf_expanded, 0);
}

fn build_visible_items_from_shelves(
    shelves: &[crate::state::library_state::Shelf],
    expanded: &std::collections::HashSet<String>,
    depth: usize,
) -> Vec<crate::state::library_state::ShelfItem> {
    let mut items = Vec::new();
    for shelf in shelves {
        let path_key = shelf.path.join("/");
        let is_expanded = expanded.contains(&path_key);
        items.push(crate::state::library_state::ShelfItem::Shelf {
            depth,
            name: shelf.name.clone(),
            full_path: shelf.path.clone(),
            entry_count: shelf.entry_count as usize,
            is_expanded,
        });
        if is_expanded {
            let children = build_visible_items_from_shelves(&shelf.children, expanded, depth + 1);
            items.extend(children);
        }
    }
    items
}

/// Render Library mode layout
pub fn render(f: &mut Frame, size: Rect, state: &AppState, theme: &Theme, tick: u64) {
    // Use the provided theme instead of hardcoded Theme::library()
    let lib_theme = theme;

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1),   // Status bar
            Constraint::Min(0),      // Main area
            Constraint::Length(3),   // Bottom bar
        ])
        .split(size);

    // Status bar
    let search_indicator = if state.library_state.search_mode {
        format!(" SEARCH: {} |", state.library_state.search_query)
    } else {
        String::new()
    };
    let session_info = format!(
        " {}{} shelves | {} entries | mode: {}",
        search_indicator,
        state.library_state.shelf_count,
        state.library_state.entry_count,
        state.library_state.content_mode.label(),
    );
    render_status_bar(
        f,
        chunks[0],
        "LIBRARY",
        lib_theme.accent,
        &format!(" Fought [LIBRARY]  {session_info}"),
        " Tab: Next  /: Search  i: Ingest  a: Ask ",
        lib_theme,
    );

    // Main area: 2 columns
    let main_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(30),   // Shelf panel
            Constraint::Percentage(70),   // Content panel
        ])
        .split(chunks[1]);

    library::shelf::render(f, main_chunks[0], &state.library_state, lib_theme, tick);

    match state.library_state.content_mode {
        ContentMode::Browse => library::reader::render(f, main_chunks[1], &state.library_state, lib_theme, tick),
        ContentMode::Ask => library::ask::render(f, main_chunks[1], &state.library_state, lib_theme, tick),
        ContentMode::Ingest => library::ingest::render(f, main_chunks[1], &state.library_state, lib_theme, tick),
    }

    // Bottom bar — different content per mode
    match state.library_state.content_mode {
        ContentMode::Browse => {
            if state.library_state.search_mode {
                crate::ui::components::render_input_bar(f, chunks[2], &state.library_state.search_query, "Enter: Search  Esc: Cancel", lib_theme);
            } else {
                let hint = "a: Ask  i: Ingest  /: Search  g/G: Top/Bottom";
                crate::ui::components::render_input_bar(f, chunks[2], "", hint, lib_theme);
            }
        }
        ContentMode::Ask => {
            crate::ui::components::render_input_bar(f, chunks[2], &state.library_state.ask_input, "Enter: Send  Esc: Back", lib_theme);
        }
        ContentMode::Ingest => {
            let field_hint = match state.library_state.ingest_field_active {
                IngestField::Title => "Tab: Switch to Content",
                IngestField::Content => "Tab: Switch to Title  Enter: Submit",
            };
            crate::ui::components::render_input_bar(f, chunks[2], &state.library_state.ingest_content, field_hint, lib_theme);
        }
    }
}
