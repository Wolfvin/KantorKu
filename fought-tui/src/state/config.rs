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
