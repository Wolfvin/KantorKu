"""Layers package — Conductor, BriefingRoom, WorkerHub, Intake, GroupChannel, ExecutionChannel, TodoReviewPhase, SessionTranscript, O8-O25 enrichment modules."""

from kantorku.layers.conductor import Conductor, Contract, ContractState, TodoItem
from kantorku.layers.briefing_room import BriefingRoom, BriefingResult
from kantorku.layers.worker_hub import WorkerHub
from kantorku.layers.intake import Intake, IntakeResult
from kantorku.layers.group_channel import GroupChannel, GroupMessage, MessageType, DiscussionRound
from kantorku.layers.execution_channel import ExecutionChannel, PermissionResult
from kantorku.layers.todo_review import TodoReviewPhase, TodoReview, TodoReviewResult
from kantorku.layers.session_transcript import SessionTranscript, TranscriptEntry

# O8-O25: Enrichment modules
from kantorku.layers.ceo_mode import CEOOrchestrationMode, FailureType, RecoveryStrategy
from kantorku.layers.think_gate import OfficeThinkGate, ThinkAction, ThinkResult
from kantorku.layers.smart_plan import SmartPlan, PlanPhase, PlanSchema
from kantorku.layers.worker_evolve import WorkerEvolveEngine, WorkerHealth, EvolveSignal, EvolveAction, EvolveActionType
from kantorku.layers.token_budget import TokenBudgetManager, BudgetMode, BudgetAllocation
from kantorku.layers.senior_call import SeniorCall, ReviewVerdict, ReviewResult, ReviewIssue
from kantorku.layers.dead_code_detector import DeadCodeDetector, DeadCodeIssue, IssueType, DeadCodeVerdict
from kantorku.layers.blocker_resolver import BlockerResolver, BlockerType, ResolutionStrategy, Blocker, Resolution
from kantorku.layers.enhanced_checkpoint import EnhancedCheckpoint, CheckpointData
from kantorku.layers.review_anti_ribet import ReviewAntiRibet, ApproachScore
from kantorku.layers.halt_conditions import HaltMonitor, HaltStatus, HaltConfig, SessionCounters
from kantorku.layers.opinionated_defaults import OpinionatedDefaults, Recommendation
from kantorku.layers.context_alignment import ContextAlignmentGate, AlignmentResult
from kantorku.layers.self_healing import OfficeDoctor, HealthIssue, HealthReport
from kantorku.layers.task_router import TaskSkillRouter, RoutingResult
from kantorku.layers.mcp_integration import MCPManager, MCPServer
from kantorku.layers.debug_loop import StructuredDebugLoop, DebugPhase, DebugEvidence, DebugResult
from kantorku.layers.contract_flow import ContractFlowManager, ContractPhase, PhaseTransition

__all__ = [
    "Conductor",
    "Contract",
    "ContractState",
    "TodoItem",
    "BriefingRoom",
    "BriefingResult",
    "WorkerHub",
    "Intake",
    "IntakeResult",
    # P4
    "GroupChannel",
    "GroupMessage",
    "MessageType",
    "DiscussionRound",
    "ExecutionChannel",
    "PermissionResult",
    "TodoReviewPhase",
    "TodoReview",
    "TodoReviewResult",
    "SessionTranscript",
    "TranscriptEntry",
    # O8-O25: Enrichment modules
    "CEOOrchestrationMode",
    "FailureType",
    "RecoveryStrategy",
    "OfficeThinkGate",
    "ThinkAction",
    "ThinkResult",
    "SmartPlan",
    "PlanPhase",
    "PlanSchema",
    "WorkerEvolveEngine",
    "WorkerHealth",
    "EvolveSignal",
    "EvolveAction",
    "EvolveActionType",
    "TokenBudgetManager",
    "BudgetMode",
    "BudgetAllocation",
    "SeniorCall",
    "ReviewVerdict",
    "ReviewResult",
    "ReviewIssue",
    "DeadCodeDetector",
    "DeadCodeIssue",
    "IssueType",
    "DeadCodeVerdict",
    "BlockerResolver",
    "BlockerType",
    "ResolutionStrategy",
    "Blocker",
    "Resolution",
    "EnhancedCheckpoint",
    "CheckpointData",
    "ReviewAntiRibet",
    "ApproachScore",
    "HaltMonitor",
    "HaltStatus",
    "HaltConfig",
    "SessionCounters",
    "OpinionatedDefaults",
    "Recommendation",
    "ContextAlignmentGate",
    "AlignmentResult",
    "OfficeDoctor",
    "HealthIssue",
    "HealthReport",
    "TaskSkillRouter",
    "RoutingResult",
    "MCPManager",
    "MCPServer",
    "StructuredDebugLoop",
    "DebugPhase",
    "DebugEvidence",
    "DebugResult",
    "ContractFlowManager",
    "ContractPhase",
    "PhaseTransition",
]
