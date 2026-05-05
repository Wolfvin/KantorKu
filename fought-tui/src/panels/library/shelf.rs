use std::collections::HashSet;

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::library_state::{LibraryEntryBrief, LibraryState, ShelfItem};
use crate::ui::theme::Theme;

/// Render the Shelf Panel (left column in Library mode)
/// The "never-ending rak" — tree view of all shelves and entries
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme) {
    let block = Block::default()
        .title("RAK BUKU")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Breadcrumb header if navigated
    let (breadcrumb_area, list_area) = if !state.shelf_breadcrumb.is_empty() {
        let v = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(1), Constraint::Min(0)])
            .split(inner);
        (Some(v[0]), v[1])
    } else {
        (None, inner)
    };

    if let Some(bc_area) = breadcrumb_area {
        let breadcrumb = format!("← {}", state.shelf_breadcrumb.join(" → "));
        let bc_widget = Paragraph::new(breadcrumb)
            .style(Style::default().fg(theme.dim));
        f.render_widget(bc_widget, bc_area);
    }

    // Build visible items from shelves and entries
    let visible_items = build_visible_items(state);
    let visible_count = list_area.height as usize;

    let items: Vec<ListItem> = visible_items
        .iter()
        .enumerate()
        .skip(state.shelf_scroll)
        .take(visible_count)
        .map(|(idx, item)| {
            let is_selected = idx == state.shelf_selection;
            render_shelf_item(item, is_selected, theme)
        })
        .collect();

    let list = List::new(items);
    f.render_widget(list, list_area);
}

fn build_visible_items(state: &LibraryState) -> Vec<ShelfItem> {
    let mut items = Vec::new();

    // Add shelves as items
    for shelf in &state.shelves {
        let path_key = shelf.path.join("/");
        let is_expanded = state.shelf_expanded.contains(&path_key);
        let is_selected = false; // Selection tracked by index

        items.push(ShelfItem::Shelf {
            depth: 0,
            name: shelf.name.clone(),
            full_path: shelf.path.clone(),
            entry_count: shelf.entry_count as usize,
            is_expanded,
            is_selected,
        });

        // If expanded, add children
        if is_expanded {
            build_shelf_items_recursive(&shelf.children, 1, &state.shelf_expanded, &mut items);
        }
    }

    // Add current entries
    for entry in &state.current_entries {
        items.push(ShelfItem::Entry {
            depth: state.shelf_breadcrumb.len(),
            entry: entry.clone(),
            is_selected: false,
        });
    }

    items
}

fn build_shelf_items_recursive(
    shelves: &[crate::state::library_state::Shelf],
    depth: usize,
    expanded: &HashSet<String>,
    items: &mut Vec<ShelfItem>,
) {
    for shelf in shelves {
        let path_key = shelf.path.join("/");
        let is_expanded = expanded.contains(&path_key);

        items.push(ShelfItem::Shelf {
            depth,
            name: shelf.name.clone(),
            full_path: shelf.path.clone(),
            entry_count: shelf.entry_count as usize,
            is_expanded,
            is_selected: false,
        });

        if is_expanded {
            build_shelf_items_recursive(&shelf.children, depth + 1, expanded, items);
        }
    }
}

fn render_shelf_item(item: &ShelfItem, is_selected: bool, theme: &Theme) -> ListItem<'static> {
    let indent = "  ";

    match item {
        ShelfItem::Shelf { depth, name, entry_count, is_expanded, .. } => {
            let prefix = indent.repeat(*depth);
            let arrow = if *is_expanded { "▼" } else { "▶" };
            let folder_icon = if *is_expanded { "📂" } else { "📁" };
            let text = format!("{}{} {} {}  [{}]", prefix, arrow, folder_icon, name, entry_count);
            let style = if is_selected {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.fg)
            };
            ListItem::new(text).style(style)
        }
        ShelfItem::Entry { depth, entry, .. } => {
            let prefix = indent.repeat(*depth);
            let icon = crate::state::library_state::entry_type_icon(&entry.entry_type);
            let verified = if entry.verified { "✓" } else { "○" };
            let quality = format!("{:.2}", entry.quality_score);
            let text = format!(
                "{}{} {}  {} {} | {}x",
                prefix, icon, entry.title, verified, quality, entry.usage_count
            );
            let style = if is_selected {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            } else {
                entry_type_style(&entry.entry_type, theme)
            };
            ListItem::new(text).style(style)
        }
    }
}

fn entry_type_style(entry_type: &str, theme: &Theme) -> Style {
    match entry_type {
        "knowledge" => Style::default().fg(theme.fg),
        "solution" => Style::default().fg(theme.yellow),
        "qa_pair" => Style::default().fg(theme.cyan),
        "procedure" => Style::default().fg(theme.green),
        _ => Style::default().fg(theme.dim),
    }
}
