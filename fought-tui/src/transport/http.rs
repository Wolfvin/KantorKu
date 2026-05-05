use anyhow::Result;
use serde::Deserialize;

use crate::state::library_state::{LibraryEntry, LibraryEntryBrief, Shelf};

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)] // Fields used for serde deserialization
pub struct ArchivistResponse {
    pub answer: String,
    pub sources: Vec<crate::state::library_state::SourceRef>,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)] // Fields used for serde deserialization
pub struct SessionBrief {
    pub session_id: String,
    pub state: String,
    pub created_at: String,
    pub cost_usd: f64,
}

#[derive(Debug, Clone)]
#[allow(dead_code)] // API client methods used at runtime
pub struct BackendClient {
    client: reqwest::Client,
    base_url: String,
}

impl BackendClient {
    pub fn new(base_url: &str, timeout_secs: u64) -> Self {
        Self {
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(timeout_secs))
                .build()
                .unwrap_or_else(|e| {
                    tracing::warn!("Failed to build HTTP client with TLS: {e}, using default");
                    reqwest::Client::new()
                }),
            base_url: base_url.to_string(),
        }
    }

    // === KANTOR ENDPOINTS (core — actively used) ===

    pub async fn send_message(&self, session_id: &str, message: &str) -> Result<()> {
        self.client
            .post(format!("{}/sessions/{}/message", self.base_url, session_id))
            .json(&serde_json::json!({ "message": message }))
            .send()
            .await?;
        Ok(())
    }

    pub async fn accept_contract(&self, session_id: &str) -> Result<()> {
        self.client
            .post(format!("{}/sessions/{}/accept", self.base_url, session_id))
            .send()
            .await?;
        Ok(())
    }

    pub async fn revise_contract(&self, session_id: &str, feedback: &str) -> Result<()> {
        self.client
            .post(format!("{}/sessions/{}/revise", self.base_url, session_id))
            .json(&serde_json::json!({ "feedback": feedback }))
            .send()
            .await?;
        Ok(())
    }

    // === KANTOR ENDPOINTS (status — used by future dashboard/status views) ===
    #[allow(dead_code)] // API-complete: used when status panels are implemented
    pub async fn get_sessions(&self) -> Result<Vec<SessionBrief>> {
        Ok(self.client
            .get(format!("{}/sessions", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    #[allow(dead_code)] // API-complete: used when status panels are implemented
    pub async fn get_status(&self) -> Result<serde_json::Value> {
        Ok(self.client
            .get(format!("{}/status", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    #[allow(dead_code)] // API-complete: used when cost panels are implemented
    pub async fn get_cost(&self) -> Result<serde_json::Value> {
        Ok(self.client
            .get(format!("{}/cost", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    #[allow(dead_code)] // API-complete: used when health dashboard is implemented
    pub async fn get_health(&self) -> Result<serde_json::Value> {
        Ok(self.client
            .get(format!("{}/health/dashboard", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    #[allow(dead_code)] // API-complete: used when memory stats panel is implemented
    pub async fn get_memory_stats(&self) -> Result<serde_json::Value> {
        Ok(self.client
            .get(format!("{}/memory/stats", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    #[allow(dead_code)] // API-complete: used when circuit breaker panel is implemented
    pub async fn get_circuit_breakers(&self) -> Result<serde_json::Value> {
        Ok(self.client
            .get(format!("{}/circuit-breaker", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    // === LIBRARY ENDPOINTS ===

    #[allow(dead_code)] // API-complete: used by initial state fetch
    pub async fn get_shelves(&self) -> Result<Vec<Shelf>> {
        Ok(self.client
            .get(format!("{}/library/shelves", self.base_url))
            .send()
            .await?
            .json()
            .await?)
    }

    pub async fn get_entries(&self, shelf_path: &[String]) -> Result<Vec<LibraryEntryBrief>> {
        // URL-encode each segment of the shelf path to handle special characters
        let path: String = shelf_path.iter()
            .map(|s| percent_encoding::utf8_percent_encode(s, percent_encoding::NON_ALPHANUMERIC).to_string())
            .collect::<Vec<_>>()
            .join("/");
        Ok(self.client
            .get(format!("{}/library/shelves/{}/entries", self.base_url, path))
            .send()
            .await?
            .json()
            .await?)
    }

    pub async fn get_entry(&self, entry_id: &str) -> Result<LibraryEntry> {
        Ok(self.client
            .get(format!("{}/library/entries/{}", self.base_url, entry_id))
            .send()
            .await?
            .json()
            .await?)
    }

    pub async fn ask_archivist(&self, query: &str) -> Result<ArchivistResponse> {
        Ok(self.client
            .post(format!("{}/library/ask", self.base_url))
            .json(&serde_json::json!({ "query": query }))
            .send()
            .await?
            .json()
            .await?)
    }

    pub async fn ingest_entry(&self, title: &str, content: &str) -> Result<LibraryEntry> {
        Ok(self.client
            .post(format!("{}/library/ingest", self.base_url))
            .json(&serde_json::json!({ "title": title, "content": content }))
            .send()
            .await?
            .json()
            .await?)
    }

    pub async fn mark_helpful(&self, entry_id: &str) -> Result<()> {
        self.client
            .post(format!("{}/library/entries/{}/helpful", self.base_url, entry_id))
            .send()
            .await?;
        Ok(())
    }

    pub async fn mark_unhelpful(&self, entry_id: &str) -> Result<()> {
        self.client
            .post(format!("{}/library/entries/{}/unhelpful", self.base_url, entry_id))
            .send()
            .await?;
        Ok(())
    }

    pub async fn search_entries(&self, query: &str) -> Result<Vec<LibraryEntryBrief>> {
        Ok(self.client
            .get(format!("{}/library/search", self.base_url))
            .query(&[("q", query)])
            .send()
            .await?
            .json()
            .await?)
    }
}
