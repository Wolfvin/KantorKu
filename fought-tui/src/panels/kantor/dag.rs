use ratatui::{
    layout::Rect,
    style::{Modifier, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::theme::Theme;

/// Render the DAG panel (tab in Workers Live middle panel)
/// Shows task dependency graph as ASCII tree — the proper implementation Python TUI lacked
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    let block = Block::default()
        .title("DAG — Task Dependencies")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));

    let inner = block.inner(area);
    f.render_widget(block, area);

    if state.dag_nodes.is_empty() {
        let placeholder = Paragraph::new("No task DAG yet.\nDAG builds as tasks are assigned.")
            .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, inner);
        return;
    }

    let lines = render_dag_tree(&state.dag_nodes, 0, true);
    let items: Vec<ListItem> = lines.into_iter().map(ListItem::new).collect();
    let list = List::new(items);
    f.render_widget(list, inner);
}

fn render_dag_tree(nodes: &[crate::state::kantor_state::DagNode], depth: usize, _is_last: bool) -> Vec<Line<'static>> {
    let mut lines = Vec::new();

    for (i, node) in nodes.iter().enumerate() {
        let is_last_node = i == nodes.len() - 1;

        let prefix = if depth == 0 {
            String::new()
        } else {
            let connector = if is_last_node { "└── " } else { "├── " };
            let indent = if depth > 1 { "│   ".repeat(depth - 1) } else { String::new() };
            format!("{indent}{connector}")
        };

        let (status_icon, status_style) = match node.status.as_str() {
            "done" | "completed" => ("✓", Style::default().fg(Theme::office_dark().green)),
            "working" | "in_progress" => ("●", Style::default().fg(Theme::office_dark().yellow)),
            "failed" | "error" => ("✗", Style::default().fg(Theme::office_dark().red)),
            "pending" => ("○", Style::default().fg(Theme::office_dark().dim)),
            _ => ("·", Style::default().fg(Theme::office_dark().dim)),
        };

        let line = Line::from(format!("{}{} {} ({})", prefix, status_icon, node.title, node.worker_id));
        lines.push(line);

        if !node.children.is_empty() {
            let child_lines = render_dag_tree(&node.children, depth + 1, is_last_node);
            lines.extend(child_lines);
        }
    }

    lines
}
