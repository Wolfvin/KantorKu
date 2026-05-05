use ratatui::{
    layout::Rect,
    style::Style,
    text::{Line, Span},
    widgets::{List, ListItem, Paragraph},
    Frame,
};

use crate::state::kantor_state::KantorState;
use crate::ui::components::task_state_icon;
use crate::ui::theme::Theme;

/// Render the DAG panel — ASCII tree with proper ratatui styling
pub fn render(f: &mut Frame, area: Rect, state: &KantorState, theme: &Theme) {
    if state.dag_nodes.is_empty() {
        let placeholder = Paragraph::new(
            "No task DAG yet.\n\nThe dependency graph builds as tasks are assigned\nto workers during execution."
        )
        .style(Style::default().fg(theme.dim));
        f.render_widget(placeholder, area);
        return;
    }

    let lines = render_dag_tree(&state.dag_nodes, 0, theme);
    let items: Vec<ListItem> = lines.into_iter().map(ListItem::new).collect();
    f.render_widget(List::new(items), area);
}

fn render_dag_tree(nodes: &[crate::state::kantor_state::DagNode], depth: usize, theme: &Theme) -> Vec<Line<'static>> {
    let mut lines = Vec::new();

    for (i, node) in nodes.iter().enumerate() {
        let is_last = i == nodes.len() - 1;

        let prefix = if depth == 0 {
            String::new()
        } else {
            let indent = "│   ".repeat(depth.saturating_sub(1));
            let connector = if is_last { "└── " } else { "├── " };
            format!("{indent}{connector}")
        };

        let (status_icon, icon_color) = match node.status.as_str() {
            "done" | "completed" => (task_state_icon("done"), theme.green),
            "working" | "in_progress" => (task_state_icon("in_progress"), theme.yellow),
            "failed" | "error" => (task_state_icon("failed"), theme.red),
            "pending" => (task_state_icon("pending"), theme.dim),
            _ => ("·", theme.dim),
        };

        let title = format!("{} ({})", node.title, node.worker_id);

        lines.push(Line::from(vec![
            Span::styled(prefix, Style::default().fg(theme.dim)),
            Span::styled(status_icon.to_string(), Style::default().fg(icon_color)),
            Span::styled(format!(" {title}"), Style::default().fg(theme.fg)),
        ]));

        if !node.children.is_empty() {
            let child_lines = render_dag_tree(&node.children, depth + 1, theme);
            lines.extend(child_lines);
        }
    }

    lines
}
