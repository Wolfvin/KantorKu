mod app;
mod modes;
mod panels;
mod state;
mod transport;
mod ui;

use std::io;

use crossterm::{
    event::{DisableMouseCapture, EnableMouseCapture},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use tokio::sync::mpsc;

use app::{App, AppEvent};

/// Guard that restores the terminal on drop — even if the app panics.
struct RawModeGuard;

impl Drop for RawModeGuard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let mut stdout = io::stdout();
        let _ = execute!(stdout, LeaveAlternateScreen, DisableMouseCapture);
        let _ = Terminal::new(CrosstermBackend::new(stdout)).map(|mut t| t.show_cursor());
    }
}

/// CLI arguments
#[derive(clap::Parser, Debug)]
#[command(name = "fought-tui", version, about = "Fought — Agentic Engineering Platform TUI")]
struct Args {
    /// HTTP base URL for the Python backend
    #[arg(long, default_value = "http://localhost:8765", env = "FOUGHT_HTTP_URL")]
    http_url: String,

    /// WebSocket URL for the event stream
    #[arg(long, default_value = "ws://localhost:8765/ws/office", env = "FOUGHT_WS_URL")]
    ws_url: String,

    /// Theme name to use
    #[arg(long, default_value = "synthwave")]
    theme: String,

    /// Disable mouse support
    #[arg(long)]
    no_mouse: bool,

    /// Target FPS
    #[arg(long, default_value_t = 60)]
    fps: u64,
}

fn main() -> anyhow::Result<()> {
    // Parse CLI args
    let args = <Args as clap::Parser>::parse();

    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .with_level(true)
        .with_writer(std::io::stderr) // Don't pollute stdout (used by TUI)
        .init();

    // Load config (CLI args override config file)
    let mut config = state::config::AppConfig::load_or_default();
    if args.http_url != "http://localhost:8765" || std::env::var("FOUGHT_HTTP_URL").is_ok() {
        config.backend.http_url = args.http_url;
    }
    if args.ws_url != "ws://localhost:8765/ws/office" || std::env::var("FOUGHT_WS_URL").is_ok() {
        config.backend.ws_url = args.ws_url;
    }
    if args.theme != "synthwave" {
        config.ui.default_theme = args.theme;
    }
    if args.no_mouse {
        config.ui.mouse_enabled = false;
    }
    config.ui.fps = args.fps;

    // Setup terminal — with panic guard
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    if config.ui.mouse_enabled {
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    } else {
        execute!(stdout, EnterAlternateScreen)?;
    }
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Install the panic guard AFTER terminal setup
    let _guard = RawModeGuard;

    // Create channels
    let (event_tx, event_rx) = mpsc::unbounded_channel();
    let (action_tx, action_rx) = mpsc::unbounded_channel::<app::Action>();

    // Spawn WebSocket listener
    let ws_url = config.backend.ws_url.clone();
    let ws_event_tx = event_tx.clone();
    tokio::spawn(async move {
        transport::websocket::connect_event_stream(&ws_url, ws_event_tx).await;
    });

    // Spawn crossterm event listener (poll-based for compatibility)
    let crossterm_tx = event_tx.clone();
    std::thread::spawn(move || {
        loop {
            if crossterm::event::poll(std::time::Duration::from_millis(16)).is_ok() {
                if let Ok(ev) = crossterm::event::read() {
                    if crossterm_tx.send(AppEvent::Crossterm(ev)).is_err() {
                        break; // Channel closed, exit thread
                    }
                }
            }
        }
    });

    // Create app
    let backend_client = transport::http::BackendClient::new(
        &config.backend.http_url,
        config.backend.http_timeout_secs,
    );
    let mut app = App::new(config, backend_client, event_rx, action_rx, action_tx.clone(), event_tx);

    // Run app
    let result = app.run(&mut terminal);

    // Save config on quit
    if let Err(e) = app.config.save() {
        tracing::warn!("Failed to save config on quit: {e}");
    }

    // Guard will restore terminal on drop, but we also do it explicitly for the Ok path
    result
}
