use std::collections::HashSet;

use serde::{Deserialize, Serialize};

/// Library mode state
#[derive(Debug, Clone)]
#[allow(dead_code)] // State fields accessed by render methods
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
    pub archivist_sources: Vec<SourceRef>,
    pub archivist_streaming: Vec<String>,
    pub ask_history: Vec<AskMessage>,

    // Ingest
    pub ingest_title: String,
    pub ingest_content: String,
    pub ingest_step: IngestStep,
    /// Which ingest field is active: title or content
    pub ingest_field_active: IngestField,

    // Search
    pub search_query: String,
    pub search_mode: bool,
    pub search_results: Vec<LibraryEntryBrief>,

    // Input focus
    pub input_focused: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Copy)]
#[derive(Default)]
pub enum ContentMode {
    #[default]
    Browse,
    Ask,
    Ingest,
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

#[derive(Debug, Clone, PartialEq, Eq, Copy)]
#[derive(Default)]
pub enum IngestStep {
    #[default]
    Input,
    Analyzing,
    Confirm,
    Done,
}


/// Which field in the ingest form is active
#[derive(Debug, Clone, PartialEq, Eq, Copy)]
#[derive(Default)]
pub enum IngestField {
    #[default]
    Title,
    Content,
}


// === Data Models — MUST match Python models.py ===

/// Full library entry — mirrors Python LibraryEntry dataclass
#[derive(Debug, Clone, Deserialize, Serialize)]
#[allow(dead_code)] // Fields used for serde deserialization
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
#[allow(dead_code)] // Fields used for serde deserialization
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
#[allow(dead_code)] // Fields used for serde deserialization
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
#[allow(dead_code)] // Fields used for serde deserialization
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
            archivist_sources: vec![],
            archivist_streaming: vec![],
            ask_history: vec![],
            ingest_title: String::new(),
            ingest_content: String::new(),
            ingest_step: IngestStep::Input,
            ingest_field_active: IngestField::Title,
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

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: all ContentMode variants return correct labels
    #[test]
    fn test_content_mode_label() {
        assert_eq!(ContentMode::Browse.label(), "Browse", "AI Agent: Browse label must match");
        assert_eq!(ContentMode::Ask.label(), "Ask", "AI Agent: Ask label must match");
        assert_eq!(ContentMode::Ingest.label(), "Ingest", "AI Agent: Ingest label must match");
    }

    // AI Agent verifies: IngestStep default is Input
    #[test]
    fn test_ingest_step_default() {
        assert_eq!(IngestStep::default(), IngestStep::Input,
            "AI Agent invariant: IngestStep default must be Input");
    }

    // AI Agent verifies: IngestField default is Title
    #[test]
    fn test_ingest_field_default() {
        assert_eq!(IngestField::default(), IngestField::Title,
            "AI Agent invariant: IngestField default must be Title");
    }

    // AI Agent verifies: all known entry types return correct emoji icon
    #[test]
    fn test_entry_type_icon() {
        assert_eq!(entry_type_icon("knowledge"), "\u{1F4D6}", "AI Agent: knowledge → 📖");
        assert_eq!(entry_type_icon("solution"), "\u{1F4A1}", "AI Agent: solution → 💡");
        assert_eq!(entry_type_icon("qa_pair"), "\u{1F4AC}", "AI Agent: qa_pair → 💬");
        assert_eq!(entry_type_icon("procedure"), "\u{1F527}", "AI Agent: procedure → 🔧");
        assert_eq!(entry_type_icon("unknown"), "\u{1F4C4}", "AI Agent: unknown → 📄 fallback");
        assert_eq!(entry_type_icon(""), "\u{1F4C4}", "AI Agent: empty → 📄 fallback");
    }

    // AI Agent verifies: all known entry types return correct text label
    #[test]
    fn test_entry_type_label() {
        assert_eq!(entry_type_label("knowledge"), "[K]", "AI Agent: knowledge → [K]");
        assert_eq!(entry_type_label("solution"), "[S]", "AI Agent: solution → [S]");
        assert_eq!(entry_type_label("qa_pair"), "[Q]", "AI Agent: qa_pair → [Q]");
        assert_eq!(entry_type_label("procedure"), "[P]", "AI Agent: procedure → [P]");
        assert_eq!(entry_type_label("other"), "[?]", "AI Agent: unknown → [?] fallback");
        assert_eq!(entry_type_label(""), "[?]", "AI Agent: empty → [?] fallback");
    }

    // AI Agent verifies: default LibraryState has all expected values
    #[test]
    fn test_library_state_default() {
        let state = LibraryState::default();
        assert!(!state.shelves.is_empty(), "AI Agent: default shelves should not be empty");
        assert_eq!(state.shelf_count, 3, "AI Agent: default shelf_count is 3");
        assert_eq!(state.entry_count, 0, "AI Agent: no entries at start");
        assert!(state.shelf_breadcrumb.is_empty(), "AI Agent: no breadcrumb at start");
        assert!(state.shelf_expanded.is_empty(), "AI Agent: no expanded shelves at start");
        assert_eq!(state.shelf_selection, 0, "AI Agent: shelf selection starts at 0");
        assert_eq!(state.shelf_scroll, 0, "AI Agent: shelf scroll starts at 0");
        assert!(state.visible_items.is_empty(), "AI Agent: no visible items at start");
        assert!(state.current_entries.is_empty(), "AI Agent: no current entries at start");
        assert!(state.current_entry.is_none(), "AI Agent: no current entry at start");
        assert_eq!(state.reader_scroll, 0, "AI Agent: reader scroll starts at 0");
        assert_eq!(state.content_mode, ContentMode::Browse, "AI Agent: default mode is Browse");
        assert!(state.ask_input.is_empty(), "AI Agent: ask input empty at start");
        assert!(state.archivist_sources.is_empty(), "AI Agent: no sources at start");
        assert!(state.archivist_streaming.is_empty(), "AI Agent: no streaming at start");
        assert!(state.ask_history.is_empty(), "AI Agent: no ask history at start");
        assert!(state.ingest_title.is_empty(), "AI Agent: ingest title empty at start");
        assert!(state.ingest_content.is_empty(), "AI Agent: ingest content empty at start");
        assert_eq!(state.ingest_step, IngestStep::Input, "AI Agent: default ingest step is Input");
        assert_eq!(state.ingest_field_active, IngestField::Title, "AI Agent: default ingest field is Title");
        assert!(state.search_query.is_empty(), "AI Agent: search query empty at start");
        assert!(!state.search_mode, "AI Agent: search mode off at start");
        assert!(state.search_results.is_empty(), "AI Agent: no search results at start");
        assert!(state.input_focused, "AI Agent: input focused by default");
    }

    // AI Agent verifies: scroll_up in Browse mode decrements shelf_selection (clamped at 0)
    #[test]
    fn test_library_state_scroll_browse() {
        let mut state = LibraryState::default();
        state.content_mode = ContentMode::Browse;
        state.shelf_selection = 0;

        // Scroll up at 0 stays at 0
        state.scroll_up();
        assert_eq!(state.shelf_selection, 0, "AI Agent: scroll_up at 0 stays at 0");

        // Set up some visible items for scroll_down
        state.visible_items = vec![
            ShelfItem::Shelf { depth: 0, name: "A".into(), full_path: vec!["A".into()], entry_count: 1, is_expanded: false },
            ShelfItem::Shelf { depth: 0, name: "B".into(), full_path: vec!["B".into()], entry_count: 2, is_expanded: false },
            ShelfItem::Shelf { depth: 0, name: "C".into(), full_path: vec!["C".into()], entry_count: 3, is_expanded: false },
        ];

        state.scroll_down();
        assert_eq!(state.shelf_selection, 1, "AI Agent: scroll_down increments selection");

        state.scroll_down();
        assert_eq!(state.shelf_selection, 2, "AI Agent: scroll_down increments again");

        // At max, scroll_down clamps
        state.scroll_down();
        assert_eq!(state.shelf_selection, 2, "AI Agent: scroll_down at max stays at max");

        state.scroll_up();
        assert_eq!(state.shelf_selection, 1, "AI Agent: scroll_up decrements selection");
    }

    // AI Agent verifies: scroll in Ask mode adjusts reader_scroll
    #[test]
    fn test_library_state_scroll_ask() {
        let mut state = LibraryState::default();
        state.content_mode = ContentMode::Ask;
        state.reader_scroll = 10;

        state.scroll_up();
        assert_eq!(state.reader_scroll, 7, "AI Agent: Ask scroll_up subtracts 3");

        state.scroll_up();
        assert_eq!(state.reader_scroll, 4, "AI Agent: Ask scroll_up subtracts 3 again");

        // Saturating: scroll_up at 0 stays at 0
        state.reader_scroll = 0;
        state.scroll_up();
        assert_eq!(state.reader_scroll, 0, "AI Agent: Ask scroll_up at 0 saturates");

        state.scroll_down();
        assert_eq!(state.reader_scroll, 3, "AI Agent: Ask scroll_down adds 3");

        state.scroll_down();
        assert_eq!(state.reader_scroll, 6, "AI Agent: Ask scroll_down adds 3 again");
    }

    // AI Agent verifies: ShelfItem variants can be constructed and are Debug
    #[test]
    fn test_shelf_item_construction() {
        let shelf_item = ShelfItem::Shelf {
            depth: 1,
            name: "Backend".into(),
            full_path: vec!["Engineering".into(), "Backend".into()],
            entry_count: 5,
            is_expanded: false,
        };
        let entry_item = ShelfItem::Entry {
            depth: 2,
            entry: LibraryEntryBrief {
                id: "e1".into(),
                title: "Test".into(),
                entry_type: "knowledge".into(),
                quality_score: 0.9,
                verified: true,
                usage_count: 3,
                shelf_path: vec!["Engineering".into(), "Backend".into()],
                updated_at: "2024-01-01".into(),
            },
        };

        // AI Agent: verify Debug impl works (no panic)
        let _shelf_debug = format!("{:?}", shelf_item);
        let _entry_debug = format!("{:?}", entry_item);

        // AI Agent: verify Clone impl works
        let _shelf_clone = shelf_item.clone();
        let _entry_clone = entry_item.clone();
    }

    // AI Agent verifies: ContentMode default is Browse
    #[test]
    fn test_content_mode_default() {
        assert_eq!(ContentMode::default(), ContentMode::Browse,
            "AI Agent: ContentMode default must be Browse");
    }

    // AI Agent verifies: Ingest step transitions are well-defined
    #[test]
    fn test_ingest_step_variants() {
        assert_eq!(IngestStep::Input, IngestStep::Input);
        assert_ne!(IngestStep::Input, IngestStep::Analyzing);
        assert_ne!(IngestStep::Analyzing, IngestStep::Confirm);
        assert_ne!(IngestStep::Confirm, IngestStep::Done);
    }
}
