pub mod app_state;
pub mod config;
pub mod contract_state;
pub mod kantor_state;
pub mod library_state;
pub mod worker_state;

pub use app_state::AppState;

/// Settings tabs
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SettingsTab {
    Workers,
    Theme,
    Keybindings,
}

impl SettingsTab {
    pub fn next(self) -> Self {
        match self {
            SettingsTab::Workers => SettingsTab::Theme,
            SettingsTab::Theme => SettingsTab::Keybindings,
            SettingsTab::Keybindings => SettingsTab::Workers,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            SettingsTab::Workers => "Workers",
            SettingsTab::Theme => "Theme",
            SettingsTab::Keybindings => "Keybindings",
        }
    }

    pub fn all() -> &'static [SettingsTab] {
        &[SettingsTab::Workers, SettingsTab::Theme, SettingsTab::Keybindings]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: SettingsTab::next cycles Workers→Theme→Keybindings→Workers
    #[test]
    fn test_settings_tab_next() {
        assert_eq!(SettingsTab::Workers.next(), SettingsTab::Theme,
            "AI Agent: Workers→Theme");
        assert_eq!(SettingsTab::Theme.next(), SettingsTab::Keybindings,
            "AI Agent: Theme→Keybindings");
        assert_eq!(SettingsTab::Keybindings.next(), SettingsTab::Workers,
            "AI Agent invariant: Keybindings wraps back to Workers");

        // AI Agent: full cycle returns to start
        let start = SettingsTab::Workers;
        let after_cycle = start.next().next().next();
        assert_eq!(after_cycle, start,
            "AI Agent invariant: 3 next() calls must cycle back to start");
    }

    // AI Agent verifies: all labels are correct
    #[test]
    fn test_settings_tab_label() {
        assert_eq!(SettingsTab::Workers.label(), "Workers");
        assert_eq!(SettingsTab::Theme.label(), "Theme");
        assert_eq!(SettingsTab::Keybindings.label(), "Keybindings");
    }

    // AI Agent verifies: all() returns exactly 3 tabs
    #[test]
    fn test_settings_tab_all() {
        let all = SettingsTab::all();
        assert_eq!(all.len(), 3, "AI Agent: exactly 3 settings tabs must exist");
        assert_eq!(all[0], SettingsTab::Workers);
        assert_eq!(all[1], SettingsTab::Theme);
        assert_eq!(all[2], SettingsTab::Keybindings);
    }
}
