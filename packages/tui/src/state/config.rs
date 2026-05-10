use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

/// Application configuration loaded from `~/.config/fought/config.toml`
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub backend: BackendConfig,
    pub ui: UiConfig,
    pub library: LibraryConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendConfig {
    /// WebSocket URL for event stream
    pub ws_url: String,
    /// HTTP base URL for REST API
    pub http_url: String,
    /// Reconnect backoff initial delay in ms
    pub reconnect_backoff_ms: u64,
    /// Maximum reconnect backoff in ms
    pub reconnect_backoff_max_ms: u64,
    /// HTTP request timeout in seconds
    pub http_timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UiConfig {
    /// Default theme name
    pub default_theme: String,
    /// Mouse support
    pub mouse_enabled: bool,
    /// Render FPS target
    pub fps: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LibraryConfig {
    /// Default domain for new entries
    pub default_domain: String,
    /// Default language for new entries
    pub default_lang: String,
    /// Minimum quality score to show in shelf
    pub min_quality_display: f32,
    /// Maximum shelf depth
    pub max_shelf_depth: usize,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            backend: BackendConfig {
                ws_url: "ws://localhost:8765/ws/office".to_string(),
                http_url: "http://localhost:8765".to_string(),
                reconnect_backoff_ms: 500,
                reconnect_backoff_max_ms: 30_000,
                http_timeout_secs: 30,
            },
            ui: UiConfig {
                default_theme: "synthwave".to_string(),
                mouse_enabled: true,
                fps: 60,
            },
            library: LibraryConfig {
                default_domain: "web_text".to_string(),
                default_lang: "id".to_string(),
                min_quality_display: 0.0,
                max_shelf_depth: 4,
            },
        }
    }
}

impl UiConfig {
    pub fn default_theme_index(&self) -> usize {
        crate::ui::theme::theme_index_by_name(&self.default_theme)
    }
}

impl AppConfig {
    /// Returns the config file path: `~/.config/fought/config.toml`
    pub fn config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("fought")
            .join("config.toml")
    }

    /// Load config from disk, falling back to defaults
    pub fn load_or_default() -> Self {
        let path = Self::config_path();
        if path.exists() {
            match fs::read_to_string(&path) {
                Ok(content) => match toml::from_str(&content) {
                    Ok(config) => {
                        tracing::info!("Loaded config from {}", path.display());
                        return config;
                    }
                    Err(e) => {
                        tracing::warn!("Failed to parse config at {}: {e}", path.display());
                    }
                },
                Err(e) => {
                    tracing::warn!("Failed to read config at {}: {e}", path.display());
                }
            }
        }
        let config = Self::default();
        // Try to save default config for user convenience
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        match toml::to_string_pretty(&config) {
            Ok(toml_str) => {
                if fs::write(&path, toml_str).is_ok() {
                    tracing::info!("Created default config at {}", path.display());
                }
            }
            Err(e) => tracing::warn!("Failed to serialize default config: {e}"),
        }
        config
    }

    /// Save current config to disk
    pub fn save(&self) -> anyhow::Result<()> {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let toml_str = toml::to_string_pretty(self)?;
        fs::write(&path, toml_str)?;
        tracing::info!("Saved config to {}", path.display());
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: default AppConfig has all expected values
    #[test]
    fn test_config_default() {
        let config = AppConfig::default();
        assert_eq!(config.backend.ws_url, "ws://localhost:8765/ws/office",
            "AI Agent: default ws_url must match Python backend");
        assert_eq!(config.backend.http_url, "http://localhost:8765",
            "AI Agent: default http_url must match Python backend");
        assert_eq!(config.backend.reconnect_backoff_ms, 500);
        assert_eq!(config.backend.reconnect_backoff_max_ms, 30_000);
        assert_eq!(config.backend.http_timeout_secs, 30);
        assert_eq!(config.ui.default_theme, "synthwave",
            "AI Agent: default theme must be synthwave");
        assert!(config.ui.mouse_enabled, "AI Agent: mouse enabled by default");
        assert_eq!(config.ui.fps, 60, "AI Agent: default fps is 60");
        assert_eq!(config.library.default_domain, "web_text",
            "AI Agent: default domain must match");
        assert_eq!(config.library.default_lang, "id",
            "AI Agent: default lang must be id");
        assert_eq!(config.library.min_quality_display, 0.0);
        assert_eq!(config.library.max_shelf_depth, 4);
    }

    // AI Agent verifies: config serializes and deserializes without data loss
    #[test]
    fn test_config_serialization() {
        let config = AppConfig::default();
        let toml_str = toml::to_string_pretty(&config)
            .expect("AI Agent: serialization must succeed");
        let parsed: AppConfig = toml::from_str(&toml_str)
            .expect("AI Agent: deserialization must succeed");

        // AI Agent invariant: roundtrip must preserve all values
        assert_eq!(parsed.backend.ws_url, config.backend.ws_url);
        assert_eq!(parsed.backend.http_url, config.backend.http_url);
        assert_eq!(parsed.backend.reconnect_backoff_ms, config.backend.reconnect_backoff_ms);
        assert_eq!(parsed.backend.reconnect_backoff_max_ms, config.backend.reconnect_backoff_max_ms);
        assert_eq!(parsed.backend.http_timeout_secs, config.backend.http_timeout_secs);
        assert_eq!(parsed.ui.default_theme, config.ui.default_theme);
        assert_eq!(parsed.ui.mouse_enabled, config.ui.mouse_enabled);
        assert_eq!(parsed.ui.fps, config.ui.fps);
        assert_eq!(parsed.library.default_domain, config.library.default_domain);
        assert_eq!(parsed.library.default_lang, config.library.default_lang);
        assert_eq!(parsed.library.min_quality_display, config.library.min_quality_display);
        assert_eq!(parsed.library.max_shelf_depth, config.library.max_shelf_depth);
    }

    // AI Agent verifies: synthwave theme returns index 0
    #[test]
    fn test_default_theme_index() {
        let config = AppConfig::default();
        assert_eq!(config.ui.default_theme_index(), 0,
            "AI Agent: synthwave must be theme index 0");
    }
}
