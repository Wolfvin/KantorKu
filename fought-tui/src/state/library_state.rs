use std::collections::HashSet;

use serde::{Deserialize, Serialize};

/// Library mode state
#[derive(Debug, Clone)]
pub struct LibraryState {
    // Shelf
    pub shelves: Vec<Shelf>,
    pub shelf_count: usize,
    pub entry_count: usize,
    pub shelf_breadcrumb: Vec<String>,
    pub shelf_expanded: HashSet<String>,
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
    pub ask_cursor: usize,
    pub archivist_chunks: Vec<(String, String)>,
    pub archivist_sources: Vec<SourceRef>,
    pub archivist_streaming: Vec<String>,
    pub ask_history: Vec<AskMessage>,

    // Ingest
    pub ingest_title: String,
    pub ingest_content: String,
    pub ingest_step: IngestStep,

    // Search
    pub search_query: String,
    pub search_mode: bool,
    pub search_results: Vec<LibraryEntryBrief>,

    // Input focus
    pub input_focused: bool,
}

#[derive(Debug, Clone, PartialEq, Copy)]
pub enum ContentMode {
    Browse,
    Ask,
    Ingest,
}

impl Default for ContentMode {
    fn default() -> Self { ContentMode::Browse }
}

impl ContentMode {
    pub fn label(self) -> &'static str {
        match self {
            ContentMode::Browse => "Browse",
            ContentMode::Ask => "Ask",
            ContentMode::Ingest => "Ingest",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Copy)]
pub enum IngestStep {
    Input,
    Analyzing,
    Confirm,
    Done,
}

impl Default for IngestStep {
    fn default() -> Self { IngestStep::Input }
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
    },
    Entry {
        depth: usize,
        entry: LibraryEntryBrief,
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
    pub role: String,
    pub content: String,
    pub sources: Vec<SourceRef>,
    pub timestamp: String,
}

impl LibraryState {
    pub fn scroll_up(&mut self) {
        match self.content_mode {
            ContentMode::Browse => {
                if self.shelf_selection > 0 {
                    self.shelf_selection -= 1;
                }
            }
            ContentMode::Ask => {
                self.reader_scroll = self.reader_scroll.saturating_sub(3);
            }
            ContentMode::Ingest => {}
        }
    }

    pub fn scroll_down(&mut self) {
        match self.content_mode {
            ContentMode::Browse => {
                let max = self.visible_items.len().saturating_sub(1);
                if self.shelf_selection < max {
                    self.shelf_selection += 1;
                }
            }
            ContentMode::Ask => {
                self.reader_scroll = self.reader_scroll.saturating_add(3);
            }
            ContentMode::Ingest => {}
        }
    }
}

impl Default for LibraryState {
    fn default() -> Self {
        Self {
            shelves: vec![
                Shelf { name: "Engineering".into(), path: vec!["Engineering".into()], entry_count: 0, quality_avg: 0.0, last_updated: None, children: vec![
                    Shelf { name: "Backend".into(), path: vec!["Engineering".into(), "Backend".into()], entry_count: 0, quality_avg: 0.0, last_updated: None, children: vec![], is_expanded: false },
                    Shelf { name: "Frontend".into(), path: vec!["Engineering".into(), "Frontend".into()], entry_count: 0, quality_avg: 0.0, last_updated: None, children: vec![], is_expanded: false },
                ], is_expanded: false },
                Shelf { name: "Mathematics".into(), path: vec!["Mathematics".into()], entry_count: 0, quality_avg: 0.0, last_updated: None, children: vec![], is_expanded: false },
                Shelf { name: "Science".into(), path: vec!["Science".into()], entry_count: 0, quality_avg: 0.0, last_updated: None, children: vec![], is_expanded: false },
            ],
            shelf_count: 3,
            entry_count: 0,
            shelf_breadcrumb: vec![],
            shelf_expanded: HashSet::new(),
            shelf_selection: 0,
            shelf_scroll: 0,
            visible_items: vec![],
            current_entries: vec![],
            current_entry: None,
            reader_scroll: 0,
            content_mode: ContentMode::Browse,
            ask_input: String::new(),
            ask_cursor: 0,
            archivist_chunks: vec![],
            archivist_sources: vec![],
            archivist_streaming: vec![],
            ask_history: vec![],
            ingest_title: String::new(),
            ingest_content: String::new(),
            ingest_step: IngestStep::Input,
            search_query: String::new(),
            search_mode: false,
            search_results: vec![],
            input_focused: true,
        }
    }
}

/// Entry type icons — SYNC with Python models.py ENTRY_TYPE_ICONS
pub fn entry_type_icon(entry_type: &str) -> &'static str {
    match entry_type {
        "knowledge" => "\u{1F4D6}",  // 📖
        "solution"  => "\u{1F4A1}",  // 💡
        "qa_pair"   => "\u{1F4AC}",  // 💬
        "procedure" => "\u{1F527}",  // 🔧
        _           => "\u{1F4C4}",  // 📄
    }
}

/// Entry type label fallback for terminals without emoji
pub fn entry_type_label(entry_type: &str) -> &'static str {
    match entry_type {
        "knowledge" => "[K]",
        "solution"  => "[S]",
        "qa_pair"   => "[Q]",
        "procedure" => "[P]",
        _           => "[?]",
    }
}
