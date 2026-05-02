import { create } from 'zustand';
import {
  ContractState,
  Contract,
  TodoItem,
  ClientChatMessage,
  WorkersChatMessage,
  WorkerIdentity,
  OfficeEvent,
  BriefingResult,
  IntakeResult,
  CostReport,
  HealthStatus,
  CircuitBreakerState,
  MetricsSummary,
  Session,
  MemoryEntry,
  DAGNode,
  DAGEdge,
  MiddlewareStep,
  TraceEntry,
  ApprovalGate,
  DelegationRequest,
  EscalationEvent,
  WorkerEmotion,
  TrustScore,
  BulletinBoardEntry,
  DebriefResult,
  TeamFeedbackRound,
  ReviewRevision,
  TimeTravelSnapshot,
  ContextSwitchEvent,
  ImpromptuTask,
} from './types';
import { WORKERS } from './workers-data';

// ── Persistence Helpers ────────────────────────────────────────────
const STORAGE_KEY = 'kantorku_state';

function loadFromStorage<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : fallback;
  } catch {
    return fallback;
  }
}

function saveToStorage(key: string, data: unknown) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch {
    // Storage full or unavailable
  }
}

// Debounced save
let saveTimer: ReturnType<typeof setTimeout> | null = null;
function debouncedSave(state: Partial<KantorkuStore>) {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveToStorage(STORAGE_KEY, {
      clientMessages: state.clientMessages,
      workersMessages: state.workersMessages,
      sessions: state.sessions,
      activeSessionId: state.activeSessionId,
      costReport: state.costReport,
      workers: state.workers,
      memoryEntries: state.memoryEntries,
      bulletinBoard: state.bulletinBoard,
      trustScores: state.trustScores,
      apiKey: state.apiKey,
      timelineSnapshots: state.timelineSnapshots,
      panelLayout: state.panelLayout,
    });
  }, 300);
}

interface KantorkuStore {
  // ── Active Zone ───────────────────────────────────────────────
  activeZone: 'lobby' | 'workspace' | 'dashboard';
  setActiveZone: (zone: 'lobby' | 'workspace' | 'dashboard') => void;

  // ── Sessions ──────────────────────────────────────────────────
  sessions: Session[];
  activeSessionId: string;
  setActiveSession: (id: string) => void;
  addSession: (session: Session) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;

  // ── Contract State Machine ────────────────────────────────────
  contract: Contract | null;
  contractState: ContractState;
  setContract: (contract: Contract | null) => void;
  setContractState: (state: ContractState) => void;
  updateTodoStatus: (todoId: string, status: TodoItem['status'], result?: string, error?: string) => void;
  updateTodoActualTime: (todoId: string, timeMs: number) => void;

  // ── Client Chat (Panel 1) ────────────────────────────────────
  clientMessages: ClientChatMessage[];
  addClientMessage: (msg: ClientChatMessage) => void;
  clearClientMessages: () => void;
  searchClientMessages: (query: string) => ClientChatMessage[];
  answerQuestion: (messageId: string, selectedOption: string, customAnswer?: string) => void;

  // ── Workers Chat (GroupChannel) ──────────────────────────────
  workersMessages: WorkersChatMessage[];
  addWorkersMessage: (msg: WorkersChatMessage) => void;
  clearWorkersMessages: () => void;

  // ── Workers ───────────────────────────────────────────────────
  workers: WorkerIdentity[];
  updateWorkerStatus: (id: string, status: string, task?: string) => void;
  hireWorker: (worker: WorkerIdentity) => void;
  fireWorker: (id: string) => void;
  updateWorkerStats: (id: string, stats: Partial<WorkerIdentity>) => void;

  // ── Office Events Stream ─────────────────────────────────────
  officeEvents: OfficeEvent[];
  addOfficeEvent: (event: OfficeEvent) => void;
  clearOfficeEvents: () => void;

  // ── Briefing ──────────────────────────────────────────────────
  briefingResult: BriefingResult | null;
  setBriefingResult: (result: BriefingResult | null) => void;
  discussionRounds: Array<{
    round_number: number;
    messages: WorkersChatMessage[];
    summary: string;
    decisions: string[];
    consensus_reached: boolean;
  }>;
  addDiscussionRound: (round: { round_number: number; messages: WorkersChatMessage[]; summary: string; decisions: string[]; consensus_reached: boolean }) => void;

  // ── Intake ────────────────────────────────────────────────────
  intakeResult: IntakeResult | null;
  setIntakeResult: (result: IntakeResult | null) => void;

  // ── Cost & Metrics (Dashboard) ───────────────────────────────
  costReport: CostReport | null;
  setCostReport: (report: CostReport) => void;
  addCostEntry: (model: string, inputTokens: number, outputTokens: number, costUsd: number, workerId?: string, traceId?: string) => void;
  metricsSummary: MetricsSummary | null;
  setMetricsSummary: (summary: MetricsSummary) => void;
  healthStatus: HealthStatus | null;
  setHealthStatus: (status: HealthStatus) => void;
  circuitBreakers: CircuitBreakerState[];
  setCircuitBreakers: (breakers: CircuitBreakerState[]) => void;
  latencyHistory: Array<{ timestamp: string; latency_ms: number; worker_id?: string }>;
  addLatencyEntry: (latency_ms: number, worker_id?: string) => void;

  // ── Memory ────────────────────────────────────────────────────
  memoryEntries: MemoryEntry[];
  addMemoryEntry: (entry: MemoryEntry) => void;
  clearMemoryRing: (ring: number) => void;
  queryMemory: (ring: number, query?: string) => MemoryEntry[];

  // ── DAG ───────────────────────────────────────────────────────
  dagNodes: DAGNode[];
  dagEdges: DAGEdge[];
  setDAG: (nodes: DAGNode[], edges: DAGEdge[]) => void;
  updateDAGNode: (id: string, status: DAGNode['status']) => void;

  // ── Middleware Pipeline ───────────────────────────────────────
  middlewareSteps: MiddlewareStep[];
  setMiddlewareSteps: (steps: MiddlewareStep[]) => void;

  // ── Traces / Observability ────────────────────────────────────
  traces: TraceEntry[];
  addTrace: (trace: TraceEntry) => void;
  activeTraceId: string | null;
  setActiveTraceId: (id: string | null) => void;

  // ── Approval Gates ────────────────────────────────────────────
  approvalGates: ApprovalGate[];
  setApprovalGates: (gates: ApprovalGate[]) => void;
  updateApprovalGate: (id: string, status: ApprovalGate['status'], reason?: string) => void;

  // ── Delegation ────────────────────────────────────────────────
  delegations: DelegationRequest[];
  addDelegation: (delegation: DelegationRequest) => void;
  updateDelegation: (id: string, status: DelegationRequest['status']) => void;

  // ── Escalation ────────────────────────────────────────────────
  escalations: EscalationEvent[];
  addEscalation: (escalation: EscalationEvent) => void;
  resolveEscalation: (id: string) => void;

  // ── Emotion & Trust ───────────────────────────────────────────
  workerEmotions: WorkerEmotion[];
  setWorkerEmotion: (emotion: WorkerEmotion) => void;
  trustScores: TrustScore[];
  updateTrustScore: (workerId: string, score: number) => void;

  // ── Bulletin Board / SOP ──────────────────────────────────────
  bulletinBoard: BulletinBoardEntry[];
  addBulletinEntry: (entry: BulletinBoardEntry) => void;
  deactivateBulletin: (id: string) => void;

  // ── Debrief ───────────────────────────────────────────────────
  debriefResult: DebriefResult | null;
  setDebriefResult: (result: DebriefResult | null) => void;

  // ── Team Feedback ─────────────────────────────────────────────
  teamFeedback: TeamFeedbackRound[];
  addTeamFeedback: (feedback: TeamFeedbackRound) => void;

  // ── Review & Revision ─────────────────────────────────────────
  reviews: ReviewRevision[];
  addReview: (review: ReviewRevision) => void;
  updateReview: (id: string, status: ReviewRevision['status'], comments?: string[]) => void;

  // ── Time Travel ───────────────────────────────────────────────
  timelineSnapshots: TimeTravelSnapshot[];
  addSnapshot: (snapshot: TimeTravelSnapshot) => void;

  // ── Context Switch / Impromptu ────────────────────────────────
  contextSwitches: ContextSwitchEvent[];
  addContextSwitch: (event: ContextSwitchEvent) => void;
  impromptuTasks: ImpromptuTask[];
  addImpromptuTask: (task: ImpromptuTask) => void;
  updateImpromptuTask: (id: string, volunteer: string, status: ImpromptuTask['status']) => void;

  // ── API Key ───────────────────────────────────────────────────
  apiKey: string;
  setApiKey: (key: string) => void;

  // ── Loading States ────────────────────────────────────────────
  isManagerThinking: boolean;
  setManagerThinking: (thinking: boolean) => void;
  isWorking: boolean;
  setWorking: (working: boolean) => void;

  // ── Backend Connection ────────────────────────────────────────
  isBackendConnected: boolean;
  setBackendConnected: (connected: boolean) => void;

  // ── Settings Dialog ───────────────────────────────────────────
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;

  // ── SSE Connection ────────────────────────────────────────────
  sseConnected: boolean;
  setSseConnected: (connected: boolean) => void;

  // ── Panel Layout ──────────────────────────────────────────────
  panelLayout: { lobby: number; workspace: number; dashboard: number };
  setPanelLayout: (layout: { lobby: number; workspace: number; dashboard: number }) => void;

  // ── Reset ─────────────────────────────────────────────────────
  resetAll: () => void;
}

const initialState = {
  activeZone: 'lobby' as const,
  sessions: [] as Session[],
  activeSessionId: '',
  contract: null as Contract | null,
  contractState: 'idle' as ContractState,
  clientMessages: [] as ClientChatMessage[],
  workersMessages: [] as WorkersChatMessage[],
  workers: WORKERS,
  officeEvents: [] as OfficeEvent[],
  briefingResult: null as BriefingResult | null,
  discussionRounds: [] as KantorkuStore['discussionRounds'],
  intakeResult: null as IntakeResult | null,
  costReport: null as CostReport | null,
  metricsSummary: null as MetricsSummary | null,
  healthStatus: null as HealthStatus | null,
  circuitBreakers: [] as CircuitBreakerState[],
  latencyHistory: [] as Array<{ timestamp: string; latency_ms: number; worker_id?: string }>,
  memoryEntries: [] as MemoryEntry[],
  dagNodes: [] as DAGNode[],
  dagEdges: [] as DAGEdge[],
  middlewareSteps: [] as MiddlewareStep[],
  traces: [] as TraceEntry[],
  activeTraceId: null as string | null,
  approvalGates: [] as ApprovalGate[],
  delegations: [] as DelegationRequest[],
  escalations: [] as EscalationEvent[],
  workerEmotions: [] as WorkerEmotion[],
  trustScores: [] as TrustScore[],
  bulletinBoard: [] as BulletinBoardEntry[],
  debriefResult: null as DebriefResult | null,
  teamFeedback: [] as TeamFeedbackRound[],
  reviews: [] as ReviewRevision[],
  timelineSnapshots: [] as TimeTravelSnapshot[],
  contextSwitches: [] as ContextSwitchEvent[],
  impromptuTasks: [] as ImpromptuTask[],
  panelLayout: { lobby: 30, workspace: 45, dashboard: 25 },
  apiKey: '',
  isManagerThinking: false,
  isWorking: false,
  isBackendConnected: false,
  settingsOpen: false,
  sseConnected: false,
};

// Load persisted data for specific fields
function getPersistedState() {
  if (typeof window === 'undefined') return {};
  const stored = loadFromStorage<Partial<typeof initialState>>(STORAGE_KEY, {});
  return {
    clientMessages: stored.clientMessages || [],
    workersMessages: stored.workersMessages || [],
    sessions: stored.sessions || [],
    activeSessionId: stored.activeSessionId || '',
    costReport: stored.costReport || null,
    workers: stored.workers || WORKERS,
    memoryEntries: stored.memoryEntries || [],
    bulletinBoard: stored.bulletinBoard || [],
    trustScores: stored.trustScores || [],
    apiKey: stored.apiKey || '',
    timelineSnapshots: stored.timelineSnapshots || [],
    panelLayout: (() => {
      try {
        const pl = localStorage.getItem('kantorku_panel_layout');
        return pl ? JSON.parse(pl) : { lobby: 30, workspace: 45, dashboard: 25 };
      } catch { return { lobby: 30, workspace: 45, dashboard: 25 }; }
    })(),
  };
}

export const useKantorkuStore = create<KantorkuStore>((set, get) => ({
  ...initialState,
  ...getPersistedState(),

  // ── Active Zone ─────────────────────────────────────────────
  setActiveZone: (zone) => set({ activeZone: zone }),

  // ── Sessions ────────────────────────────────────────────────
  setActiveSession: (id) => set({ activeSessionId: id }),
  addSession: (session) =>
    set((state) => {
      const updated = { sessions: [...state.sessions, session] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  updateSession: (id, updates) =>
    set((state) => {
      const updated = {
        sessions: state.sessions.map((s) =>
          s.session_id === id ? { ...s, ...updates } : s
        ),
      };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),

  // ── Contract State Machine ──────────────────────────────────
  setContract: (contract) => {
    set((state) => {
      const newState = { contract };
      if (contract) {
        // Save time travel snapshot
        const snapshot: TimeTravelSnapshot = {
          id: `snap_${Date.now()}`,
          contract_id: contract.id,
          state: contract.state,
          timestamp: new Date().toISOString(),
          description: `Contract ${contract.state}`,
          data: { ...contract },
        };
        return {
          ...newState,
          timelineSnapshots: [...state.timelineSnapshots, snapshot],
        };
      }
      return newState;
    });
  },
  setContractState: (state) => set({ contractState: state }),
  updateTodoStatus: (todoId, status, result, error) =>
    set((state) => {
      if (!state.contract) return state;
      return {
        contract: {
          ...state.contract,
          todos: state.contract.todos.map((t) =>
            t.id === todoId
              ? {
                  ...t,
                  status,
                  result: result || t.result,
                  error: error || t.error,
                  completed_at: status === 'done' ? new Date().toISOString() : t.completed_at,
                  started_at: status === 'in_progress' && !t.started_at ? new Date().toISOString() : t.started_at,
                }
              : t
          ),
        },
      };
    }),
  updateTodoActualTime: (todoId, timeMs) =>
    set((state) => {
      if (!state.contract) return state;
      return {
        contract: {
          ...state.contract,
          todos: state.contract.todos.map((t) =>
            t.id === todoId ? { ...t, actual_time_ms: timeMs } : t
          ),
        },
      };
    }),

  // ── Client Chat ────────────────────────────────────────────
  addClientMessage: (msg) =>
    set((state) => {
      const updated = { clientMessages: [...state.clientMessages, msg] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  clearClientMessages: () => set({ clientMessages: [] }),
  searchClientMessages: (query) => {
    const state = get();
    const q = query.toLowerCase();
    return state.clientMessages.filter(
      (m) => m.content.toLowerCase().includes(q)
    );
  },
  answerQuestion: (messageId, selectedOption, customAnswer) =>
    set((state) => {
      const updated = {
        clientMessages: state.clientMessages.map((m) =>
          m.id === messageId && m.question
            ? {
                ...m,
                question: {
                  ...m.question,
                  answered: true,
                  selected_option: selectedOption,
                  custom_answer: customAnswer,
                },
              }
            : m
        ),
      };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),

  // ── Workers Chat ───────────────────────────────────────────
  addWorkersMessage: (msg) =>
    set((state) => {
      const updated = { workersMessages: [...state.workersMessages, msg] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  clearWorkersMessages: () => set({ workersMessages: [] }),

  // ── Workers ────────────────────────────────────────────────
  updateWorkerStatus: (id, status, task) =>
    set((state) => ({
      workers: state.workers.map((w) =>
        w.id === id
          ? { ...w, status: status as WorkerIdentity['status'], current_task: task }
          : w
      ),
    })),
  hireWorker: (worker) =>
    set((state) => {
      if (state.workers.find((w) => w.id === worker.id)) return state;
      const updated = { workers: [...state.workers, worker] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  fireWorker: (id) =>
    set((state) => {
      const updated = { workers: state.workers.filter((w) => w.id !== id) };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  updateWorkerStats: (id, stats) =>
    set((state) => ({
      workers: state.workers.map((w) =>
        w.id === id ? { ...w, ...stats } : w
      ),
    })),

  // ── Office Events ──────────────────────────────────────────
  addOfficeEvent: (event) =>
    set((state) => ({
      officeEvents: [...state.officeEvents.slice(-199), { ...event, timestamp: event.timestamp || new Date().toISOString() }],
    })),
  clearOfficeEvents: () => set({ officeEvents: [] }),

  // ── Briefing ───────────────────────────────────────────────
  setBriefingResult: (result) => set({ briefingResult: result }),
  addDiscussionRound: (round) =>
    set((state) => ({
      discussionRounds: [...state.discussionRounds, round],
    })),

  // ── Intake ─────────────────────────────────────────────────
  setIntakeResult: (result) => set({ intakeResult: result }),

  // ── Cost & Metrics ─────────────────────────────────────────
  setCostReport: (report) => set({ costReport: report }),
  addCostEntry: (model, inputTokens, outputTokens, costUsd, workerId, traceId) =>
    set((state) => {
      const existing = state.costReport || {
        total_cost: 0,
        total_input_tokens: 0,
        total_output_tokens: 0,
        entries: [],
        by_model: {},
        by_worker: {},
      };
      const entry = {
        model,
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        cost_usd: costUsd,
        timestamp: new Date().toISOString(),
        worker_id: workerId,
        session_id: state.activeSessionId || undefined,
        trace_id: traceId,
      };
      const byModel = { ...existing.by_model };
      const prev = byModel[model] || { cost: 0, calls: 0, tokens: 0 };
      byModel[model] = {
        cost: prev.cost + costUsd,
        calls: prev.calls + 1,
        tokens: prev.tokens + inputTokens + outputTokens,
      };
      const byWorker = { ...existing.by_worker };
      if (workerId) {
        const prevW = byWorker[workerId] || { cost: 0, calls: 0, tokens: 0 };
        byWorker[workerId] = {
          cost: prevW.cost + costUsd,
          calls: prevW.calls + 1,
          tokens: prevW.tokens + inputTokens + outputTokens,
        };
      }
      const updated = {
        costReport: {
          total_cost: existing.total_cost + costUsd,
          total_input_tokens: existing.total_input_tokens + inputTokens,
          total_output_tokens: existing.total_output_tokens + outputTokens,
          entries: [...existing.entries.slice(-99), entry],
          by_model: byModel,
          by_worker: byWorker,
        },
      };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  setMetricsSummary: (summary) => set({ metricsSummary: summary }),
  setHealthStatus: (status) => set({ healthStatus: status }),
  setCircuitBreakers: (breakers) => set({ circuitBreakers: breakers }),
  addLatencyEntry: (latency_ms, worker_id) =>
    set((state) => ({
      latencyHistory: [...state.latencyHistory.slice(-199), { timestamp: new Date().toISOString(), latency_ms, worker_id }],
    })),

  // ── Memory ─────────────────────────────────────────────────
  addMemoryEntry: (entry) =>
    set((state) => {
      const updated = { memoryEntries: [...state.memoryEntries, entry] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  clearMemoryRing: (ring) =>
    set((state) => {
      const updated = { memoryEntries: state.memoryEntries.filter((e) => e.ring !== ring) };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  queryMemory: (ring, query) => {
    const state = get();
    let results = state.memoryEntries.filter((e) => e.ring === ring);
    if (query) {
      const q = query.toLowerCase();
      results = results.filter(
        (e) => e.key.toLowerCase().includes(q) || e.value.toLowerCase().includes(q)
      );
    }
    return results;
  },

  // ── DAG ────────────────────────────────────────────────────
  setDAG: (nodes, edges) => set({ dagNodes: nodes, dagEdges: edges }),
  updateDAGNode: (id, status) =>
    set((state) => ({
      dagNodes: state.dagNodes.map((n) =>
        n.id === id ? { ...n, status } : n
      ),
    })),

  // ── Middleware ──────────────────────────────────────────────
  setMiddlewareSteps: (steps) => set({ middlewareSteps: steps }),

  // ── Traces ─────────────────────────────────────────────────
  addTrace: (trace) =>
    set((state) => ({
      traces: [...state.traces.slice(-199), trace],
    })),
  setActiveTraceId: (id) => set({ activeTraceId: id }),

  // ── Approval Gates ─────────────────────────────────────────
  setApprovalGates: (gates) => set({ approvalGates: gates }),
  updateApprovalGate: (id, status, reason) =>
    set((state) => ({
      approvalGates: state.approvalGates.map((g) =>
        g.id === id ? { ...g, status, reason, timestamp: new Date().toISOString() } : g
      ),
    })),

  // ── Delegation ─────────────────────────────────────────────
  addDelegation: (delegation) =>
    set((state) => ({
      delegations: [...state.delegations, delegation],
    })),
  updateDelegation: (id, status) =>
    set((state) => ({
      delegations: state.delegations.map((d) =>
        d.id === id ? { ...d, status } : d
      ),
    })),

  // ── Escalation ─────────────────────────────────────────────
  addEscalation: (escalation) =>
    set((state) => ({
      escalations: [...state.escalations, escalation],
    })),
  resolveEscalation: (id) =>
    set((state) => ({
      escalations: state.escalations.map((e) =>
        e.id === id ? { ...e, resolved: true } : e
      ),
    })),

  // ── Emotion & Trust ────────────────────────────────────────
  setWorkerEmotion: (emotion) =>
    set((state) => ({
      workerEmotions: [
        ...state.workerEmotions.filter((e) => e.worker_id !== emotion.worker_id).slice(-19),
        emotion,
      ],
    })),
  updateTrustScore: (workerId, score) =>
    set((state) => {
      const existing = state.trustScores.find((t) => t.worker_id === workerId);
      if (existing) {
        return {
          trustScores: state.trustScores.map((t) =>
            t.worker_id === workerId
              ? {
                  ...t,
                  score,
                  trend: score > t.score ? 'improving' : score < t.score ? 'declining' : 'stable',
                  history: [...t.history.slice(-19), { timestamp: new Date().toISOString(), score }],
                }
              : t
          ),
        };
      }
      return {
        trustScores: [
          ...state.trustScores,
          { worker_id: workerId, score, trend: 'stable', history: [{ timestamp: new Date().toISOString(), score }] },
        ],
      };
    }),

  // ── Bulletin Board ─────────────────────────────────────────
  addBulletinEntry: (entry) =>
    set((state) => {
      const updated = { bulletinBoard: [...state.bulletinBoard, entry] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),
  deactivateBulletin: (id) =>
    set((state) => ({
      bulletinBoard: state.bulletinBoard.map((b) =>
        b.id === id ? { ...b, active: false } : b
      ),
    })),

  // ── Debrief ────────────────────────────────────────────────
  setDebriefResult: (result) => set({ debriefResult: result }),

  // ── Team Feedback ──────────────────────────────────────────
  addTeamFeedback: (feedback) =>
    set((state) => ({
      teamFeedback: [...state.teamFeedback, feedback],
    })),

  // ── Reviews ────────────────────────────────────────────────
  addReview: (review) =>
    set((state) => ({
      reviews: [...state.reviews, review],
    })),
  updateReview: (id, status, comments) =>
    set((state) => ({
      reviews: state.reviews.map((r) =>
        r.id === id ? { ...r, status, comments: comments || r.comments } : r
      ),
    })),

  // ── Time Travel ────────────────────────────────────────────
  addSnapshot: (snapshot) =>
    set((state) => {
      const updated = { timelineSnapshots: [...state.timelineSnapshots, snapshot] };
      debouncedSave({ ...state, ...updated });
      return updated;
    }),

  // ── Context Switch / Impromptu ─────────────────────────────
  addContextSwitch: (event) =>
    set((state) => ({
      contextSwitches: [...state.contextSwitches, event],
    })),
  addImpromptuTask: (task) =>
    set((state) => ({
      impromptuTasks: [...state.impromptuTasks, task],
    })),
  updateImpromptuTask: (id, volunteer, status) =>
    set((state) => ({
      impromptuTasks: state.impromptuTasks.map((t) =>
        t.id === id ? { ...t, volunteer, status } : t
      ),
    })),

  // ── API Key ────────────────────────────────────────────────
  setApiKey: (key) => {
    set({ apiKey: key });
    if (typeof window !== 'undefined') {
      localStorage.setItem('kantorku_api_key', key);
    }
  },

  // ── Loading States ─────────────────────────────────────────
  setManagerThinking: (thinking) => set({ isManagerThinking: thinking }),
  setWorking: (working) => set({ isWorking: working }),

  // ── Backend Connection ─────────────────────────────────────
  setBackendConnected: (connected) => set({ isBackendConnected: connected }),

  // ── Settings Dialog ────────────────────────────────────────
  setSettingsOpen: (open) => set({ settingsOpen: open }),

  // ── SSE ────────────────────────────────────────────────────
  setSseConnected: (connected) => set({ sseConnected: connected }),

  // ── Panel Layout ──────────────────────────────────────────
  setPanelLayout: (layout) => {
    set({ panelLayout: layout });
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('kantorku_panel_layout', JSON.stringify(layout));
      } catch {}
    }
  },

  // ── Reset ──────────────────────────────────────────────────
  resetAll: () => {
    set(initialState);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem('kantorku_panel_layout');
    }
  },
}));
