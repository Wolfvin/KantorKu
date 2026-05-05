#![allow(dead_code, unused_imports)]

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

fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .with_level(true)
        .with_writer(std::io::stderr) // Don't pollute stdout (used by TUI)
        .init();

    // Load config
    let config = state::config::AppConfig::load_or_default();

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

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
    let backend_client = transport::http::BackendClient::new(&config.backend.http_url);
    let mut app = App::new(config, backend_client, event_rx, action_rx, action_tx.clone());

    // Run app
    let result = app.run(&mut terminal);

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    result
}
