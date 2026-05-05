pub mod app_state;
pub mod config;
pub mod kantor_state;
pub mod library_state;

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
