use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::library_state::{entry_type_icon, entry_type_label, LibraryState};
use crate::ui::theme::Theme;

/// Render the Shelf Panel (left column in Library mode) — the "never-ending rak"
pub fn render(f: &mut Frame, area: Rect, state: &LibraryState, theme: &Theme, tick: u64) {
    let block = Block::default()
        .title(" RAK BUKU ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Breadcrumb header
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
        f.render_widget(
            Paragraph::new(breadcrumb).style(Style::default().fg(theme.dim)),
            bc_area,
        );
    }

    // Build visible items from shelves + entries
    let visible_items = build_visible_items(state);
    let visible_count = list_area.height as usize;

    let items: Vec<ListItem> = visible_items
        .iter()
        .skip(state.shelf_scroll)
        .take(visible_count)
        .map(|(global_idx, item)| {
            let is_selected = *global_idx == state.shelf_selection;
            render_shelf_item(item, is_selected, theme, tick)
        })
        .collect();

    f.render_widget(List::new(items), list_area);
}

fn build_visible_items(state: &LibraryState) -> Vec<(usize, crate::state::library_state::ShelfItem)> {
    let mut result = Vec::new();
    let items = build_shelf_items_recursive(&state.shelves, &state.shelf_expanded, 0);
    for (i, item) in items.into_iter().enumerate() {
        result.push((i, item));
    }
    // Add current entries after shelf items
    for entry in &state.current_entries {
        let idx = result.len();
        result.push((idx, crate::state::library_state::ShelfItem::Entry {
            depth: state.shelf_breadcrumb.len(),
            entry: entry.clone(),
        }));
    }
    result
}

fn build_shelf_items_recursive(
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
            let children = build_shelf_items_recursive(&shelf.children, expanded, depth + 1);
            items.extend(children);
        }
    }
    items
}

fn render_shelf_item(item: &crate::state::library_state::ShelfItem, is_selected: bool, theme: &Theme, _tick: u64) -> ListItem<'static> {
    let indent = "  ";

    let (text, base_style) = match item {
        crate::state::library_state::ShelfItem::Shelf { depth, name, entry_count, is_expanded, .. } => {
            let prefix = indent.repeat(*depth);
            let arrow = if *is_expanded { "▼" } else { "▶" };
            let label = entry_type_label("knowledge"); // fallback for folders
            let text = format!("{}{} {} {}  [{}]", prefix, arrow, label, name, entry_count);
            let style = if is_selected {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.fg)
            };
            (text, style)
        }
        crate::state::library_state::ShelfItem::Entry { depth, entry, .. } => {
            let prefix = indent.repeat(*depth);
            let icon = entry_type_icon(&entry.entry_type);
            let verified = if entry.verified { "✓" } else { "○" };
            let quality = format!("{:.0}%", entry.quality_score * 100.0);
            let text = format!(
                "{}{} {} {} {} | {}x",
                prefix, icon, entry.title, verified, quality, entry.usage_count
            );
            let style = if is_selected {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            } else {
                match entry.entry_type.as_str() {
                    "knowledge" => Style::default().fg(theme.fg),
                    "solution" => Style::default().fg(theme.yellow),
                    "qa_pair" => Style::default().fg(theme.cyan),
                    "procedure" => Style::default().fg(theme.green),
                    _ => Style::default().fg(theme.dim),
                }
            };
            (text, style)
        }
    };

    ListItem::new(text).style(base_style)
}
