use anyhow::Result;
use serde::{Deserialize, Serialize};

use crate::state::library_state::{LibraryEntry, Shelf};

#[derive(Debug, Clone, Deserialize)]
pub struct ArchivistResponse {
    pub answer: String,
    pub sources: Vec<SourceRef>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SourceRef {
    pub entry_id: String,
    pub title: String,
    pub relevance: f32,
}

pub struct BackendClient {
    client: reqwest::Client,
    base_url: String,
}

impl BackendClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .unwrap_or_default(),
            base_url: base_url.to_string(),
        }
    }

    // === KANTOR ENDPOINTS ===

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

    pub async fn get_sessions(&self) -> Result<Vec<SessionBrief>> {
        let sessions = self.client
            .get(format!("{}/sessions", self.base_url))
            .send()
            .await?
            .json::<Vec<SessionBrief>>()
            .await?;
        Ok(sessions)
    }

    pub async fn get_status(&self) -> Result<serde_json::Value> {
        let status = self.client
            .get(format!("{}/status", self.base_url))
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;
        Ok(status)
    }

    pub async fn get_cost(&self) -> Result<serde_json::Value> {
        let cost = self.client
            .get(format!("{}/cost", self.base_url))
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;
        Ok(cost)
    }

    pub async fn get_health(&self) -> Result<serde_json::Value> {
        let health = self.client
            .get(format!("{}/health/dashboard", self.base_url))
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;
        Ok(health)
    }

    // === LIBRARY ENDPOINTS ===

    pub async fn get_shelves(&self) -> Result<Vec<Shelf>> {
        let shelves = self.client
            .get(format!("{}/library/shelves", self.base_url))
            .send()
            .await?
            .json::<Vec<Shelf>>()
            .await?;
        Ok(shelves)
    }

    pub async fn get_entries(&self, shelf_path: &[String]) -> Result<Vec<crate::state::library_state::LibraryEntryBrief>> {
        let path = shelf_path.join("/");
        let entries = self.client
            .get(format!("{}/library/shelves/{}/entries", self.base_url, path))
            .send()
            .await?
            .json::<Vec<crate::state::library_state::LibraryEntryBrief>>()
            .await?;
        Ok(entries)
    }

    pub async fn get_entry(&self, entry_id: &str) -> Result<LibraryEntry> {
        let entry = self.client
            .get(format!("{}/library/entries/{}", self.base_url, entry_id))
            .send()
            .await?
            .json::<LibraryEntry>()
            .await?;
        Ok(entry)
    }

    pub async fn ask_archivist(&self, query: &str) -> Result<ArchivistResponse> {
        let response = self.client
            .post(format!("{}/library/ask", self.base_url))
            .json(&serde_json::json!({ "query": query }))
            .send()
            .await?
            .json::<ArchivistResponse>()
            .await?;
        Ok(response)
    }

    pub async fn ingest_entry(&self, title: &str, content: &str) -> Result<LibraryEntry> {
        let entry = self.client
            .post(format!("{}/library/ingest", self.base_url))
            .json(&serde_json::json!({ "title": title, "content": content }))
            .send()
            .await?
            .json::<LibraryEntry>()
            .await?;
        Ok(entry)
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
}

#[derive(Debug, Clone, Deserialize)]
pub struct SessionBrief {
    pub session_id: String,
    pub state: String,
    pub created_at: String,
    pub cost_usd: f64,
}
