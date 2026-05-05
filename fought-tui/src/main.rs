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

use app::App;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .with_level(true)
        .init();

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Channels for async events
    let (event_tx, event_rx) = mpsc::unbounded_channel();
    let (action_tx, action_rx) = mpsc::unbounded_channel::<app::Action>();

    // Spawn WebSocket listener
    let ws_url = std::env::var("FOUGHT_WS_URL")
        .unwrap_or_else(|_| "ws://localhost:8765/ws/office".to_string());
    let ws_event_tx = event_tx.clone();
    tokio::spawn(async move {
        transport::websocket::connect_event_stream(&ws_url, ws_event_tx).await;
    });

    // Spawn crossterm event listener
    let crossterm_tx = event_tx.clone();
    tokio::spawn(async move {
        loop {
            if crossterm::event::poll(std::time::Duration::from_millis(100)).is_ok() {
                if let Ok(ev) = crossterm::event::read() {
                    let _ = crossterm_tx.send(app::AppEvent::Crossterm(ev));
                }
            }
        }
    });

    // Create app
    let http_url = std::env::var("FOUGHT_HTTP_URL")
        .unwrap_or_else(|_| "http://localhost:8765".to_string());
    let backend_client = transport::http::BackendClient::new(&http_url);
    let mut app = App::new(backend_client, event_rx, action_rx);

    // Run app
    let result = app.run(&mut terminal).await;

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
