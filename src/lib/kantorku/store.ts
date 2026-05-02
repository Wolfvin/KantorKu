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
} from './types';
import { WORKERS } from './workers-data';

interface KantorkuStore {
  // ── Active Zone ───────────────────────────────────────────────
  activeZone: 'lobby' | 'workspace' | 'dashboard';
  setActiveZone: (zone: 'lobby' | 'workspace' | 'dashboard') => void;

  // ── Sessions ──────────────────────────────────────────────────
  sessions: Session[];
  activeSessionId: string;
  setActiveSession: (id: string) => void;
  addSession: (session: Session) => void;

  // ── Contract State Machine ────────────────────────────────────
  contract: Contract | null;
  contractState: ContractState;
  setContract: (contract: Contract | null) => void;
  setContractState: (state: ContractState) => void;
  updateTodoStatus: (todoId: string, status: TodoItem['status']) => void;

  // ── Client Chat (Panel 1) ────────────────────────────────────
  clientMessages: ClientChatMessage[];
  addClientMessage: (msg: ClientChatMessage) => void;
  clearClientMessages: () => void;

  // ── Workers Chat (GroupChannel) ──────────────────────────────
  workersMessages: WorkersChatMessage[];
  addWorkersMessage: (msg: WorkersChatMessage) => void;
  clearWorkersMessages: () => void;

  // ── Workers ───────────────────────────────────────────────────
  workers: WorkerIdentity[];
  updateWorkerStatus: (id: string, status: string, task?: string) => void;

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
  }>;
  addDiscussionRound: (round: { round_number: number; messages: WorkersChatMessage[]; summary: string; decisions: string[] }) => void;

  // ── Intake ────────────────────────────────────────────────────
  intakeResult: IntakeResult | null;
  setIntakeResult: (result: IntakeResult | null) => void;

  // ── Cost & Metrics (Dashboard) ───────────────────────────────
  costReport: CostReport | null;
  setCostReport: (report: CostReport) => void;
  addCostEntry: (model: string, inputTokens: number, outputTokens: number, costUsd: number) => void;
  metricsSummary: MetricsSummary | null;
  setMetricsSummary: (summary: MetricsSummary) => void;
  healthStatus: HealthStatus | null;
  setHealthStatus: (status: HealthStatus) => void;
  circuitBreakers: CircuitBreakerState[];
  setCircuitBreakers: (breakers: CircuitBreakerState[]) => void;

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
}

export const useKantorkuStore = create<KantorkuStore>((set, get) => ({
  // ── Active Zone ─────────────────────────────────────────────
  activeZone: 'lobby',
  setActiveZone: (zone) => set({ activeZone: zone }),

  // ── Sessions ────────────────────────────────────────────────
  sessions: [],
  activeSessionId: '',
  setActiveSession: (id) => set({ activeSessionId: id }),
  addSession: (session) =>
    set((state) => ({ sessions: [...state.sessions, session] })),

  // ── Contract State Machine ──────────────────────────────────
  contract: null,
  contractState: 'idle',
  setContract: (contract) => set({ contract }),
  setContractState: (state) => set({ contractState: state }),
  updateTodoStatus: (todoId, status) =>
    set((state) => {
      if (!state.contract) return state;
      return {
        contract: {
          ...state.contract,
          todos: state.contract.todos.map((t) =>
            t.id === todoId ? { ...t, status } : t
          ),
        },
      };
    }),

  // ── Client Chat ────────────────────────────────────────────
  clientMessages: [],
  addClientMessage: (msg) =>
    set((state) => ({ clientMessages: [...state.clientMessages, msg] })),
  clearClientMessages: () => set({ clientMessages: [] }),

  // ── Workers Chat ───────────────────────────────────────────
  workersMessages: [],
  addWorkersMessage: (msg) =>
    set((state) => ({ workersMessages: [...state.workersMessages, msg] })),
  clearWorkersMessages: () => set({ workersMessages: [] }),

  // ── Workers ────────────────────────────────────────────────
  workers: WORKERS,
  updateWorkerStatus: (id, status, task) =>
    set((state) => ({
      workers: state.workers.map((w) =>
        w.id === id
          ? {
              ...w,
              status: status as WorkerIdentity['status'],
              current_task: task,
            }
          : w
      ),
    })),

  // ── Office Events ──────────────────────────────────────────
  officeEvents: [],
  addOfficeEvent: (event) =>
    set((state) => ({
      officeEvents: [...state.officeEvents.slice(-99), event],
    })),
  clearOfficeEvents: () => set({ officeEvents: [] }),

  // ── Briefing ───────────────────────────────────────────────
  briefingResult: null,
  setBriefingResult: (result) => set({ briefingResult: result }),
  discussionRounds: [],
  addDiscussionRound: (round) =>
    set((state) => ({
      discussionRounds: [...state.discussionRounds, round],
    })),

  // ── Intake ─────────────────────────────────────────────────
  intakeResult: null,
  setIntakeResult: (result) => set({ intakeResult: result }),

  // ── Cost & Metrics ─────────────────────────────────────────
  costReport: null,
  setCostReport: (report) => set({ costReport: report }),
  addCostEntry: (model, inputTokens, outputTokens, costUsd) =>
    set((state) => {
      const existing = state.costReport || {
        total_cost: 0,
        total_input_tokens: 0,
        total_output_tokens: 0,
        entries: [],
        by_model: {},
      };
      const entry = {
        model,
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        cost_usd: costUsd,
        timestamp: new Date().toISOString(),
      };
      const byModel = { ...existing.by_model };
      const prev = byModel[model] || { cost: 0, calls: 0, tokens: 0 };
      byModel[model] = {
        cost: prev.cost + costUsd,
        calls: prev.calls + 1,
        tokens: prev.tokens + inputTokens + outputTokens,
      };
      return {
        costReport: {
          total_cost: existing.total_cost + costUsd,
          total_input_tokens: existing.total_input_tokens + inputTokens,
          total_output_tokens: existing.total_output_tokens + outputTokens,
          entries: [...existing.entries.slice(-49), entry],
          by_model: byModel,
        },
      };
    }),
  metricsSummary: null,
  setMetricsSummary: (summary) => set({ metricsSummary: summary }),
  healthStatus: null,
  setHealthStatus: (status) => set({ healthStatus: status }),
  circuitBreakers: [],
  setCircuitBreakers: (breakers) => set({ circuitBreakers: breakers }),

  // ── API Key ────────────────────────────────────────────────
  apiKey: '',
  setApiKey: (key) => set({ apiKey: key }),

  // ── Loading States ─────────────────────────────────────────
  isManagerThinking: false,
  setManagerThinking: (thinking) => set({ isManagerThinking: thinking }),
  isWorking: false,
  setWorking: (working) => set({ isWorking: working }),

  // ── Backend Connection ─────────────────────────────────────
  isBackendConnected: false,
  setBackendConnected: (connected) => set({ isBackendConnected: connected }),

  // ── Settings Dialog ────────────────────────────────────────
  settingsOpen: false,
  setSettingsOpen: (open) => set({ settingsOpen: open }),
}));
