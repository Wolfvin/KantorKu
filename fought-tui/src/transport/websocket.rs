use futures_util::StreamExt;
use tokio::sync::mpsc;
use tokio_tungstenite::connect_async;

use crate::app::AppEvent;

/// Connect to the Python backend WebSocket event stream.
/// Implements exponential backoff on connection failure — fixing the Python TUI's flat retry bug.
pub async fn connect_event_stream(url: &str, tx: mpsc::UnboundedSender<AppEvent>) {
    let mut backoff_ms: u64 = 500;
    let max_backoff_ms: u64 = 30_000;
    let mut connect_attempts: u32 = 0;

    loop {
        connect_attempts += 1;
        tracing::info!("WebSocket connecting to {} (attempt #{})...", url, connect_attempts);

        // Notify app that we're connecting
        let _ = tx.send(AppEvent::Backend(Box::new(
            crate::transport::types::BackendEvent::WsConnecting
        )));

        match connect_async(url).await {
            Ok((ws_stream, _)) => {
                backoff_ms = 500; // Reset backoff after successful connect
                connect_attempts = 0;
                tracing::info!("WebSocket connected to {}", url);

                // Notify app that we're connected
                let _ = tx.send(AppEvent::Backend(Box::new(
                    crate::transport::types::BackendEvent::WsConnected
                )));

                let (_write, mut read) = ws_stream.split();

                while let Some(msg) = read.next().await {
                    match msg {
                        Ok(msg) if msg.is_text() => {
                            let text = msg.to_text().unwrap_or("");
                            match serde_json::from_str::<crate::transport::types::BackendEvent>(text) {
                                Ok(event) => {
                                    if tx.send(AppEvent::Backend(Box::new(event))).is_err() {
                                        tracing::warn!("Event channel closed, exiting WebSocket loop");
                                        return;
                                    }
                                }
                                Err(e) => {
                                    // Not every message is a BackendEvent (e.g. pings, health checks)
                                    tracing::debug!("Non-event WS message ({}): {}", e, crate::truncate_str(text, 100));
                                }
                            }
                        }
                        Ok(msg) if msg.is_ping() || msg.is_pong() => {
                            // Heartbeat, ignore
                        }
                        Ok(_) => {
                            // Binary or close frame, ignore
                        }
                        Err(e) => {
                            tracing::warn!("WebSocket read error: {e}");
                            break; // Reconnect
                        }
                    }
                }

                tracing::warn!("WebSocket stream ended, reconnecting...");
                let _ = tx.send(AppEvent::Backend(Box::new(
                    crate::transport::types::BackendEvent::WsDisconnected
                )));
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
