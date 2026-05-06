use serde::{Deserialize, Serialize};

/// DAG (Directed Acyclic Graph) node — represents a task in the dependency tree
#[derive(Debug, Clone, Deserialize, Serialize)]
#[allow(dead_code)] // Fields used for serde deserialization
pub struct DagNode {
    pub title: String,
    pub worker_id: String,
    pub task_id: Option<String>,
    pub status: String,
    pub children: Vec<DagNode>,
}

impl DagNode {
    /// Find a node by task_id (recursive search)
    pub fn find_by_task(&self, task_id: &str) -> Option<&DagNode> {
        if self.task_id.as_deref() == Some(task_id) {
            return Some(self);
        }
        for child in &self.children {
            if let Some(found) = child.find_by_task(task_id) {
                return Some(found);
            }
        }
        None
    }

    /// Find a mutable node by task_id (recursive search)
    pub fn find_by_task_mut(&mut self, task_id: &str) -> Option<&mut DagNode> {
        if self.task_id.as_deref() == Some(task_id) {
            return Some(self);
        }
        for child in &mut self.children {
            if let Some(found) = child.find_by_task_mut(task_id) {
                return Some(found);
            }
        }
        None
    }
}

/// Worker event — tracks all events related to workers in the system
#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct WorkerEvent {
    pub worker_id: String,
    pub event_type: String,
    pub content: String,
    pub task_id: Option<String>,
    pub timestamp: String,
}

/// Log event — filtered view of worker events for the Events panel
#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct LogEvent {
    pub event_type: String,
    pub content: String,
    pub timestamp: String,
    pub severity: String,
}

/// Chat message — used in Manager Chat panel
#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    pub timestamp: String,
}

/// Briefing message — used in Briefing panel
#[derive(Debug, Clone)]
#[allow(dead_code)] // Used by render methods
pub struct BriefingMessage {
    pub speaker: String,
    pub content: String,
    pub timestamp: String,
}

/// Workers tab — which sub-panel is shown in the Workers Live panel
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[derive(Default)]
pub enum WorkersTab {
    #[default]
    Workers,
    Briefing,
    Dag,
    Events,
}
