// ── Contract State Machine ─────────────────────────────────────────
export type ContractState =
  | 'idle'
  | 'manager_thinking'
  | 'clarifying'
  | 'contract_presented'
  | 'team_review'
  | 'todo_review'
  | 'client_feedback'
  | 'working'
  | 'done';

// ── Contract & Todo ────────────────────────────────────────────────
export interface TodoItem {
  id: string;
  description: string;
  assigned_to: string;
  status: 'pending' | 'in_progress' | 'done' | 'failed';
  depends_on: string[];
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
  team_feedback_rounds: Array<Record<string, unknown>>;
  team_approved: boolean;
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
  | 'manager_decision';

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
}

// ── Cost & Metrics ─────────────────────────────────────────────────
export interface CostEntry {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  timestamp: string;
}

export interface CostReport {
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  entries: CostEntry[];
  by_model: Record<string, { cost: number; calls: number; tokens: number }>;
}

export interface HealthStatus {
  is_healthy: boolean;
  message: string;
  providers?: Record<string, { status: string; latency_ms: number }>;
  workers?: Record<string, { status: string; current_task?: string }>;
}

export interface CircuitBreakerState {
  provider: string;
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  last_failure?: string;
}

export interface MetricsSummary {
  total_calls: number;
  total_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
  success_rate: number;
  by_model: Record<string, unknown>;
}

// ── Chat Messages ──────────────────────────────────────────────────
export interface ClientChatMessage {
  id: string;
  role: 'user' | 'manager';
  content: string;
  timestamp: string;
  source?: string;
}

export interface WorkersChatMessage {
  id: string;
  from_id: string;
  message_type: MessageType;
  content: string;
  timestamp: string;
  reply_to?: string;
}

// ── Briefing ───────────────────────────────────────────────────────
export interface BriefingResult {
  plan: Record<string, unknown>;
  rounds_completed: number;
  consensus_reached: boolean;
  concerns: Array<Record<string, unknown>>;
  decisions: string[];
}

// ── Session ────────────────────────────────────────────────────────
export interface Session {
  session_id: string;
  state: ContractState;
  contract_title: string;
}

// ── Memory Ring ────────────────────────────────────────────────────
export interface MemoryRing {
  ring: number;
  label: string;
  description: string;
  size: number;
  color: string;
}

// ── API Response Types ─────────────────────────────────────────────
export interface ChatApiResponse {
  type: 'manager_message' | 'contract_ready';
  content?: string;
  contract?: Contract;
  intake?: IntakeResult;
}

export interface ExecuteApiResponse {
  session_id: string;
  events: OfficeEvent[];
  results: Record<string, unknown>;
}
