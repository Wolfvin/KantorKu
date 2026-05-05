use ratatui::style::Color;

/// Theme colors for the TUI.
/// Default theme is ported from Python KANTORKU_THEMES["synthwave"].
#[derive(Debug, Clone)]
pub struct Theme {
    // Background
    pub bg: Color,
    pub surface: Color,
    pub code_bg: Color,

    // Foreground
    pub fg: Color,
    pub dim: Color,
    pub code_fg: Color,

    // Semantic colors
    pub accent: Color,
    pub green: Color,
    pub yellow: Color,
    pub red: Color,
    pub cyan: Color,
    pub blue: Color,
    pub border: Color,

    // Extended from synthwave theme
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
    /// Office Dark theme — ported from Python KANTORKU_THEMES["synthwave"]
    /// Uses RGB values matching the Python theme exactly.
    pub fn office_dark() -> Self {
        Self {
            // Core background
            bg: Color::Rgb(13, 13, 26),      // #0d0d1a
            surface: Color::Rgb(20, 20, 40),  // #141428
            code_bg: Color::Rgb(33, 33, 43),  // #21212b

            // Core foreground
            fg: Color::Rgb(248, 248, 242),    // #f8f8f2
            dim: Color::Rgb(98, 114, 164),    // #6272a4
            code_fg: Color::Rgb(255, 121, 198), // #ff79c6

            // Semantic
            accent: Color::Rgb(241, 250, 140),  // #f1fa8c
            green: Color::Rgb(80, 250, 123),    // #50fa7b
            yellow: Color::Rgb(255, 184, 108),  // #ffb86c
            red: Color::Rgb(255, 85, 85),       // #ff5555
            cyan: Color::Rgb(139, 233, 253),    // #8be9fd
            blue: Color::Rgb(98, 114, 164),     // #6272a4
            border: Color::Rgb(33, 33, 43),     // #21212b

            // Extended from synthwave
            primary: Color::Rgb(255, 121, 198),  // #ff79c6
            secondary: Color::Rgb(189, 147, 249), // #bd93f9
            warning: Color::Rgb(255, 184, 108),   // #ffb86c
            info: Color::Rgb(139, 233, 253),      // #8be9fd
            success: Color::Rgb(80, 250, 123),    // #50fa7b
            error: Color::Rgb(255, 85, 85),       // #ff5555
            muted: Color::Rgb(98, 114, 164),      // #6272a4
            glow: Color::Rgb(255, 121, 198),      // #ff79c6
        }
    }

    /// Library theme — warm amber accent for the Library mode
    pub fn library() -> Self {
        let mut t = Self::office_dark();
        t.accent = Color::Rgb(255, 171, 76);    // Amber for library
        t.border = Color::Rgb(56, 50, 36);      // Warm border
        t.primary = Color::Rgb(255, 171, 76);    // Amber primary
        t.glow = Color::Rgb(255, 171, 76);       // Amber glow
        t
    }

    /// Midnight theme — darker, cooler tones
    pub fn midnight() -> Self {
        Self {
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
            border: Color::Rgb(48, 54, 61),
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

    /// Get the theme for the current mode
    pub fn for_mode(&self, is_library: bool) -> Self {
        if is_library {
            Self::library()
        } else {
            self.clone()
        }
    }
}

/// Named themes for the theme switcher (Ctrl+Shift+T)
pub const THEME_NAMES: &[&str] = &[
    "office_dark",
    "library",
    "midnight",
];

/// Get a theme by name
pub fn theme_by_name(name: &str) -> Theme {
    match name {
        "office_dark" => Theme::office_dark(),
        "library" => Theme::library(),
        "midnight" => Theme::midnight(),
        _ => Theme::office_dark(),
    }
}
