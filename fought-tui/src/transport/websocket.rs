use tokio::sync::mpsc;
use tokio_tungstenite::connect_async;
use futures_util::StreamExt;

use super::types::BackendEvent;
use crate::app::AppEvent;

/// Connect to the Python backend WebSocket event stream.
/// Implements exponential backoff on connection failure — fixing the Python TUI's flat retry bug.
pub async fn connect_event_stream(url: &str, tx: mpsc::UnboundedSender<AppEvent>) {
    let mut backoff_ms: u64 = 500;
    let max_backoff_ms: u64 = 30_000;

    loop {
        match connect_async(url).await {
            Ok((ws_stream, _)) => {
                backoff_ms = 500; // Reset backoff after successful connect
                tracing::info!("WebSocket connected to {}", url);
                let (_write, mut read) = ws_stream.split();

                while let Some(msg) = read.next().await {
                    match msg {
                        Ok(msg) if msg.is_text() => {
                            let text = msg.to_text().unwrap_or("");
                            if let Ok(event) = serde_json::from_str::<BackendEvent>(text) {
                                let _ = tx.send(AppEvent::Backend(event));
                            } else {
                                tracing::debug!("Failed to parse backend event: {}", &text[..text.len().min(200)]);
                            }
                        }
                        Ok(_) => {
                            // Ping/pong or binary — ignore
                        }
                        Err(e) => {
                            tracing::warn!("WebSocket read error: {e}");
                            break; // Reconnect
                        }
                    }
                }

                tracing::warn!("WebSocket stream ended, reconnecting...");
            }
            Err(e) => {
                tracing::warn!("WebSocket connect failed: {e}, retry in {backoff_ms}ms");
            }
        }

        // Exponential backoff (fix from Python TUI which had flat retry)
        tokio::time::sleep(tokio::time::Duration::from_millis(backoff_ms)).await;
        backoff_ms = (backoff_ms * 2).min(max_backoff_ms);
    }
}
