// ── Contract State Machine ─────────────────────────────────────────
export type ContractState =
  | 'idle'
  | 'manager_thinking'
  | 'team_consult'
  | 'clarifying'
  | 'contract_presented'
  | 'team_review'
  | 'todo_review'
  | 'client_feedback'
  | 'working'
  | 'done'
  | 'failed';

// ── Contract & Todo ────────────────────────────────────────────────
export interface TodoItem {
  id: string;
  description: string;
  assigned_to: string;
  status: 'pending' | 'in_progress' | 'done' | 'failed' | 'blocked';
  depends_on: string[];
  priority?: 'low' | 'medium' | 'high' | 'critical';
  estimated_time_ms?: number;
  actual_time_ms?: number;
  result?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface Contract {
  id: string;
  session_id: string;
  title: string;
  description: string;
  todos: TodoItem[];
  state: ContractState;
  client_messages: Array<{ role: string; content: string }>;
  manager_messages: Array<{ role: string; content: string }>;
  team_feedback_rounds: TeamFeedbackRound[];
  team_approved: boolean;
  approval_gates: ApprovalGate[];
  deadline?: string;
  budget_limit?: number;
  created_at: string;
  updated_at: string;
}

// ── GroupChannel Message Types ─────────────────────────────────────
export type MessageType =
  | 'speak'
  | 'concern'
  | 'suggestion'
  | 'question'
  | 'response'
  | 'agreement'
  | 'disagreement'
  | 'info'
  | 'manager_summary'
  | 'manager_decision'
  | 'volunteer'
  | 'escalation'
  | 'overhearing'
  | 'delegation_request'
  | 'delegation_response'
  | 'brainstorm'
  | 'context_switch';

export interface GroupMessage {
  id: string;
  session_id: string;
  from_id: string;
  message_type: MessageType;
  content: string;
  reply_to: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface DiscussionRound {
  round_number: number;
  messages: GroupMessage[];
  summary: string;
  decisions: string[];
  consensus_reached: boolean;
}

// ── Office Events ──────────────────────────────────────────────────
export interface OfficeEvent {
  type: string;
  from_id?: string;
  to_id?: string;
  content?: string;
  session_id?: string;
  model?: string;
  files?: string[];
  error?: string;
  todos?: TodoItem[];
  issues?: string[];
  approved?: boolean;
  reason?: string;
  worker?: string;
  lesson?: string;
  chunk?: string;
  full_text?: string;
  trace_id?: string;
  span_id?: string;
  duration_ms?: number;
  timestamp?: string;
  [key: string]: unknown;
}

// ── Worker Identity ────────────────────────────────────────────────
export interface WorkerIdentity {
  id: string;
  model: string;
  squad: string;
  role: string;
  skill_md: string;
  personality?: string;
  emoji?: string;
  color?: string;
  status?: 'idle' | 'busy' | 'error' | 'offline';
  current_task?: string;
  capabilities?: string[];
  trust_score?: number;
  total_tasks?: number;
  success_rate?: number;
  avg_latency_ms?: number;
  hired_at?: string;
  is_custom?: boolean;
}

// ── Intake ─────────────────────────────────────────────────────────
export interface IntakeResult {
  original_message: string;
  type: 'new_request' | 'follow_up' | 'revision' | 'question' | 'feedback';
  urgency: 'low' | 'medium' | 'high' | 'critical';
  domain: string[];
  technologies: string[];
  summary: string;
  key_requirements: string[];
  estimated_complexity: 'simple' | 'moderate' | 'complex' | 'very_complex';
  estimated_workers?: string[];
  estimated_duration_ms?: number;
}

// ── Cost & Metrics ─────────────────────────────────────────────────
export interface CostEntry {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  timestamp: string;
  worker_id?: string;
  session_id?: string;
  trace_id?: string;
}

export interface CostReport {
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  entries: CostEntry[];
  by_model: Record<string, { cost: number; calls: number; tokens: number }>;
  by_worker: Record<string, { cost: number; calls: number; tokens: number }>;
  budget_remaining?: number;
}

export interface HealthStatus {
  is_healthy: boolean;
  message: string;
  providers?: Record<string, { status: string; latency_ms: number; error_rate: number }>;
  workers?: Record<string, { status: string; current_task?: string; latency_ms?: number }>;
  uptime_ms?: number;
  last_check?: string;
}

export interface CircuitBreakerState {
  provider: string;
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  last_failure?: string;
  last_success?: string;
  recovery_timeout_ms?: number;
}

export interface MetricsSummary {
  total_calls: number;
  total_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
  success_rate: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  by_model: Record<string, unknown>;
  time_series?: MetricDataPoint[];
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

// ── Interactive Question (AI asks user with options) ──────────────
export interface QuestionOption {
  label: string;  // 'A', 'B', 'C', etc.
  text: string;   // 'React', 'Vue', etc.
}

export interface InteractiveQuestion {
  id: string;
  question: string;
  options: QuestionOption[];
  allow_other: boolean;  // Always true — user can type custom answer
  answered?: boolean;    // Marked true once user selects an option
  selected_option?: string;  // The label the user selected (e.g., 'A')
  custom_answer?: string;    // If user chose "Other" and typed a response
}

// ── Chat Messages ──────────────────────────────────────────────────
export interface ClientChatMessage {
  id: string;
  role: 'user' | 'manager';
  content: string;
  timestamp: string;
  source?: string;
  session_id?: string;
  question?: InteractiveQuestion;  // Present when manager asks with options
}

export interface WorkersChatMessage {
  id: string;
  from_id: string;
  message_type: MessageType;
  content: string;
  timestamp: string;
  reply_to?: string;
  session_id?: string;
}

// ── Briefing ───────────────────────────────────────────────────────
export interface BriefingResult {
  plan: Record<string, unknown>;
  rounds_completed: number;
  consensus_reached: boolean;
  concerns: Array<Record<string, unknown>>;
  decisions: string[];
  volunteer_assignments?: Record<string, string>;
  estimated_total_time_ms?: number;
}

// ── Session ────────────────────────────────────────────────────────
export interface Session {
  session_id: string;
  state: ContractState;
  contract_title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  total_cost: number;
}

// ── Memory Ring ────────────────────────────────────────────────────
export interface MemoryRing {
  ring: number;
  label: string;
  description: string;
  size: number;
  color: string;
  engine: string;
}

export interface MemoryEntry {
  id: string;
  ring: number;
  key: string;
  value: string;
  timestamp: string;
  session_id?: string;
  tags?: string[];
  access_count?: number;
}

// ── DAG (Task Dependencies) ────────────────────────────────────────
export interface DAGNode {
  id: string;
  label: string;
  status: 'pending' | 'in_progress' | 'done' | 'failed' | 'blocked';
  assigned_to: string;
  depth: number;
}

export interface DAGEdge {
  from: string;
  to: string;
  type: 'depends_on' | 'delegates_to' | 'verifies';
}

// ── Middleware Pipeline ────────────────────────────────────────────
export interface MiddlewareStep {
  name: string;
  type: 'auth' | 'logging' | 'rate_limit' | 'cost_guard' | 'cache' | 'retry' | 'circuit_breaker' | 'validation';
  status: 'passed' | 'blocked' | 'skipped' | 'error';
  duration_ms: number;
  detail?: string;
}

// ── Observability / Tracing ────────────────────────────────────────
export interface TraceEntry {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  operation: string;
  worker_id?: string;
  model?: string;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  status: 'ok' | 'error' | 'timeout';
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;
  metadata?: Record<string, unknown>;
}

export interface Span {
  id: string;
  name: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  status: 'ok' | 'error' | 'running';
  children?: Span[];
  attributes?: Record<string, string>;
}

// ── Approval Gates ─────────────────────────────────────────────────
export interface ApprovalGate {
  id: string;
  gate_type: 'team_review' | 'client_approval' | 'budget_check' | 'security_review';
  status: 'pending' | 'approved' | 'rejected' | 'skipped';
  approver: string;
  reason?: string;
  timestamp?: string;
}

// ── Delegation ─────────────────────────────────────────────────────
export interface DelegationRequest {
  id: string;
  from_worker: string;
  to_worker: string;
  task_description: string;
  reason: string;
  status: 'pending' | 'accepted' | 'rejected';
  timestamp: string;
}

// ── Escalation ─────────────────────────────────────────────────────
export interface EscalationEvent {
  id: string;
  from_worker: string;
  reason: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: string;
  resolved: boolean;
}

// ── Emotion & Trust ────────────────────────────────────────────────
export interface WorkerEmotion {
  worker_id: string;
  emotion: 'confident' | 'uncertain' | 'frustrated' | 'excited' | 'neutral';
  confidence: number;
  timestamp: string;
}

export interface TrustScore {
  worker_id: string;
  score: number;
  trend: 'improving' | 'stable' | 'declining';
  history: Array<{ timestamp: string; score: number }>;
}

// ── Bulletin Board / SOP ───────────────────────────────────────────
export interface BulletinBoardEntry {
  id: string;
  type: 'announcement' | 'sop' | 'rule' | 'alert';
  title: string;
  content: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  active: boolean;
}

// ── Debrief ────────────────────────────────────────────────────────
export interface DebriefResult {
  contract_id: string;
  session_id: string;
  what_went_well: string[];
  what_could_improve: string[];
  lessons_learned: string[];
  worker_feedback: Record<string, string>;
  total_duration_ms: number;
  total_cost: number;
  timestamp: string;
}

// ── Team Feedback ──────────────────────────────────────────────────
export interface TeamFeedbackRound {
  round_number: number;
  worker_id: string;
  feedback_type: 'concern' | 'suggestion' | 'agreement' | 'disagreement';
  content: string;
  timestamp: string;
}

// ── Review & Revision ──────────────────────────────────────────────
export interface ReviewRevision {
  id: string;
  contract_id: string;
  reviewer: string;
  review_type: 'code' | 'design' | 'security' | 'quality';
  status: 'pending' | 'approved' | 'changes_requested';
  comments: string[];
  timestamp: string;
}

// ── Time Travel Snapshot ───────────────────────────────────────────
export interface TimeTravelSnapshot {
  id: string;
  contract_id: string;
  state: ContractState;
  timestamp: string;
  description: string;
  data: Record<string, unknown>;
}

// ── API Response Types ─────────────────────────────────────────────
export interface ChatApiResponse {
  type: 'manager_message' | 'contract_ready' | 'team_feedback' | 'team_consult' | 'question';
  content?: string;
  contract?: Contract;
  intake?: IntakeResult;
  team_feedback?: TeamFeedbackRound[];
  question?: InteractiveQuestion;
}

export interface ExecuteApiResponse {
  session_id: string;
  events: OfficeEvent[];
  results: Record<string, unknown>;
  trace_id?: string;
  cost?: CostReport;
  debrief?: DebriefResult;
  trust_updates?: Array<{ worker_id: string; score: number; trend: 'improving' | 'stable' | 'declining' }>;
  emotions?: Array<{ worker_id: string; emotion: string; confidence: number; timestamp: string }>;
}

export interface BriefingApiResponse {
  rounds: DiscussionRound[];
  consensus_reached: boolean;
  decisions: string[];
  volunteer_assignments: Record<string, string>;
}

// ── Context Switch / Impromptu ─────────────────────────────────────
export interface ContextSwitchEvent {
  id: string;
  from_task: string;
  to_task: string;
  reason: string;
  timestamp: string;
  worker_id: string;
}

export interface ImpromptuTask {
  id: string;
  description: string;
  requested_by: string;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'accepted' | 'declined';
  volunteer?: string;
  timestamp: string;
}

// ── Aggregated Health ──────────────────────────────────────────────
export interface AggregatedHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Record<string, {
    status: 'pass' | 'warn' | 'fail';
    message?: string;
    latency_ms?: number;
    timestamp: string;
  }>;
  uptime_ms?: number;
  version?: string;
}

// ── Health Dashboard ──────────────────────────────────────────────
export interface HealthDashboard {
  overall: 'healthy' | 'degraded' | 'unhealthy';
  providers: Record<string, {
    status: 'available' | 'degraded' | 'unavailable';
    latency_ms: number;
    error_rate: number;
    last_check: string;
    circuit_breaker?: CircuitBreakerState;
  }>;
  workers: Record<string, {
    status: 'idle' | 'busy' | 'error' | 'offline';
    current_task?: string;
    latency_ms?: number;
    tasks_completed?: number;
    error_count?: number;
  }>;
  system: {
    uptime_ms: number;
    total_requests: number;
    active_sessions: number;
    memory_usage_mb?: number;
  };
  alerts: Array<{
    id: string;
    severity: 'info' | 'warning' | 'critical';
    message: string;
    timestamp: string;
    resolved: boolean;
  }>;
}

// ── Office Status ─────────────────────────────────────────────────
export interface OfficeStatus {
  status: 'running' | 'idle' | 'error';
  active_sessions: number;
  total_workers: number;
  busy_workers: number;
  uptime_ms: number;
  version: string;
  provider_status: Record<string, 'available' | 'degraded' | 'unavailable'>;
  memory_rings: {
    ring1_entries: number;
    ring2_entries: number;
    ring3_entries: number;
  };
  task_queue: {
    pending: number;
    in_progress: number;
    completed: number;
    failed: number;
  };
}

// ── Circuit Breaker Status (Extended) ─────────────────────────────
export interface CircuitBreakerStatus {
  provider: string;
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  success_count: number;
  last_failure?: string;
  last_success?: string;
  recovery_timeout_ms: number;
  half_open_max_calls: number;
  state_changed_at: string;
}

// ── Session Snapshot ──────────────────────────────────────────────
export interface SessionSnapshot {
  session_id: string;
  state: ContractState;
  contract: Contract | null;
  messages: ClientChatMessage[];
  worker_messages: WorkersChatMessage[];
  intake: IntakeResult | null;
  briefing: BriefingResult | null;
  debrief: DebriefResult | null;
  cost: CostReport | null;
  traces: TraceEntry[];
  created_at: string;
  updated_at: string;
  duration_ms?: number;
}

// ── Cache Entry ───────────────────────────────────────────────────
export interface CacheEntry {
  key: string;
  value: string;
  ttl_ms: number;
  created_at: string;
  accessed_at: string;
  hit_count: number;
  provider?: string;
  model?: string;
}

// ── Worker API Key Configuration ──────────────────────────────────
export interface WorkerApiKeyConfig {
  worker_id: string;
  provider: string;
  model: string;
  api_key: string;
  base_url?: string;
  is_custom?: boolean;
}

// ── Undo/Redo Action ──────────────────────────────────────────────
export interface UndoableAction {
  id: string;
  type: 'contract_update' | 'todo_status' | 'gate_update' | 'delegation' | 'worker_hire' | 'worker_fire';
  description: string;
  timestamp: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}
