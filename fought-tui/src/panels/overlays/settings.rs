use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Tabs},
    Frame,
};

use crate::state::{AppState, SettingsTab};
use crate::ui::theme::Theme;

/// Render the Settings overlay (Ctrl+,)
pub fn render(f: &mut Frame, state: &AppState, theme: &Theme, current_theme_index: usize) {
    let area = centered_rect(70, 70, f.area());
    f.render_widget(Clear, area);

    let block = Block::default()
        .title(" ⚙ Fought Settings ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .style(Style::default().bg(theme.bg));

    let inner = block.inner(area);
    f.render_widget(block, area);

    // Tab bar
    let tabs = SettingsTab::all();
    let tab_labels: Vec<Line> = tabs.iter().enumerate().map(|(_i, tab)| {
        let style = if *tab == state.settings_tab {
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.dim)
        };
        Line::from(Span::styled(tab.label(), style))
    }).collect();

    let tab_area = Rect { height: 2, ..inner };
    let tabs_widget = Tabs::new(tab_labels)
        .select(state.settings_tab as usize);
    f.render_widget(tabs_widget, tab_area);

    let content_area = Rect {
        y: inner.y + 2,
        height: inner.height.saturating_sub(2),
        ..inner
    };

    match state.settings_tab {
        SettingsTab::Workers => render_workers_tab(f, content_area, state, theme),
        SettingsTab::Theme => render_theme_tab(f, content_area, state, theme, current_theme_index),
        SettingsTab::Keybindings => render_keybindings_tab(f, content_area, state, theme),
    }

    // Bottom hint
    let hint_area = Rect {
        y: inner.y + inner.height.saturating_sub(1),
        height: 1,
        ..inner
    };
    f.render_widget(
        Paragraph::new("Tab: Switch  ↑↓: Navigate  Enter: Select  Esc: Close")
            .style(Style::default().fg(theme.dim)),
        hint_area,
    );
}

fn render_workers_tab(f: &mut Frame, area: Rect, state: &AppState, theme: &Theme) {
    let items: Vec<ListItem> = state.kantor_state.workers_list.iter().enumerate().map(|(i, worker_id)| {
        let is_selected = i == state.settings_selection;
        let style = if is_selected {
            Style::default().fg(theme.bg).bg(theme.accent)
        } else {
            Style::default().fg(theme.fg)
        };
        let squad = if worker_id.contains("coder") { "Coding" }
                    else if worker_id.contains("verifier") { "Verification" }
                    else if worker_id.contains("scout") || worker_id.contains("narrator") { "Support" }
                    else { "Core" };
        ListItem::new(format!("  {}   [{}]", worker_id, squad)).style(style)
    }).collect();

    let list = List::new(items)
        .block(Block::default().title("Workers (13)").borders(Borders::NONE));
    f.render_widget(list, area);
}

fn render_theme_tab(f: &mut Frame, area: Rect, _state: &AppState, theme: &Theme, current_theme_index: usize) {
    let themes = Theme::all();
    let items: Vec<ListItem> = themes.iter().enumerate().map(|(i, t)| {
        let is_current = i == current_theme_index;
        let is_selected = i == _state.settings_selection;
        let marker = if is_current { " ● " } else { "   " };
        let style = if is_selected {
            Style::default().fg(theme.bg).bg(theme.accent)
        } else if is_current {
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.fg)
        };
        ListItem::new(format!("{}{}", marker, t.name)).style(style)
    }).collect();

    let list = List::new(items)
        .block(Block::default().title("Themes").borders(Borders::NONE));
    f.render_widget(list, area);
}

fn render_keybindings_tab(f: &mut Frame, area: Rect, _state: &AppState, theme: &Theme) {
    let bindings = vec![
        ("Tab", "Switch mode (Kantor ↔ Library)"),
        ("Ctrl+K", "Switch to Kantor"),
        ("Ctrl+B", "Switch to Library"),
        ("Ctrl+P", "Command palette"),
        ("Ctrl+,", "Settings"),
        ("Ctrl+C", "Quit"),
        ("Ctrl+Shift+T", "Cycle theme"),
        ("Ctrl+A", "Accept contract"),
        ("Ctrl+R", "Revise contract"),
        ("Ctrl+I", "Disrupt/Interrupt"),
        ("Ctrl+M", "Multi-line input"),
        ("Ctrl+F", "Focus mode / Search"),
        ("Ctrl+L", "Clear chat"),
        ("Alt+1-4", "Switch Workers tab"),
        ("g / G", "Go to top/bottom (Library)"),
        ("/", "Search (Library)"),
        ("h / u", "Mark helpful/unhelpful (Library)"),
        ("i / a / b", "Ingest / Ask / Browse (Library)"),
    ];

    let items: Vec<ListItem> = bindings.iter().map(|(key, desc)| {
        Line::from(vec![
            Span::styled(format!("  {:<20}", key), Style::default().fg(theme.accent)),
            Span::styled(*desc, Style::default().fg(theme.fg)),
        ])
    }).map(ListItem::new).collect();

    let list = List::new(items)
        .block(Block::default().title("Keyboard Shortcuts").borders(Borders::NONE));
    f.render_widget(list, area);
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_width = r.width * percent_x / 100;
    let popup_height = r.height * percent_y / 100;
    Rect {
        x: r.x + (r.width.saturating_sub(popup_width)) / 2,
        y: r.y + (r.height.saturating_sub(popup_height)) / 2,
        width: popup_width.min(80),
        height: popup_height.min(40),
    }
}
