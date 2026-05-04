import { describe, it, expect, beforeEach } from 'vitest';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { WORKERS } from '@/lib/kantorku/workers-data';
import type {
  ClientChatMessage,
  WorkersChatMessage,
  WorkerIdentity,
  OfficeEvent,
  Contract,
  TodoItem,
  MemoryEntry,
  DAGNode,
  DAGEdge,
  UndoableAction,
  CostReport,
  InteractiveQuestion,
} from '@/lib/kantorku/types';

// Helper to get fresh state for each test
function getStore() {
  return useKantorkuStore;
}

// Helper to reset store to initial state before each test
beforeEach(() => {
  useKantorkuStore.getState().resetAll();
});

// ── Initial State ─────────────────────────────────────────────────

describe('Initial state', () => {
  it('should have activeZone set to "lobby"', () => {
    expect(useKantorkuStore.getState().activeZone).toBe('lobby');
  });

  it('should have empty clientMessages', () => {
    expect(useKantorkuStore.getState().clientMessages).toEqual([]);
  });

  it('should have empty workersMessages', () => {
    expect(useKantorkuStore.getState().workersMessages).toEqual([]);
  });

  it('should have workers populated from WORKERS data', () => {
    const { workers } = useKantorkuStore.getState();
    expect(workers.length).toBe(WORKERS.length);
    expect(workers[0].id).toBe('intake');
  });

  it('should have contract as null', () => {
    expect(useKantorkuStore.getState().contract).toBeNull();
  });

  it('should have contractState as "idle"', () => {
    expect(useKantorkuStore.getState().contractState).toBe('idle');
  });

  it('should have empty officeEvents', () => {
    expect(useKantorkuStore.getState().officeEvents).toEqual([]);
  });

  it('should have empty undoStack and redoStack', () => {
    const state = useKantorkuStore.getState();
    expect(state.undoStack).toEqual([]);
    expect(state.redoStack).toEqual([]);
  });

  it('should have costReport as null', () => {
    expect(useKantorkuStore.getState().costReport).toBeNull();
  });

  it('should have empty memoryEntries', () => {
    expect(useKantorkuStore.getState().memoryEntries).toEqual([]);
  });

  it('should have empty dagNodes and dagEdges', () => {
    const state = useKantorkuStore.getState();
    expect(state.dagNodes).toEqual([]);
    expect(state.dagEdges).toEqual([]);
  });

  it('should have default panel layout', () => {
    const { panelLayout } = useKantorkuStore.getState();
    expect(panelLayout).toEqual({ lobby: 30, workspace: 45, dashboard: 25 });
  });

  it('should have isManagerThinking as false', () => {
    expect(useKantorkuStore.getState().isManagerThinking).toBe(false);
  });

  it('should have isWorking as false', () => {
    expect(useKantorkuStore.getState().isWorking).toBe(false);
  });

  it('should have isStreaming as false', () => {
    expect(useKantorkuStore.getState().isStreaming).toBe(false);
  });

  it('should have isBackendConnected as false', () => {
    expect(useKantorkuStore.getState().isBackendConnected).toBe(false);
  });

  it('should have empty apiKey', () => {
    expect(useKantorkuStore.getState().apiKey).toBe('');
  });

  it('should have empty sessions', () => {
    expect(useKantorkuStore.getState().sessions).toEqual([]);
  });

  it('should have empty activeSessionId', () => {
    expect(useKantorkuStore.getState().activeSessionId).toBe('');
  });

  it('should have briefingResult as null', () => {
    expect(useKantorkuStore.getState().briefingResult).toBeNull();
  });

  it('should have intakeResult as null', () => {
    expect(useKantorkuStore.getState().intakeResult).toBeNull();
  });

  it('should have empty discussionRounds', () => {
    expect(useKantorkuStore.getState().discussionRounds).toEqual([]);
  });
});

// ── setActiveZone ─────────────────────────────────────────────────

describe('setActiveZone', () => {
  it('should set activeZone to "workspace"', () => {
    useKantorkuStore.getState().setActiveZone('workspace');
    expect(useKantorkuStore.getState().activeZone).toBe('workspace');
  });

  it('should set activeZone to "dashboard"', () => {
    useKantorkuStore.getState().setActiveZone('dashboard');
    expect(useKantorkuStore.getState().activeZone).toBe('dashboard');
  });

  it('should set activeZone back to "lobby"', () => {
    useKantorkuStore.getState().setActiveZone('workspace');
    useKantorkuStore.getState().setActiveZone('lobby');
    expect(useKantorkuStore.getState().activeZone).toBe('lobby');
  });
});

// ── Client Chat ──────────────────────────────────────────────────

describe('Client Chat operations', () => {
  const mockMessage: ClientChatMessage = {
    id: 'msg_1',
    role: 'user',
    content: 'Hello, I need help',
    timestamp: new Date().toISOString(),
  };

  describe('addClientMessage', () => {
    it('should add a message to clientMessages', () => {
      useKantorkuStore.getState().addClientMessage(mockMessage);
      expect(useKantorkuStore.getState().clientMessages).toHaveLength(1);
      expect(useKantorkuStore.getState().clientMessages[0].id).toBe('msg_1');
    });

    it('should append multiple messages in order', () => {
      const msg1: ClientChatMessage = { ...mockMessage, id: 'msg_1' };
      const msg2: ClientChatMessage = { ...mockMessage, id: 'msg_2' };
      useKantorkuStore.getState().addClientMessage(msg1);
      useKantorkuStore.getState().addClientMessage(msg2);
      const { clientMessages } = useKantorkuStore.getState();
      expect(clientMessages).toHaveLength(2);
      expect(clientMessages[0].id).toBe('msg_1');
      expect(clientMessages[1].id).toBe('msg_2');
    });
  });

  describe('clearClientMessages', () => {
    it('should remove all client messages', () => {
      useKantorkuStore.getState().addClientMessage(mockMessage);
      expect(useKantorkuStore.getState().clientMessages).toHaveLength(1);
      useKantorkuStore.getState().clearClientMessages();
      expect(useKantorkuStore.getState().clientMessages).toHaveLength(0);
    });
  });

  describe('searchClientMessages', () => {
    beforeEach(() => {
      const messages: ClientChatMessage[] = [
        { id: '1', role: 'user', content: 'Build me a React app', timestamp: new Date().toISOString() },
        { id: '2', role: 'manager', content: 'Sure, what features?', timestamp: new Date().toISOString() },
        { id: '3', role: 'user', content: 'I need a dashboard with charts', timestamp: new Date().toISOString() },
      ];
      for (const msg of messages) {
        useKantorkuStore.getState().addClientMessage(msg);
      }
    });

    it('should find messages matching the query (case-insensitive)', () => {
      const results = useKantorkuStore.getState().searchClientMessages('react');
      expect(results).toHaveLength(1);
      expect(results[0].id).toBe('1');
    });

    it('should find messages with partial match', () => {
      const results = useKantorkuStore.getState().searchClientMessages('dash');
      expect(results).toHaveLength(1);
      expect(results[0].id).toBe('3');
    });

    it('should return empty array for no matches', () => {
      const results = useKantorkuStore.getState().searchClientMessages('python');
      expect(results).toHaveLength(0);
    });

    it('should match case-insensitively', () => {
      const results = useKantorkuStore.getState().searchClientMessages('REACT');
      expect(results).toHaveLength(1);
    });
  });

  describe('answerQuestion', () => {
    it('should mark a question as answered', () => {
      const question: InteractiveQuestion = {
        id: 'q1',
        question: 'Which framework?',
        options: [
          { label: 'A', text: 'React' },
          { label: 'B', text: 'Vue' },
        ],
        allow_other: true,
      };
      const msg: ClientChatMessage = {
        id: 'msg_q',
        role: 'manager',
        content: 'Which framework do you prefer?',
        timestamp: new Date().toISOString(),
        question,
      };
      useKantorkuStore.getState().addClientMessage(msg);
      useKantorkuStore.getState().answerQuestion('msg_q', 'A');

      const updated = useKantorkuStore.getState().clientMessages[0];
      expect(updated.question?.answered).toBe(true);
      expect(updated.question?.selected_option).toBe('A');
    });

    it('should include custom answer when provided', () => {
      const question: InteractiveQuestion = {
        id: 'q2',
        question: 'Which framework?',
        options: [{ label: 'A', text: 'React' }],
        allow_other: true,
      };
      const msg: ClientChatMessage = {
        id: 'msg_q2',
        role: 'manager',
        content: 'Which framework?',
        timestamp: new Date().toISOString(),
        question,
      };
      useKantorkuStore.getState().addClientMessage(msg);
      useKantorkuStore.getState().answerQuestion('msg_q2', 'Other', 'Svelte');

      const updated = useKantorkuStore.getState().clientMessages[0];
      expect(updated.question?.custom_answer).toBe('Svelte');
    });

    it('should not modify messages without a question', () => {
      const msg: ClientChatMessage = {
        id: 'msg_plain',
        role: 'user',
        content: 'Just a regular message',
        timestamp: new Date().toISOString(),
      };
      useKantorkuStore.getState().addClientMessage(msg);
      useKantorkuStore.getState().answerQuestion('msg_plain', 'A');

      const result = useKantorkuStore.getState().clientMessages[0];
      expect(result.question).toBeUndefined();
    });
  });
});

// ── Workers Chat ─────────────────────────────────────────────────

describe('Workers Chat operations', () => {
  const mockWorkersMsg: WorkersChatMessage = {
    id: 'wmsg_1',
    from_id: 'coder_backend',
    message_type: 'speak',
    content: 'I can handle the API route',
    timestamp: new Date().toISOString(),
  };

  describe('addWorkersMessage', () => {
    it('should add a message to workersMessages', () => {
      useKantorkuStore.getState().addWorkersMessage(mockWorkersMsg);
      expect(useKantorkuStore.getState().workersMessages).toHaveLength(1);
      expect(useKantorkuStore.getState().workersMessages[0].from_id).toBe('coder_backend');
    });

    it('should append multiple workers messages', () => {
      useKantorkuStore.getState().addWorkersMessage(mockWorkersMsg);
      useKantorkuStore.getState().addWorkersMessage({ ...mockWorkersMsg, id: 'wmsg_2' });
      expect(useKantorkuStore.getState().workersMessages).toHaveLength(2);
    });
  });

  describe('clearWorkersMessages', () => {
    it('should remove all workers messages', () => {
      useKantorkuStore.getState().addWorkersMessage(mockWorkersMsg);
      useKantorkuStore.getState().clearWorkersMessages();
      expect(useKantorkuStore.getState().workersMessages).toHaveLength(0);
    });
  });
});

// ── Workers ──────────────────────────────────────────────────────

describe('Worker operations', () => {
  describe('updateWorkerStatus', () => {
    it('should update a worker status to busy', () => {
      useKantorkuStore.getState().updateWorkerStatus('intake', 'busy', 'Processing message');
      const worker = useKantorkuStore.getState().workers.find((w) => w.id === 'intake');
      expect(worker?.status).toBe('busy');
      expect(worker?.current_task).toBe('Processing message');
    });

    it('should update status without task', () => {
      useKantorkuStore.getState().updateWorkerStatus('intake', 'idle');
      const worker = useKantorkuStore.getState().workers.find((w) => w.id === 'intake');
      expect(worker?.status).toBe('idle');
      expect(worker?.current_task).toBeUndefined();
    });

    it('should not affect other workers', () => {
      useKantorkuStore.getState().updateWorkerStatus('intake', 'busy', 'task');
      const scout = useKantorkuStore.getState().workers.find((w) => w.id === 'scout');
      expect(scout?.status).toBe('idle');
    });
  });

  describe('hireWorker', () => {
    it('should add a new worker to the list', () => {
      const newWorker: WorkerIdentity = {
        id: 'custom_1',
        model: 'custom/model',
        squad: 'engineering',
        role: 'Custom Worker',
        skill_md: 'Does custom things',
        personality: 'Unique',
        emoji: '🤖',
        color: '#ff00ff',
        status: 'idle',
        is_custom: true,
      };
      useKantorkuStore.getState().hireWorker(newWorker);
      const worker = useKantorkuStore.getState().workers.find((w) => w.id === 'custom_1');
      expect(worker).toBeDefined();
      expect(worker?.role).toBe('Custom Worker');
    });

    it('should not add a duplicate worker', () => {
      const initialCount = useKantorkuStore.getState().workers.length;
      const intakeWorker = WORKERS[0]; // intake
      useKantorkuStore.getState().hireWorker(intakeWorker);
      expect(useKantorkuStore.getState().workers.length).toBe(initialCount);
    });
  });

  describe('fireWorker', () => {
    it('should remove a worker by id', () => {
      const initialCount = useKantorkuStore.getState().workers.length;
      useKantorkuStore.getState().fireWorker('intake');
      expect(useKantorkuStore.getState().workers.length).toBe(initialCount - 1);
      const worker = useKantorkuStore.getState().workers.find((w) => w.id === 'intake');
      expect(worker).toBeUndefined();
    });

    it('should not affect other workers when firing one', () => {
      useKantorkuStore.getState().fireWorker('intake');
      const scout = useKantorkuStore.getState().workers.find((w) => w.id === 'scout');
      expect(scout).toBeDefined();
    });
  });
});

// ── Contract ─────────────────────────────────────────────────────

describe('Contract operations', () => {
  const mockContract: Contract = {
    id: 'contract_1',
    session_id: 'session_1',
    title: 'Build a web app',
    description: 'Create a full-stack web application',
    todos: [
      {
        id: 'todo_1',
        description: 'Set up API routes',
        assigned_to: 'coder_backend',
        status: 'pending',
        depends_on: [],
        priority: 'high',
      },
      {
        id: 'todo_2',
        description: 'Build UI components',
        assigned_to: 'coder_frontend',
        status: 'pending',
        depends_on: ['todo_1'],
        priority: 'medium',
      },
    ] as TodoItem[],
    state: 'working',
    client_messages: [{ role: 'user', content: 'Build it' }],
    manager_messages: [{ role: 'manager', content: 'On it!' }],
    team_feedback_rounds: [],
    team_approved: false,
    approval_gates: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  describe('setContract', () => {
    it('should set the contract', () => {
      useKantorkuStore.getState().setContract(mockContract);
      expect(useKantorkuStore.getState().contract).not.toBeNull();
      expect(useKantorkuStore.getState().contract?.id).toBe('contract_1');
    });

    it('should create a timeline snapshot when setting a contract', () => {
      useKantorkuStore.getState().setContract(mockContract);
      expect(useKantorkuStore.getState().timelineSnapshots.length).toBe(1);
      expect(useKantorkuStore.getState().timelineSnapshots[0].contract_id).toBe('contract_1');
    });

    it('should set contract to null without adding a snapshot', () => {
      useKantorkuStore.getState().setContract(mockContract);
      useKantorkuStore.getState().setContract(null);
      expect(useKantorkuStore.getState().contract).toBeNull();
      // Only 1 snapshot from the initial set
      expect(useKantorkuStore.getState().timelineSnapshots.length).toBe(1);
    });
  });

  describe('setContractState', () => {
    it('should update the contractState', () => {
      useKantorkuStore.getState().setContractState('working');
      expect(useKantorkuStore.getState().contractState).toBe('working');
    });

    it('should cycle through contract states', () => {
      const store = useKantorkuStore.getState();
      store.setContractState('manager_thinking');
      expect(useKantorkuStore.getState().contractState).toBe('manager_thinking');
      store.setContractState('team_consult');
      expect(useKantorkuStore.getState().contractState).toBe('team_consult');
      store.setContractState('done');
      expect(useKantorkuStore.getState().contractState).toBe('done');
    });
  });

  describe('updateTodoStatus', () => {
    beforeEach(() => {
      useKantorkuStore.getState().setContract(mockContract);
    });

    it('should update a todo status to in_progress', () => {
      useKantorkuStore.getState().updateTodoStatus('todo_1', 'in_progress');
      const todo = useKantorkuStore.getState().contract?.todos.find((t) => t.id === 'todo_1');
      expect(todo?.status).toBe('in_progress');
      expect(todo?.started_at).toBeDefined();
    });

    it('should update a todo status to done and set completed_at', () => {
      useKantorkuStore.getState().updateTodoStatus('todo_1', 'done', 'All done');
      const todo = useKantorkuStore.getState().contract?.todos.find((t) => t.id === 'todo_1');
      expect(todo?.status).toBe('done');
      expect(todo?.result).toBe('All done');
      expect(todo?.completed_at).toBeDefined();
    });

    it('should update a todo status to failed with error', () => {
      useKantorkuStore.getState().updateTodoStatus('todo_1', 'failed', undefined, 'API timeout');
      const todo = useKantorkuStore.getState().contract?.todos.find((t) => t.id === 'todo_1');
      expect(todo?.status).toBe('failed');
      expect(todo?.error).toBe('API timeout');
    });

    it('should not affect other todos', () => {
      useKantorkuStore.getState().updateTodoStatus('todo_1', 'in_progress');
      const todo2 = useKantorkuStore.getState().contract?.todos.find((t) => t.id === 'todo_2');
      expect(todo2?.status).toBe('pending');
    });

    it('should do nothing when no contract exists', () => {
      useKantorkuStore.getState().setContract(null);
      // Should not throw
      useKantorkuStore.getState().updateTodoStatus('todo_1', 'done');
      expect(useKantorkuStore.getState().contract).toBeNull();
    });
  });
});

// ── Office Events ────────────────────────────────────────────────

describe('Office Events operations', () => {
  describe('addOfficeEvent', () => {
    it('should add an office event', () => {
      const event: OfficeEvent = { type: 'task_start', from_id: 'intake' };
      useKantorkuStore.getState().addOfficeEvent(event);
      expect(useKantorkuStore.getState().officeEvents).toHaveLength(1);
      expect(useKantorkuStore.getState().officeEvents[0].type).toBe('task_start');
    });

    it('should add a timestamp if not provided', () => {
      const event: OfficeEvent = { type: 'task_start' };
      useKantorkuStore.getState().addOfficeEvent(event);
      expect(useKantorkuStore.getState().officeEvents[0].timestamp).toBeDefined();
    });

    it('should preserve provided timestamp', () => {
      const ts = '2024-01-01T00:00:00.000Z';
      const event: OfficeEvent = { type: 'task_start', timestamp: ts };
      useKantorkuStore.getState().addOfficeEvent(event);
      expect(useKantorkuStore.getState().officeEvents[0].timestamp).toBe(ts);
    });

    it('should cap office events at 200', () => {
      for (let i = 0; i < 250; i++) {
        useKantorkuStore.getState().addOfficeEvent({ type: 'event', content: `event_${i}` });
      }
      expect(useKantorkuStore.getState().officeEvents.length).toBeLessThanOrEqual(200);
    });
  });

  describe('clearOfficeEvents', () => {
    it('should remove all office events', () => {
      useKantorkuStore.getState().addOfficeEvent({ type: 'test' });
      useKantorkuStore.getState().clearOfficeEvents();
      expect(useKantorkuStore.getState().officeEvents).toHaveLength(0);
    });
  });
});

// ── Undo/Redo ────────────────────────────────────────────────────

describe('Undo/Redo operations', () => {
  const mockAction: UndoableAction = {
    id: 'action_1',
    type: 'contract_update',
    description: 'Updated contract state',
    timestamp: new Date().toISOString(),
    before: { state: 'idle' },
    after: { state: 'working' },
  };

  describe('pushUndo', () => {
    it('should add an action to the undo stack', () => {
      useKantorkuStore.getState().pushUndo(mockAction);
      expect(useKantorkuStore.getState().undoStack).toHaveLength(1);
    });

    it('should clear the redo stack when a new action is pushed', () => {
      useKantorkuStore.getState().pushUndo(mockAction);
      useKantorkuStore.getState().undo();
      expect(useKantorkuStore.getState().redoStack).toHaveLength(1);
      useKantorkuStore.getState().pushUndo({ ...mockAction, id: 'action_2' });
      expect(useKantorkuStore.getState().redoStack).toHaveLength(0);
    });

    it('should cap undo stack at 50 entries', () => {
      for (let i = 0; i < 60; i++) {
        useKantorkuStore.getState().pushUndo({
          ...mockAction,
          id: `action_${i}`,
        });
      }
      expect(useKantorkuStore.getState().undoStack.length).toBeLessThanOrEqual(50);
    });
  });

  describe('undo', () => {
    it('should move the last action from undoStack to redoStack', () => {
      useKantorkuStore.getState().pushUndo(mockAction);
      useKantorkuStore.getState().undo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(0);
      expect(useKantorkuStore.getState().redoStack).toHaveLength(1);
      expect(useKantorkuStore.getState().redoStack[0].id).toBe('action_1');
    });

    it('should do nothing when undoStack is empty', () => {
      useKantorkuStore.getState().undo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(0);
      expect(useKantorkuStore.getState().redoStack).toHaveLength(0);
    });
  });

  describe('redo', () => {
    it('should move the last action from redoStack to undoStack', () => {
      useKantorkuStore.getState().pushUndo(mockAction);
      useKantorkuStore.getState().undo();
      useKantorkuStore.getState().redo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(1);
      expect(useKantorkuStore.getState().redoStack).toHaveLength(0);
    });

    it('should do nothing when redoStack is empty', () => {
      useKantorkuStore.getState().redo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(0);
      expect(useKantorkuStore.getState().redoStack).toHaveLength(0);
    });
  });

  describe('canUndo / canRedo', () => {
    it('canUndo returns false when undoStack is empty', () => {
      expect(useKantorkuStore.getState().canUndo()).toBe(false);
    });

    it('canUndo returns true when undoStack has items', () => {
      useKantorkuStore.getState().pushUndo(mockAction);
      expect(useKantorkuStore.getState().canUndo()).toBe(true);
    });

    it('canRedo returns false when redoStack is empty', () => {
      expect(useKantorkuStore.getState().canRedo()).toBe(false);
    });

    it('canRedo returns true when redoStack has items', () => {
      useKantorkuStore.getState().pushUndo(mockAction);
      useKantorkuStore.getState().undo();
      expect(useKantorkuStore.getState().canRedo()).toBe(true);
    });

    it('full undo/redo cycle works correctly', () => {
      const action1: UndoableAction = { ...mockAction, id: 'a1' };
      const action2: UndoableAction = { ...mockAction, id: 'a2' };

      useKantorkuStore.getState().pushUndo(action1);
      useKantorkuStore.getState().pushUndo(action2);

      expect(useKantorkuStore.getState().canUndo()).toBe(true);
      expect(useKantorkuStore.getState().canRedo()).toBe(false);

      useKantorkuStore.getState().undo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(1);
      expect(useKantorkuStore.getState().undoStack[0].id).toBe('a1');
      expect(useKantorkuStore.getState().redoStack).toHaveLength(1);
      expect(useKantorkuStore.getState().redoStack[0].id).toBe('a2');

      useKantorkuStore.getState().undo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(0);
      expect(useKantorkuStore.getState().redoStack).toHaveLength(2);

      useKantorkuStore.getState().redo();
      expect(useKantorkuStore.getState().undoStack).toHaveLength(1);
      expect(useKantorkuStore.getState().undoStack[0].id).toBe('a1');
      expect(useKantorkuStore.getState().redoStack).toHaveLength(1);
      expect(useKantorkuStore.getState().redoStack[0].id).toBe('a2');
    });
  });
});

// ── Cost & Metrics ───────────────────────────────────────────────

describe('Cost operations', () => {
  describe('addCostEntry', () => {
    it('should create a costReport if none exists', () => {
      useKantorkuStore.getState().addCostEntry('claude-opus-4-6', 1000, 500, 0.05);
      const report = useKantorkuStore.getState().costReport;
      expect(report).not.toBeNull();
      expect(report?.total_cost).toBeCloseTo(0.05, 4);
      expect(report?.total_input_tokens).toBe(1000);
      expect(report?.total_output_tokens).toBe(500);
    });

    it('should accumulate costs on existing report', () => {
      useKantorkuStore.getState().addCostEntry('claude-opus-4-6', 1000, 500, 0.05);
      useKantorkuStore.getState().addCostEntry('claude-sonnet-4-6', 2000, 1000, 0.03);
      const report = useKantorkuStore.getState().costReport;
      expect(report?.total_cost).toBeCloseTo(0.08, 4);
      expect(report?.total_input_tokens).toBe(3000);
      expect(report?.total_output_tokens).toBe(1500);
    });

    it('should track by_model correctly', () => {
      useKantorkuStore.getState().addCostEntry('claude-opus-4-6', 1000, 500, 0.05);
      useKantorkuStore.getState().addCostEntry('claude-opus-4-6', 500, 200, 0.02);
      const byModel = useKantorkuStore.getState().costReport?.by_model;
      expect(byModel?.['claude-opus-4-6'].calls).toBe(2);
      expect(byModel?.['claude-opus-4-6'].cost).toBeCloseTo(0.07, 4);
      expect(byModel?.['claude-opus-4-6'].tokens).toBe(2200);
    });

    it('should track by_worker when workerId is provided', () => {
      useKantorkuStore.getState().addCostEntry('model', 1000, 500, 0.05, 'coder_backend');
      const byWorker = useKantorkuStore.getState().costReport?.by_worker;
      expect(byWorker?.['coder_backend'].calls).toBe(1);
      expect(byWorker?.['coder_backend'].cost).toBeCloseTo(0.05, 4);
    });

    it('should not track by_worker when workerId is not provided', () => {
      useKantorkuStore.getState().addCostEntry('model', 1000, 500, 0.05);
      const byWorker = useKantorkuStore.getState().costReport?.by_worker;
      expect(Object.keys(byWorker ?? {}).length).toBe(0);
    });
  });

  describe('setCostReport', () => {
    it('should set the full cost report', () => {
      const report: CostReport = {
        total_cost: 1.5,
        total_input_tokens: 10000,
        total_output_tokens: 5000,
        entries: [],
        by_model: {},
        by_worker: {},
      };
      useKantorkuStore.getState().setCostReport(report);
      expect(useKantorkuStore.getState().costReport?.total_cost).toBe(1.5);
    });
  });
});

// ── Memory Operations ────────────────────────────────────────────

describe('Memory operations', () => {
  const mockEntry: MemoryEntry = {
    id: 'mem_1',
    ring: 1,
    key: 'task_result',
    value: 'Successfully built API',
    timestamp: new Date().toISOString(),
    session_id: 'session_1',
  };

  describe('addMemoryEntry', () => {
    it('should add a memory entry', () => {
      useKantorkuStore.getState().addMemoryEntry(mockEntry);
      expect(useKantorkuStore.getState().memoryEntries).toHaveLength(1);
      expect(useKantorkuStore.getState().memoryEntries[0].key).toBe('task_result');
    });
  });

  describe('clearMemoryRing', () => {
    it('should clear entries for a specific ring', () => {
      useKantorkuStore.getState().addMemoryEntry({ ...mockEntry, ring: 1, id: 'mem1' });
      useKantorkuStore.getState().addMemoryEntry({ ...mockEntry, ring: 2, id: 'mem2' });
      useKantorkuStore.getState().addMemoryEntry({ ...mockEntry, ring: 1, id: 'mem3' });

      useKantorkuStore.getState().clearMemoryRing(1);
      const entries = useKantorkuStore.getState().memoryEntries;
      expect(entries).toHaveLength(1);
      expect(entries[0].ring).toBe(2);
    });

    it('should not affect other rings', () => {
      useKantorkuStore.getState().addMemoryEntry({ ...mockEntry, ring: 1, id: 'mem1' });
      useKantorkuStore.getState().addMemoryEntry({ ...mockEntry, ring: 2, id: 'mem2' });
      useKantorkuStore.getState().clearMemoryRing(1);
      expect(useKantorkuStore.getState().memoryEntries.some((e) => e.ring === 2)).toBe(true);
    });
  });

  describe('queryMemory', () => {
    beforeEach(() => {
      useKantorkuStore.getState().addMemoryEntry({
        id: 'mem1',
        ring: 1,
        key: 'task_result',
        value: 'API built successfully',
        timestamp: new Date().toISOString(),
      });
      useKantorkuStore.getState().addMemoryEntry({
        id: 'mem2',
        ring: 1,
        key: 'error_log',
        value: 'Timeout occurred',
        timestamp: new Date().toISOString(),
      });
      useKantorkuStore.getState().addMemoryEntry({
        id: 'mem3',
        ring: 2,
        key: 'lesson',
        value: 'Always add retry logic',
        timestamp: new Date().toISOString(),
      });
    });

    it('should return all entries for a given ring when no query', () => {
      const results = useKantorkuStore.getState().queryMemory(1);
      expect(results).toHaveLength(2);
    });

    it('should filter by query string (case-insensitive)', () => {
      const results = useKantorkuStore.getState().queryMemory(1, 'api');
      expect(results).toHaveLength(1);
      expect(results[0].key).toBe('task_result');
    });

    it('should search both key and value', () => {
      const results = useKantorkuStore.getState().queryMemory(1, 'timeout');
      expect(results).toHaveLength(1);
      expect(results[0].key).toBe('error_log');
    });

    it('should return empty for ring with no entries', () => {
      const results = useKantorkuStore.getState().queryMemory(3);
      expect(results).toHaveLength(0);
    });

    it('should return empty when query matches nothing', () => {
      const results = useKantorkuStore.getState().queryMemory(1, 'nonexistent');
      expect(results).toHaveLength(0);
    });
  });
});

// ── DAG Operations ───────────────────────────────────────────────

describe('DAG operations', () => {
  const mockNodes: DAGNode[] = [
    { id: 'node_1', label: 'Setup API', status: 'pending', assigned_to: 'coder_backend', depth: 0 },
    { id: 'node_2', label: 'Build UI', status: 'pending', assigned_to: 'coder_frontend', depth: 1 },
  ];
  const mockEdges: DAGEdge[] = [
    { from: 'node_1', to: 'node_2', type: 'depends_on' },
  ];

  describe('setDAG', () => {
    it('should set DAG nodes and edges', () => {
      useKantorkuStore.getState().setDAG(mockNodes, mockEdges);
      expect(useKantorkuStore.getState().dagNodes).toHaveLength(2);
      expect(useKantorkuStore.getState().dagEdges).toHaveLength(1);
    });
  });

  describe('updateDAGNode', () => {
    beforeEach(() => {
      useKantorkuStore.getState().setDAG(mockNodes, mockEdges);
    });

    it('should update a node status', () => {
      useKantorkuStore.getState().updateDAGNode('node_1', 'in_progress');
      const node = useKantorkuStore.getState().dagNodes.find((n) => n.id === 'node_1');
      expect(node?.status).toBe('in_progress');
    });

    it('should not affect other nodes', () => {
      useKantorkuStore.getState().updateDAGNode('node_1', 'done');
      const node2 = useKantorkuStore.getState().dagNodes.find((n) => n.id === 'node_2');
      expect(node2?.status).toBe('pending');
    });
  });
});

// ── resetAll ─────────────────────────────────────────────────────

describe('resetAll', () => {
  it('should reset all state to initial values', () => {
    const store = useKantorkuStore.getState();

    // Mutate state
    store.setActiveZone('workspace');
    store.addClientMessage({
      id: '1',
      role: 'user',
      content: 'test',
      timestamp: new Date().toISOString(),
    });
    store.addWorkersMessage({
      id: '1',
      from_id: 'intake',
      message_type: 'speak',
      content: 'test',
      timestamp: new Date().toISOString(),
    });
    store.setContractState('working');
    store.addOfficeEvent({ type: 'test' });
    store.pushUndo({
      id: '1',
      type: 'contract_update',
      description: 'test',
      timestamp: new Date().toISOString(),
      before: {},
      after: {},
    });
    store.addMemoryEntry({
      id: 'mem1',
      ring: 1,
      key: 'test',
      value: 'test',
      timestamp: new Date().toISOString(),
    });
    store.setDAG(
      [{ id: 'n1', label: 'Test', status: 'pending', assigned_to: 'intake', depth: 0 }],
      []
    );

    // Reset
    store.resetAll();

    const state = useKantorkuStore.getState();
    expect(state.activeZone).toBe('lobby');
    expect(state.clientMessages).toEqual([]);
    expect(state.workersMessages).toEqual([]);
    expect(state.contractState).toBe('idle');
    expect(state.contract).toBeNull();
    expect(state.officeEvents).toEqual([]);
    expect(state.undoStack).toEqual([]);
    expect(state.redoStack).toEqual([]);
    expect(state.memoryEntries).toEqual([]);
    expect(state.dagNodes).toEqual([]);
    expect(state.dagEdges).toEqual([]);
    expect(state.costReport).toBeNull();
  });

  it('should reset workers back to WORKERS data', () => {
    useKantorkuStore.getState().fireWorker('intake');
    expect(useKantorkuStore.getState().workers.find((w) => w.id === 'intake')).toBeUndefined();

    useKantorkuStore.getState().resetAll();
    expect(useKantorkuStore.getState().workers.find((w) => w.id === 'intake')).toBeDefined();
  });
});
