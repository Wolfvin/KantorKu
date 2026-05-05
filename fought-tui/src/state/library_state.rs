use serde::{Deserialize, Serialize};

/// Library mode state
#[derive(Debug, Clone, Default)]
pub struct LibraryState {
    // Shelf
    pub shelves: Vec<Shelf>,
    pub shelf_count: usize,
    pub entry_count: usize,
    pub shelf_breadcrumb: Vec<String>,
    pub shelf_expanded: std::collections::HashSet<String>,
    pub shelf_selection: usize,
    pub shelf_scroll: usize,
    pub visible_items: Vec<ShelfItem>,

    // Entries
    pub current_entries: Vec<LibraryEntryBrief>,
    pub current_entry: Option<LibraryEntry>,
    pub reader_scroll: u16,

    // Ask panel
    pub content_mode: ContentMode,
    pub ask_input: String,
    pub archivist_chunks: Vec<(String, String)>, // (query_id, chunk)
    pub archivist_sources: Vec<SourceRef>,
    pub ask_history: Vec<AskMessage>,

    // Ingest
    pub ingest_title: String,
    pub ingest_content: String,
    pub ingest_step: IngestStep,

    // Search
    pub search_query: String,
    pub search_mode: bool,
    pub search_results: Vec<LibraryEntryBrief>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ContentMode {
    Browse,
    Ask,
    Ingest,
}

impl Default for ContentMode {
    fn default() -> Self {
        ContentMode::Browse
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum IngestStep {
    Input,
    Analyzing,
    Confirm,
    Done,
}

impl Default for IngestStep {
    fn default() -> Self {
        IngestStep::Input
    }
}

// === Data Models — MUST match Python models.py ===

/// Full library entry — mirrors Python LibraryEntry dataclass
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct LibraryEntry {
    pub id: String,
    pub created_at: String,
    pub updated_at: String,
    pub source: String,
    pub title: String,
    pub content: String,
    pub summary: String,
    pub keywords: Vec<String>,
    pub entry_type: String,
    pub domain: String,
    pub lang: String,
    pub shelf_path: Vec<String>,
    pub shelf_confidence: f32,
    pub related_ids: Vec<String>,
    pub supersedes_id: Option<String>,
    pub solution_for: Option<String>,
    pub quality_score: f32,
    pub verified: bool,
    pub usage_count: u32,
    pub was_helpful: u32,
    pub was_unhelpful: u32,
    pub origin_session_id: Option<String>,
    pub origin_worker_id: Option<String>,
    pub origin_task_id: Option<String>,
    pub problem_description: Option<String>,
    pub failed_attempts: Vec<serde_json::Value>,
    pub solution_code: Option<String>,
    pub verification_result: Option<String>,
    pub question: Option<String>,
    pub answer: Option<String>,
    pub source_entry_ids: Vec<String>,
    pub steps: Vec<serde_json::Value>,
}

/// Brief entry for shelf display
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct LibraryEntryBrief {
    pub id: String,
    pub title: String,
    pub entry_type: String,
    pub quality_score: f32,
    pub verified: bool,
    pub usage_count: u32,
    pub shelf_path: Vec<String>,
    pub updated_at: String,
}

/// Shelf tree node — mirrors Python ShelfNode
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Shelf {
    pub name: String,
    pub path: Vec<String>,
    pub entry_count: u32,
    pub quality_avg: f32,
    pub last_updated: Option<String>,
    pub children: Vec<Shelf>,
    #[serde(default)]
    pub is_expanded: bool,
}

/// Flattened shelf item for rendering
#[derive(Debug, Clone)]
pub enum ShelfItem {
    Shelf {
        depth: usize,
        name: String,
        full_path: Vec<String>,
        entry_count: usize,
        is_expanded: bool,
        is_selected: bool,
    },
    Entry {
        depth: usize,
        entry: LibraryEntryBrief,
        is_selected: bool,
    },
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SourceRef {
    pub entry_id: String,
    pub title: String,
    pub relevance: f32,
}

#[derive(Debug, Clone)]
pub struct AskMessage {
    pub role: String, // "user" or "archivist"
    pub content: String,
    pub sources: Vec<SourceRef>,
    pub timestamp: String,
}

/// Entry type icons — SYNC with Python models.py ENTRY_TYPE_ICONS
pub fn entry_type_icon(entry_type: &str) -> &'static str {
    match entry_type {
        "knowledge" => "\u{1F4D6}",  // 📖
        "solution" => "\u{1F4A1}",   // 💡
        "qa_pair" => "\u{1F4AC}",    // 💬
        "procedure" => "\u{1F527}",  // 🔧
        _ => "\u{1F4C4}",            // 📄
    }
}

/// Entry type display names for terminal fallback when emoji doesn't render
pub fn entry_type_label(entry_type: &str) -> &'static str {
    match entry_type {
        "knowledge" => "[K]",
        "solution" => "[S]",
        "qa_pair" => "[Q]",
        "procedure" => "[P]",
        _ => "[?]",
    }
}
