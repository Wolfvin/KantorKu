use ratatui::style::Color;

/// Theme for the TUI.
/// Default theme ported from Python KANTORKU_THEMES["synthwave"].
#[derive(Debug, Clone)]
#[allow(dead_code)] // Theme fields accessed by render methods
pub struct Theme {
    pub name: &'static str,
    pub bg: Color,
    pub surface: Color,
    pub code_bg: Color,
    pub fg: Color,
    pub dim: Color,
    pub code_fg: Color,
    pub accent: Color,
    pub green: Color,
    pub yellow: Color,
    pub red: Color,
    pub cyan: Color,
    pub blue: Color,
    pub border: Color,
    pub primary: Color,
    pub secondary: Color,
    pub warning: Color,
    pub info: Color,
    pub success: Color,
    pub error: Color,
    pub muted: Color,
    pub glow: Color,
}

impl Theme {
    /// All available themes for the theme switcher
    pub fn all() -> Vec<Theme> {
        vec![
            Self::synthwave(),
            Self::office_dark(),
            Self::midnight(),
            Self::terminal_green(),
            Self::library(),
        ]
    }

    /// Get theme index by name
    pub fn index_by_name(name: &str) -> usize {
        Self::all().iter().position(|t| t.name == name).unwrap_or(0)
    }

    /// Synthwave theme — ported from Python KANTORKU_THEMES["synthwave"]
    pub fn synthwave() -> Self {
        Self {
            name: "synthwave",
            bg: Color::Rgb(13, 13, 26),
            surface: Color::Rgb(20, 20, 40),
            code_bg: Color::Rgb(33, 33, 43),
            fg: Color::Rgb(248, 248, 242),
            dim: Color::Rgb(98, 114, 164),
            code_fg: Color::Rgb(255, 121, 198),
            accent: Color::Rgb(241, 250, 140),
            green: Color::Rgb(80, 250, 123),
            yellow: Color::Rgb(255, 184, 108),
            red: Color::Rgb(255, 85, 85),
            cyan: Color::Rgb(139, 233, 253),
            blue: Color::Rgb(98, 114, 164),
            border: Color::Rgb(33, 33, 43),
            primary: Color::Rgb(255, 121, 198),
            secondary: Color::Rgb(189, 147, 249),
            warning: Color::Rgb(255, 184, 108),
            info: Color::Rgb(139, 233, 253),
            success: Color::Rgb(80, 250, 123),
            error: Color::Rgb(255, 85, 85),
            muted: Color::Rgb(98, 114, 164),
            glow: Color::Rgb(255, 121, 198),
        }
    }

    /// Office Dark — GitHub-dark inspired
    pub fn office_dark() -> Self {
        Self {
            name: "office_dark",
            bg: Color::Rgb(13, 17, 23),
            surface: Color::Rgb(22, 27, 34),
            code_bg: Color::Rgb(30, 36, 44),
            fg: Color::Rgb(201, 209, 217),
            dim: Color::Rgb(110, 118, 129),
            code_fg: Color::Rgb(255, 123, 114),
            accent: Color::Rgb(88, 166, 255),
            green: Color::Rgb(63, 185, 80),
            yellow: Color::Rgb(210, 153, 34),
            red: Color::Rgb(248, 81, 73),
            cyan: Color::Rgb(57, 197, 187),
            blue: Color::Rgb(88, 166, 255),
            border: Color::Rgb(48, 54, 61),
            primary: Color::Rgb(88, 166, 255),
            secondary: Color::Rgb(139, 148, 158),
            warning: Color::Rgb(210, 153, 34),
            info: Color::Rgb(88, 166, 255),
            success: Color::Rgb(63, 185, 80),
            error: Color::Rgb(248, 81, 73),
            muted: Color::Rgb(110, 118, 129),
            glow: Color::Rgb(88, 166, 255),
        }
    }

    /// Midnight — deeper, cooler
    pub fn midnight() -> Self {
        Self {
            name: "midnight",
            bg: Color::Rgb(0, 0, 12),
            surface: Color::Rgb(8, 8, 20),
            code_bg: Color::Rgb(16, 16, 32),
            fg: Color::Rgb(200, 210, 220),
            dim: Color::Rgb(80, 90, 110),
            code_fg: Color::Rgb(255, 123, 114),
            accent: Color::Rgb(88, 166, 255),
            green: Color::Rgb(63, 185, 80),
            yellow: Color::Rgb(210, 153, 34),
            red: Color::Rgb(248, 81, 73),
            cyan: Color::Rgb(57, 197, 187),
            blue: Color::Rgb(88, 166, 255),
            border: Color::Rgb(32, 36, 44),
            primary: Color::Rgb(88, 166, 255),
            secondary: Color::Rgb(139, 148, 158),
            warning: Color::Rgb(210, 153, 34),
            info: Color::Rgb(88, 166, 255),
            success: Color::Rgb(63, 185, 80),
            error: Color::Rgb(248, 81, 73),
            muted: Color::Rgb(80, 90, 110),
            glow: Color::Rgb(88, 166, 255),
        }
    }

    /// Terminal Green — classic hacker aesthetic
    pub fn terminal_green() -> Self {
        Self {
            name: "terminal_green",
            bg: Color::Rgb(0, 8, 0),
            surface: Color::Rgb(0, 16, 0),
            code_bg: Color::Rgb(0, 24, 0),
            fg: Color::Rgb(0, 255, 0),
            dim: Color::Rgb(0, 128, 0),
            code_fg: Color::Rgb(128, 255, 128),
            accent: Color::Rgb(0, 255, 128),
            green: Color::Rgb(0, 255, 0),
            yellow: Color::Rgb(128, 255, 0),
            red: Color::Rgb(255, 64, 64),
            cyan: Color::Rgb(0, 255, 200),
            blue: Color::Rgb(64, 128, 255),
            border: Color::Rgb(0, 64, 0),
            primary: Color::Rgb(0, 255, 128),
            secondary: Color::Rgb(64, 200, 64),
            warning: Color::Rgb(128, 255, 0),
            info: Color::Rgb(0, 200, 255),
            success: Color::Rgb(0, 255, 0),
            error: Color::Rgb(255, 64, 64),
            muted: Color::Rgb(0, 128, 0),
            glow: Color::Rgb(0, 255, 0),
        }
    }

    /// Library theme — warm amber for Library mode
    pub fn library() -> Self {
        Self {
            name: "library",
            bg: Color::Rgb(13, 13, 26),
            surface: Color::Rgb(20, 20, 40),
            code_bg: Color::Rgb(33, 33, 43),
            fg: Color::Rgb(248, 248, 242),
            dim: Color::Rgb(98, 114, 164),
            code_fg: Color::Rgb(255, 171, 76),
            accent: Color::Rgb(255, 171, 76),
            green: Color::Rgb(80, 250, 123),
            yellow: Color::Rgb(255, 184, 108),
            red: Color::Rgb(255, 85, 85),
            cyan: Color::Rgb(139, 233, 253),
            blue: Color::Rgb(98, 114, 164),
            border: Color::Rgb(56, 50, 36),
            primary: Color::Rgb(255, 171, 76),
            secondary: Color::Rgb(189, 147, 249),
            warning: Color::Rgb(255, 184, 108),
            info: Color::Rgb(139, 233, 253),
            success: Color::Rgb(80, 250, 123),
            error: Color::Rgb(255, 85, 85),
            muted: Color::Rgb(98, 114, 164),
            glow: Color::Rgb(255, 171, 76),
        }
    }
}

/// Get theme index by name (for config)
pub fn theme_index_by_name(name: &str) -> usize {
    Theme::index_by_name(name)
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: exactly 5 themes exist
    #[test]
    fn test_theme_all_count() {
        let themes = Theme::all();
        assert_eq!(themes.len(), 5, "AI Agent: exactly 5 themes must exist");
    }

    // AI Agent verifies: synthwave is index 0
    #[test]
    fn test_theme_index_by_name_synthwave() {
        assert_eq!(Theme::index_by_name("synthwave"), 0,
            "AI Agent: synthwave must be index 0");
        assert_eq!(theme_index_by_name("synthwave"), 0,
            "AI Agent: free function must return same result");
    }

    // AI Agent verifies: unknown theme name returns index 0 (default fallback)
    #[test]
    fn test_theme_index_by_name_unknown() {
        assert_eq!(Theme::index_by_name("nonexistent"), 0,
            "AI Agent invariant: unknown theme must default to index 0");
        assert_eq!(Theme::index_by_name(""), 0,
            "AI Agent: empty string must default to index 0");
    }

    // AI Agent verifies: all theme names are unique (invariant: no name collisions)
    #[test]
    fn test_theme_names_unique() {
        let themes = Theme::all();
        let names: Vec<&str> = themes.iter().map(|t| t.name).collect();
        for i in 0..names.len() {
            for j in (i+1)..names.len() {
                assert_ne!(names[i], names[j],
                    "AI Agent invariant: theme names must be unique, but found duplicate '{}'", names[i]);
            }
        }
    }

    // AI Agent verifies: synthwave theme has specific color values from Python port
    #[test]
    fn test_synthwave_theme_values() {
        let theme = Theme::synthwave();
        assert_eq!(theme.name, "synthwave");
        assert_eq!(theme.bg, Color::Rgb(13, 13, 26), "AI Agent: synthwave bg must match Python");
        assert_eq!(theme.surface, Color::Rgb(20, 20, 40), "AI Agent: synthwave surface must match");
        assert_eq!(theme.fg, Color::Rgb(248, 248, 242), "AI Agent: synthwave fg must match");
        assert_eq!(theme.accent, Color::Rgb(241, 250, 140), "AI Agent: synthwave accent must match");
        assert_eq!(theme.green, Color::Rgb(80, 250, 123), "AI Agent: synthwave green must match");
        assert_eq!(theme.red, Color::Rgb(255, 85, 85), "AI Agent: synthwave red must match");
        assert_eq!(theme.cyan, Color::Rgb(139, 233, 253), "AI Agent: synthwave cyan must match");
        assert_eq!(theme.primary, Color::Rgb(255, 121, 198), "AI Agent: synthwave primary must match");
        assert_eq!(theme.secondary, Color::Rgb(189, 147, 249), "AI Agent: synthwave secondary must match");
    }
}
