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
