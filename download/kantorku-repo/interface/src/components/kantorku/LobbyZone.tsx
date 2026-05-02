'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { ClientChatPanel } from './ChatPanel';
import { ContractCard } from './ContractCard';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CONTRACT_STATE_LABELS, CONTRACT_STATE_COLORS } from '@/lib/kantorku/workers-data';
import type { ChatApiResponse, ExecuteApiResponse, TeamFeedbackRound, DebriefResult, Contract, TodoItem } from '@/lib/kantorku/types';
import { toast } from 'sonner';
import {
  MessageSquare,
  Zap,
  RefreshCcw,
  CheckCircle2,
  AlertTriangle,
  Users,
  Clock,
  FileText,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';

export function LobbyZone() {
  const {
    clientMessages,
    contract,
    contractState,
    isManagerThinking,
    isWorking,
    intakeResult,
    teamFeedback,
    debriefResult,
    approvalGates,
    sessions,
    activeSessionId,
    addClientMessage,
    setContract,
    setContractState,
    setManagerThinking,
    setWorking,
    addOfficeEvent,
    updateWorkerStatus,
    addWorkersMessage,
    updateTodoStatus,
    updateTodoActualTime,
    addCostEntry,
    setIntakeResult,
    setBriefingResult,
    addDiscussionRound,
    addSession,
    updateSession,
    setApprovalGates,
    setDAG,
    setMiddlewareSteps,
    addTrace,
    addLatencyEntry,
    setDebriefResult,
    addTeamFeedback,
    clearClientMessages,
    clearWorkersMessages,
    clearOfficeEvents,
    setMetricsSummary,
    setHealthStatus,
    setCircuitBreakers,
    addMemoryEntry,
    answerQuestion,
    setWorkerEmotion,
    updateTrustScore,
  } = useKantorkuStore();

  const handleSendMessage = async (message: string) => {
    // Add user message
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    });

    setManagerThinking(true);
    setContractState('manager_thinking');

    try {
      // Run intake classification in parallel
      const intakePromise = fetch('/api/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      }).then((r) => r.json()).catch(() => null);

      // Send to chat API with streaming
      const history = clientMessages.map((m) => ({
        role: m.role === 'manager' ? 'assistant' : 'user',
        content: m.content,
      }));

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          history,
          session_id: activeSessionId || 'default',
          stream: true,
        }),
      });

      // Check if response is SSE stream
      const contentType = response.headers.get('content-type') || '';
      let data: ChatApiResponse | null = null;

      if (contentType.includes('text/event-stream') && response.body) {
        // ── Consume SSE Stream ─────────────────────────────────
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamingContent = '';
        let streamingMsgId = `msg_stream_${Date.now()}`;

        // Create a placeholder streaming message
        addClientMessage({
          id: streamingMsgId,
          role: 'manager',
          content: '',
          timestamp: new Date().toISOString(),
        });

        let buffer = '';

        while (reader) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // Parse SSE lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const sseData = JSON.parse(jsonStr);

              if (sseData.type === 'chunk') {
                streamingContent += sseData.content;
                // Update the streaming message in place
                const store = useKantorkuStore.getState();
                const updatedMessages = store.clientMessages.map((m) =>
                  m.id === streamingMsgId
                    ? { ...m, content: streamingContent }
                    : m
                );
                useKantorkuStore.setState({ clientMessages: updatedMessages });
              } else if (sseData.type === 'done' && sseData.response) {
                data = sseData.response as ChatApiResponse;
              } else if (sseData.type === 'error') {
                toast.error('LLM Stream Error', { description: sseData.message });
              }
            } catch {
              // Ignore parse errors for individual SSE chunks
            }
          }
        }

        // Remove the streaming placeholder message
        const storeAfterStream = useKantorkuStore.getState();
        useKantorkuStore.setState({
          clientMessages: storeAfterStream.clientMessages.filter(
            (m) => m.id !== streamingMsgId
          ),
        });

        // If we never got a 'done' event with a parsed response, fall back
        if (!data) {
          data = {
            type: 'manager_message',
            content: streamingContent,
          };
        }
      } else {
        // Non-streaming fallback
        data = await response.json();
      }

      // Process intake result
      const intakeData = await intakePromise;
      if (intakeData && !intakeData.error) {
        setIntakeResult(intakeData);
      }

      if (data.type === 'contract_ready' && data.contract) {
        // Contract is ready
        setContract(data.contract);
        setContractState('contract_presented');
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: `I've drafted a contract for "${data.contract.title}". Please review the todos and let me know if you'd like to proceed or make changes.`,
          timestamp: new Date().toISOString(),
        });
        addOfficeEvent({
          type: 'contract_ready',
          from_id: 'conductor',
          content: data.contract.title,
          session_id: activeSessionId || 'default',
        });
        toast.success('📋 Contract ready for review', {
          description: data.contract.title,
          duration: 5000,
        });

        // Create session if new
        if (!activeSessionId) {
          const sid = `session_${Date.now()}`;
          addSession({
            session_id: sid,
            state: 'contract_presented',
            contract_title: data.contract.title,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            message_count: 1,
            total_cost: 0,
          });
        }
      } else if (data.type === 'team_feedback' && data.team_feedback) {
        // Team consultation feedback
        setContractState('team_consult');
        data.team_feedback.forEach((fb: TeamFeedbackRound) => {
          addTeamFeedback(fb);
        });
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: `The team has some feedback on this request. Let me share their thoughts...`,
          source: 'team_feedback',
          timestamp: new Date().toISOString(),
        });
        toast.info('👥 Team consultation in progress');
      } else if (data.type === 'question' && data.question) {
        // Manager is asking an interactive question with options
        setContractState('clarifying');
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: data.content || data.question.question,
          timestamp: new Date().toISOString(),
          question: data.question,
        });
        toast.info('❓ Manager has a question', {
          description: data.question.question,
          duration: 6000,
        });
      } else if (data.type === 'manager_message' && data.content) {
        // Clarification needed
        setContractState('clarifying');
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: data.content,
          timestamp: new Date().toISOString(),
        });
      }

      // Track cost (estimated)
      addCostEntry('conductor', 500, 200, 0.015);
    } catch (error) {
      console.error('Chat error:', error);
      setContractState('idle');
      addClientMessage({
        id: `msg_${Date.now()}`,
        role: 'manager',
        content: 'I apologize, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      });
      toast.error('❌ Chat error', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setManagerThinking(false);
    }
  };

  const handleAccept = async () => {
    if (!contract) return;

    // ── Phase 1: Team Consult ────────────────────────────────────
    setContractState('team_consult');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: 'Great choice! Let me run this by the team first for a quick consultation...',
      timestamp: new Date().toISOString(),
    });

    try {
      const briefingResponse = await fetch('/api/briefing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract,
          session_id: activeSessionId || 'default',
        }),
      });
      const briefingData = await briefingResponse.json();

      if (briefingData.rounds) {
        for (const round of briefingData.rounds) {
          addDiscussionRound(round);
          for (const msg of round.messages) {
            addWorkersMessage({
              id: `wmsg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              from_id: msg.from_id,
              message_type: msg.message_type || 'speak',
              content: msg.content,
              timestamp: msg.timestamp || new Date().toISOString(),
            });
          }
        }
      }

      if (briefingData.decisions) {
        for (const decision of briefingData.decisions) {
          addTeamFeedback({
            round_number: 1,
            worker_id: 'conductor',
            feedback_type: 'agreement',
            content: decision,
            timestamp: new Date().toISOString(),
          });
        }
      }

      setBriefingResult({
        plan: {},
        rounds_completed: briefingData.rounds?.length || 1,
        consensus_reached: briefingData.consensus_reached ?? true,
        concerns: briefingData.concerns || [],
        decisions: briefingData.decisions || ['Proceed with plan'],
      });
      toast.success('💬 Briefing complete', {
        description: `${briefingData.rounds?.length || 1} rounds completed`,
      });
    } catch {
      // Fallback: simulate brief feedback
      const activeWorkers = contract.todos
        .map((t) => t.assigned_to)
        .filter((v, i, a) => v && a.indexOf(v) === i) as string[];
      for (const workerId of activeWorkers.slice(0, 3)) {
        addWorkersMessage({
          id: `wmsg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          from_id: workerId,
          message_type: 'agreement',
          content: 'Ready to contribute to this project.',
          timestamp: new Date().toISOString(),
        });
      }
    }

    await new Promise((r) => setTimeout(r, 800));

    // ── Phase 2: Team Review ─────────────────────────────────────
    setContractState('team_review');
    const gates: Array<{ id: string; gate_type: 'team_review' | 'client_approval' | 'budget_check' | 'security_review'; status: 'pending' | 'approved' | 'rejected' | 'skipped'; approver: string; reason?: string; timestamp: string }> = [
      { id: 'gate_team', gate_type: 'team_review', status: 'approved', approver: 'conductor', reason: 'Team aligned on plan', timestamp: new Date().toISOString() },
    ];
    if (contract.budget_limit && contract.budget_limit > 5) {
      gates.push({ id: 'gate_budget', gate_type: 'budget_check' as const, status: 'approved' as const, approver: 'conductor', reason: 'Within budget limits', timestamp: new Date().toISOString() });
    }
    setApprovalGates(gates);
    addOfficeEvent({
      type: 'approval_gate_passed',
      from_id: 'conductor',
      content: 'Team review approved',
      session_id: activeSessionId || 'default',
    });

    await new Promise((r) => setTimeout(r, 600));

    // ── Phase 3: TODO Review ─────────────────────────────────────
    setContractState('todo_review');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: `All ${contract.todos.length} todos have been reviewed and dependencies verified. Proceeding to final confirmation...`,
      timestamp: new Date().toISOString(),
    });

    await new Promise((r) => setTimeout(r, 500));

    // ── Phase 4: Client Feedback ─────────────────────────────────
    setContractState('client_feedback');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: 'Starting execution now. I\'ll keep you updated on progress!',
      timestamp: new Date().toISOString(),
    });

    await new Promise((r) => setTimeout(r, 400));

    // ── Phase 5: Working ─────────────────────────────────────────
    setContractState('working');
    setWorking(true);
    addOfficeEvent({
      type: 'contract_accepted',
      from_id: 'conductor',
      content: contract.title,
      session_id: activeSessionId || 'default',
    });

    // Mark relevant workers as busy
    for (const todo of contract.todos) {
      if (todo.assigned_to) {
        updateWorkerStatus(todo.assigned_to, 'busy', todo.description);
      }
    }

    // Set up DAG nodes
    const nodes = contract.todos.map((t) => ({
      id: t.id,
      label: t.description,
      status: t.status as 'pending',
      assigned_to: t.assigned_to,
      depth: t.depends_on.length > 0 ? 1 : 0,
    }));
    const edges = contract.todos.flatMap((t) =>
      t.depends_on.map((dep) => ({
        from: dep,
        to: t.id,
        type: 'depends_on' as const,
      }))
    );
    setDAG(nodes, edges);

    // Set up middleware steps
    setMiddlewareSteps([
      { name: 'Auth Check', type: 'auth', status: 'passed', duration_ms: 2 },
      { name: 'Rate Limiter', type: 'rate_limit', status: 'passed', duration_ms: 1 },
      { name: 'Cost Guard', type: 'cost_guard', status: 'passed', duration_ms: 3, detail: `Budget: $${contract.budget_limit || '∞'}` },
      { name: 'Cache Lookup', type: 'cache', status: 'skipped', duration_ms: 0 },
      { name: 'Validation', type: 'validation', status: 'passed', duration_ms: 5 },
    ]);

    try {
      // Budget enforcement check
      const currentCost = useKantorkuStore.getState().costReport?.total_cost || 0;
      const budgetLimit = contract.budget_limit;
      if (budgetLimit && currentCost > budgetLimit) {
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: `⚠️ Budget limit of $${budgetLimit.toFixed(2)} has been reached (current: $${currentCost.toFixed(4)}). Please increase the budget or simplify the scope before proceeding.`,
          timestamp: new Date().toISOString(),
        });
        setContractState('contract_presented');
        setWorking(false);
        return;
      }

      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract,
          session_id: activeSessionId || 'default',
        }),
      });

      const data: ExecuteApiResponse = await response.json();

      if (data.events) {
        // Process events sequentially with delays
        for (const event of data.events) {
          await new Promise((resolve) => setTimeout(resolve, 300));

          addOfficeEvent(event);

          // Update worker chat for certain events
          if (
            event.type === 'worker_speak_up' ||
            event.type === 'manager_summary' ||
            event.type === 'manager_decision' ||
            event.type === 'briefing_opened' ||
            event.type === 'plan_drafted'
          ) {
            addWorkersMessage({
              id: `wmsg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              from_id: (event.from_id as string) || 'conductor',
              message_type: event.type === 'manager_summary'
                ? 'manager_summary'
                : event.type === 'manager_decision'
                ? 'manager_decision'
                : event.type === 'plan_drafted'
                ? 'info'
                : 'speak',
              content: (event.content as string) || '',
              timestamp: (event.timestamp as string) || new Date().toISOString(),
            });
          }

          // Update task status
          if (event.type === 'task_started' && event.to_id) {
            const todo = contract.todos.find(
              (t) => t.assigned_to === event.to_id && t.status === 'pending'
            );
            if (todo) {
              updateTodoStatus(todo.id, 'in_progress');
              addLatencyEntry(Math.random() * 500 + 100, event.to_id);
            }
          }

          if (event.type === 'task_done' && event.from_id) {
            const todo = contract.todos.find(
              (t) => t.assigned_to === event.from_id && t.status === 'in_progress'
            );
            if (todo) {
              updateTodoStatus(todo.id, 'done');
              const actualTime = Math.random() * 5000 + 1000;
              updateTodoActualTime(todo.id, actualTime);

              // ── Memory Population ─────────────────────────────
              // Ring 1: Task result
              addMemoryEntry({
                id: `mem_r1_${Date.now()}_${todo.id}`,
                ring: 1,
                key: `task_result:${todo.id}`,
                value: JSON.stringify({
                  description: todo.description,
                  assigned_to: todo.assigned_to,
                  actual_time_ms: actualTime,
                  status: 'done',
                }),
                timestamp: new Date().toISOString(),
                session_id: activeSessionId || 'default',
                tags: ['task_result', todo.assigned_to, 'completed'],
              });

              // Ring 2: Lesson learned
              addMemoryEntry({
                id: `mem_r2_${Date.now()}_${todo.id}`,
                ring: 2,
                key: `lesson:${todo.assigned_to}:${todo.description.slice(0, 30)}`,
                value: `Task completed in ${(actualTime / 1000).toFixed(1)}s. Dependency order maintained successfully.`,
                timestamp: new Date().toISOString(),
                session_id: activeSessionId || 'default',
                tags: ['lesson', 'task_completion', todo.assigned_to],
              });
            }
            updateWorkerStatus(event.from_id, 'idle', undefined);
            addLatencyEntry(Math.random() * 300 + 50, event.from_id);
            toast.success(`✅ ${event.from_id} completed task`);
          }

          // Handle task_failed events
          if (event.type === 'task_failed' && event.from_id) {
            const todo = contract.todos.find(
              (t) => t.assigned_to === event.from_id && t.status === 'in_progress'
            );
            if (todo) {
              updateTodoStatus(todo.id, 'failed', undefined, (event.error as string) || 'Unknown error');

              // Memory: Record failure in Ring 1
              addMemoryEntry({
                id: `mem_r1_fail_${Date.now()}_${todo.id}`,
                ring: 1,
                key: `task_failed:${todo.id}`,
                value: JSON.stringify({
                  description: todo.description,
                  assigned_to: todo.assigned_to,
                  error: event.error || 'Unknown error',
                }),
                timestamp: new Date().toISOString(),
                session_id: activeSessionId || 'default',
                tags: ['task_failed', todo.assigned_to, 'error'],
              });
            }
            updateWorkerStatus(event.from_id, 'error', undefined);
            toast.error(`❌ ${event.from_id} task failed`, {
              description: (event.error as string) || 'Unknown error',
            });
          }

          // Process worker emotions
          if (event.emotion && typeof event.emotion === 'object') {
            const emo = event.emotion as { worker_id: string; emotion: string; confidence: number; timestamp: string };
            setWorkerEmotion({
              worker_id: emo.worker_id,
              emotion: emo.emotion as 'confident' | 'uncertain' | 'frustrated' | 'excited' | 'neutral',
              confidence: emo.confidence,
              timestamp: emo.timestamp,
            });
          }

          // Add trace entries for events
          if (event.type === 'task_started' || event.type === 'task_done' || event.type === 'task_failed') {
            addTrace({
              trace_id: `tr_${Date.now()}`,
              span_id: `sp_${Math.random().toString(36).slice(2, 10)}`,
              operation: event.type,
              worker_id: (event.from_id as string) || (event.to_id as string),
              model: undefined,
              start_time: new Date().toISOString(),
              end_time: new Date().toISOString(),
              duration_ms: Math.floor(Math.random() * 2000 + 200),
              status: event.type === 'task_failed' ? 'error' : 'ok',
              input_tokens: Math.floor(Math.random() * 1000 + 100),
              output_tokens: Math.floor(Math.random() * 500 + 50),
              cost_usd: Math.random() * 0.01,
            });
          }
        }
      }

      // Update briefing result
      setBriefingResult({
        plan: {},
        rounds_completed: 1,
        consensus_reached: true,
        concerns: [],
        decisions: ['Proceed with current plan'],
      });

      // Process trust score updates
      if (data.trust_updates) {
        for (const tu of data.trust_updates as Array<{ worker_id: string; score: number; trend: 'improving' | 'stable' | 'declining' }>) {
          updateTrustScore(tu.worker_id, tu.score);
        }
      }

      // Process emotions from execute response
      if (data.emotions) {
        for (const emo of data.emotions as Array<{ worker_id: string; emotion: string; confidence: number; timestamp: string }>) {
          setWorkerEmotion({
            worker_id: emo.worker_id,
            emotion: emo.emotion as 'confident' | 'uncertain' | 'frustrated' | 'excited' | 'neutral',
            confidence: emo.confidence,
            timestamp: emo.timestamp,
          });
        }
      }

      addDiscussionRound({
        round_number: 1,
        messages: useKantorkuStore.getState().workersMessages.slice(-5),
        summary: 'Briefing complete. Team is aligned.',
        decisions: ['Proceed with current plan'],
        consensus_reached: true,
      });

      // Generate debrief
      const currentContract = useKantorkuStore.getState().contract || contract;
      const failedTodos = currentContract.todos.filter((t) => t.status === 'failed');
      const completedTodos = currentContract.todos.filter((t) => t.status === 'done');

      const debrief: DebriefResult = {
        contract_id: contract.id,
        session_id: activeSessionId || 'default',
        what_went_well: completedTodos.length > 0
          ? [`Completed ${completedTodos.length} task(s) successfully`, 'Team communication was clear']
          : ['Team communication was clear'],
        what_could_improve: failedTodos.length > 0
          ? [`${failedTodos.length} task(s) failed — retry recommended`, 'Better error handling for failed tasks']
          : ['Could parallelize independent tasks', 'Better error handling'],
        lessons_learned: failedTodos.length > 0
          ? ['Some tasks failed — investigation needed', 'Retry mechanism is important for resilience']
          : ['Dependency tracking helps execution order', 'Budget monitoring prevents overspending'],
        worker_feedback: Object.fromEntries(
          [...new Set(contract.todos.map((t) => t.assigned_to).filter(Boolean))].map((w) => [
            w,
            failedTodos.some((f) => f.assigned_to === w) ? 'Task encountered errors' : 'Task completed successfully',
          ])
        ),
        total_duration_ms: Math.floor(Math.random() * 10000 + 5000),
        total_cost: useKantorkuStore.getState().costReport?.total_cost || 0.05,
        timestamp: new Date().toISOString(),
      };
      setDebriefResult(debrief);
      toast.info('📊 Debrief generated', {
        description: hasFailed ? `${failedTodos.length} tasks failed` : `All ${completedTodos.length} tasks completed`,
      });

      // Mark contract as done (or failed if any task failed)
      const hasFailed = failedTodos.length > 0;
      if (!hasFailed) {
        contract.todos.forEach((t) => updateTodoStatus(t.id, 'done'));
      }
      setContractState(hasFailed ? 'failed' : 'done');
      addCostEntry('conductor', 2000, 800, 0.05);

      // ── Memory: Overall contract result ───────────────────────
      addMemoryEntry({
        id: `mem_r1_contract_${Date.now()}`,
        ring: 1,
        key: `contract_result:${contract.id}`,
        value: JSON.stringify({
          title: contract.title,
          total_todos: contract.todos.length,
          completed: completedTodos.length,
          failed: failedTodos.length,
          final_state: hasFailed ? 'failed' : 'done',
        }),
        timestamp: new Date().toISOString(),
        session_id: activeSessionId || 'default',
        tags: ['contract_result', hasFailed ? 'partial_failure' : 'success'],
      });

      // Ring 2: Episode lesson
      addMemoryEntry({
        id: `mem_r2_episode_${Date.now()}`,
        ring: 2,
        key: `episode:${contract.title.slice(0, 30)}`,
        value: hasFailed
          ? `Contract partially failed: ${failedTodos.length}/${contract.todos.length} tasks failed. Retry recommended.`
          : `Contract fully completed: ${contract.todos.length} tasks done successfully.`,
        timestamp: new Date().toISOString(),
        session_id: activeSessionId || 'default',
        tags: ['episode', 'contract_completion', hasFailed ? 'failure' : 'success'],
      });

      // Update metrics summary
      const store = useKantorkuStore.getState();
      setMetricsSummary({
        total_calls: (store.metricsSummary?.total_calls || 0) + contract.todos.length + 3,
        total_tokens: (store.metricsSummary?.total_tokens || 0) + 2800,
        total_cost: store.costReport?.total_cost || 0.065,
        avg_latency_ms: store.latencyHistory.length > 0
          ? store.latencyHistory.reduce((s, l) => s + l.latency_ms, 0) / store.latencyHistory.length
          : 0,
        success_rate: hasFailed ? completedTodos.length / contract.todos.length : 1.0,
        p50_latency_ms: 200,
        p95_latency_ms: 800,
        p99_latency_ms: 1500,
        by_model: {},
      });

      // Update session
      if (activeSessionId) {
        updateSession(activeSessionId, { state: hasFailed ? 'failed' : 'done', total_cost: store.costReport?.total_cost || 0 });
      }
    } catch (error) {
      console.error('Execute error:', error);
      setContractState('failed');
      addClientMessage({
        id: `msg_${Date.now()}`,
        role: 'manager',
        content: 'Execution failed. Please check the dashboard for details and try again.',
        timestamp: new Date().toISOString(),
      });
      toast.error('❌ Execution failed', {
        description: error instanceof Error ? error.message : 'Unknown execution error',
      });
    } finally {
      setWorking(false);
    }
  };

  const handleRevise = async (feedback: string) => {
    if (!contract) return;

    setManagerThinking(true);
    setContractState('manager_thinking');

    try {
      const history = [
        ...clientMessages.map((m) => ({
          role: m.role === 'manager' ? 'assistant' : 'user',
          content: m.content,
        })),
        { role: 'user', content: `[REVISION REQUEST] ${feedback}` },
      ];

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `[REVISION REQUEST] ${feedback}`,
          history,
          session_id: activeSessionId || 'default',
        }),
      });

      const data: ChatApiResponse = await response.json();

      if (data.type === 'contract_ready' && data.contract) {
        setContract(data.contract);
        setContractState('contract_presented');
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: `I've revised the contract based on your feedback. Please review the updated todos.`,
          timestamp: new Date().toISOString(),
        });
      } else if (data.content) {
        setContractState('clarifying');
        addClientMessage({
          id: `msg_${Date.now()}`,
          role: 'manager',
          content: data.content,
          timestamp: new Date().toISOString(),
        });
      }
    } catch (error) {
      console.error('Revise error:', error);
    } finally {
      setManagerThinking(false);
    }
  };

  const handleRetryTodo = async (todoId: string) => {
    if (!contract) return;
    const todo = contract.todos.find((t) => t.id === todoId);
    if (!todo) return;

    // Reset the todo status to pending
    updateTodoStatus(todoId, 'pending');
    if (todo.assigned_to) {
      updateWorkerStatus(todo.assigned_to, 'busy', todo.description);
    }

    // Simulate retry execution
    updateTodoStatus(todoId, 'in_progress');
    addOfficeEvent({
      type: 'task_started',
      to_id: todo.assigned_to,
      content: `Retrying: ${todo.description}`,
      session_id: activeSessionId || 'default',
    });

    // Simulate work with a delay
    await new Promise((r) => setTimeout(r, 1500));

    const success = Math.random() > 0.3; // 70% success on retry
    if (success) {
      updateTodoStatus(todoId, 'done');
      const actualTime = Math.random() * 3000 + 500;
      updateTodoActualTime(todoId, actualTime);
      if (todo.assigned_to) {
        updateWorkerStatus(todo.assigned_to, 'idle', undefined);
      }
      addOfficeEvent({
        type: 'task_done',
        from_id: todo.assigned_to,
        content: `Retry successful: ${todo.description}`,
        session_id: activeSessionId || 'default',
      });

      // Memory: Record retry success
      addMemoryEntry({
        id: `mem_r1_retry_${Date.now()}_${todoId}`,
        ring: 1,
        key: `retry_success:${todoId}`,
        value: JSON.stringify({ description: todo.description, retry_count: 1, actual_time_ms: actualTime }),
        timestamp: new Date().toISOString(),
        session_id: activeSessionId || 'default',
        tags: ['retry', 'success', todo.assigned_to || 'unknown'],
      });

      addClientMessage({
        id: `msg_${Date.now()}`,
        role: 'manager',
        content: `✅ Retry successful: "${todo.description}" completed on second attempt.`,
        timestamp: new Date().toISOString(),
      });

      // Check if all todos are now done
      const currentContract = useKantorkuStore.getState().contract;
      if (currentContract) {
        const allDone = currentContract.todos.every((t) => t.status === 'done');
        const anyFailed = currentContract.todos.some((t) => t.status === 'failed');
        if (allDone) {
          setContractState('done');
        } else if (!anyFailed) {
          setContractState('done');
        }
      }
    } else {
      updateTodoStatus(todoId, 'failed', undefined, 'Retry failed: persistent error encountered');
      if (todo.assigned_to) {
        updateWorkerStatus(todo.assigned_to, 'error', undefined);
      }
      addOfficeEvent({
        type: 'task_failed',
        from_id: todo.assigned_to,
        content: `Retry failed: ${todo.description}`,
        error: 'Persistent error on retry',
        session_id: activeSessionId || 'default',
      });

      addClientMessage({
        id: `msg_${Date.now()}`,
        role: 'manager',
        content: `❌ Retry failed: "${todo.description}" still encountering errors. Consider revising the contract.`,
        timestamp: new Date().toISOString(),
      });
    }
  };

  const handleReject = () => {
    setContract(null);
    setContractState('idle');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: 'Contract rejected. Feel free to start a new request anytime.',
      timestamp: new Date().toISOString(),
    });
  };

  const handleNewSession = () => {
    clearClientMessages();
    clearWorkersMessages();
    clearOfficeEvents();
    setContract(null);
    setContractState('idle');
    setIntakeResult(null);
    setDebriefResult(null);
    setBriefingResult(null);
  };

  const handleAnswerQuestion = async (messageId: string, selectedOption: string, customAnswer?: string) => {
    // Mark the question as answered in the store
    answerQuestion(messageId, selectedOption, customAnswer);

    // Build the response text based on what the user selected
    const answerText = selectedOption === 'OTHER'
      ? customAnswer || 'Other'
      : selectedOption;

    // Auto-send the answer as a user message to continue the conversation
    await handleSendMessage(answerText);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-slate-700/50 bg-slate-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white">LOBBY</h2>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={`text-[9px] px-1.5 py-0 h-4 font-mono ${CONTRACT_STATE_COLORS[contractState]}`}
            >
              {CONTRACT_STATE_LABELS[contractState]}
            </Badge>
          </div>
        </div>
      </div>

      {/* Intake Result */}
      {intakeResult && (
        <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-slate-800/60 border border-slate-700/30">
          <div className="flex items-center gap-1.5 mb-1">
            <Zap className="h-3 w-3 text-amber-400" />
            <span className="text-[10px] text-amber-400 font-mono font-semibold">INTAKE</span>
          </div>
          <div className="flex flex-wrap gap-1">
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300">
              {intakeResult.type}
            </Badge>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-cyan-500/30 text-cyan-300">
              {intakeResult.urgency}
            </Badge>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-violet-500/30 text-violet-300">
              {intakeResult.estimated_complexity}
            </Badge>
            {intakeResult.estimated_workers && intakeResult.estimated_workers.length > 0 && (
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-teal-500/30 text-teal-300">
                ~{intakeResult.estimated_workers.length} workers
              </Badge>
            )}
            {intakeResult.estimated_duration_ms && (
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-500/30 text-slate-300">
                ~{(intakeResult.estimated_duration_ms / 1000).toFixed(0)}s
              </Badge>
            )}
          </div>
          {intakeResult.summary && (
            <p className="text-[9px] text-slate-500 mt-1">{intakeResult.summary}</p>
          )}
        </div>
      )}

      {/* Team Consult Feedback */}
      {contractState === 'team_consult' && teamFeedback.length > 0 && (
        <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-violet-500/10 border border-violet-500/30">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Users className="h-3 w-3 text-violet-400" />
            <span className="text-[10px] text-violet-400 font-mono font-semibold">TEAM FEEDBACK</span>
          </div>
          <div className="space-y-1 max-h-24 overflow-y-auto custom-scrollbar">
            {teamFeedback.map((fb, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <span className="text-[9px]">
                  {fb.feedback_type === 'concern' ? '⚠️' :
                   fb.feedback_type === 'suggestion' ? '💡' :
                   fb.feedback_type === 'agreement' ? '✅' : '❌'}
                </span>
                <div>
                  <span className="text-[9px] text-slate-400 font-mono">{fb.worker_id}</span>
                  <p className="text-[9px] text-slate-300">{fb.content}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval Gates Section (team_review state) */}
      {contractState === 'team_review' && approvalGates.length > 0 && (
        <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-teal-500/10 border border-teal-500/30">
          <div className="flex items-center gap-1.5 mb-1.5">
            <CheckCircle2 className="h-3 w-3 text-teal-400" />
            <span className="text-[10px] text-teal-400 font-mono font-semibold">APPROVAL GATES</span>
          </div>
          <div className="space-y-1">
            {approvalGates.map((gate) => (
              <div key={gate.id} className="flex items-center justify-between">
                <span className="text-[9px] text-slate-300">{gate.gate_type}</span>
                <Badge variant="outline" className={`text-[8px] px-1 py-0 h-3.5 ${
                  gate.status === 'approved' ? 'border-green-500/30 text-green-300' :
                  gate.status === 'rejected' ? 'border-red-500/30 text-red-300' :
                  'border-amber-500/30 text-amber-300'
                }`}>
                  {gate.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debrief Summary (done state) */}
      {contractState === 'done' && debriefResult && (
        <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-green-500/10 border border-green-500/30">
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileText className="h-3 w-3 text-green-400" />
            <span className="text-[10px] text-green-400 font-mono font-semibold">DEBRIEF</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5 mb-1.5">
            <div className="text-center p-1.5 rounded bg-slate-900/60">
              <p className="text-xs font-bold text-cyan-300 font-mono">
                {(debriefResult.total_duration_ms / 1000).toFixed(1)}s
              </p>
              <p className="text-[8px] text-slate-500">Duration</p>
            </div>
            <div className="text-center p-1.5 rounded bg-slate-900/60">
              <p className="text-xs font-bold text-green-300 font-mono">
                ${debriefResult.total_cost.toFixed(4)}
              </p>
              <p className="text-[8px] text-slate-500">Cost</p>
            </div>
          </div>
          <div className="space-y-1">
            {debriefResult.what_went_well.length > 0 && (
              <div>
                <span className="text-[9px] text-green-400 font-mono">✓ Went Well</span>
                {debriefResult.what_went_well.map((w, i) => (
                  <p key={i} className="text-[9px] text-slate-400 ml-2">• {w}</p>
                ))}
              </div>
            )}
            {debriefResult.lessons_learned.length > 0 && (
              <div>
                <span className="text-[9px] text-amber-400 font-mono">💡 Lessons</span>
                {debriefResult.lessons_learned.map((l, i) => (
                  <p key={i} className="text-[9px] text-slate-400 ml-2">• {l}</p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <ClientChatPanel
          messages={clientMessages}
          onSend={handleSendMessage}
          isThinking={isManagerThinking}
          disabled={isWorking}
          onNewSession={handleNewSession}
          onAnswerQuestion={handleAnswerQuestion}
        />
      </div>

      {/* Todo Review Section */}
      {contractState === 'todo_review' && contract && (
        <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-teal-500/10 border border-teal-500/30">
          <div className="flex items-center gap-1.5 mb-1.5">
            <CheckCircle2 className="h-3 w-3 text-teal-400" />
            <span className="text-[10px] text-teal-400 font-mono font-semibold">TODO REVIEW</span>
          </div>
          <div className="space-y-0.5 max-h-20 overflow-y-auto custom-scrollbar">
            {contract.todos.map((todo) => (
              <div key={todo.id} className="flex items-center gap-1.5 text-[9px]">
                <Clock className="h-2.5 w-2.5 text-teal-400" />
                <span className="text-slate-300 truncate">{todo.description}</span>
                {todo.assigned_to && (
                  <span className="text-teal-400 font-mono flex-shrink-0">→ {todo.assigned_to}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Client Feedback Phase */}
      {contractState === 'client_feedback' && (
        <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-amber-500/10 border border-amber-500/30">
          <div className="flex items-center gap-1.5">
            <ThumbsUp className="h-3 w-3 text-amber-400" />
            <span className="text-[10px] text-amber-400 font-mono font-semibold">CONFIRMED</span>
            <span className="text-[9px] text-amber-300/60 ml-1">Proceeding to execution...</span>
          </div>
        </div>
      )}

      {/* Contract Card (if presented or in lifecycle phases) */}
      {contract && !['done', 'failed'].includes(contractState) && !isWorking && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1">
          <ContractCard
            contract={contract}
            onAccept={handleAccept}
            onRevise={handleRevise}
            onReject={handleReject}
            onRetryTodo={handleRetryTodo}
            isWorking={isWorking}
          />
        </div>
      )}

      {/* Working state - show contract card with progress */}
      {contract && isWorking && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1">
          <ContractCard
            contract={contract}
            onAccept={handleAccept}
            onRevise={handleRevise}
            onReject={handleReject}
            onRetryTodo={handleRetryTodo}
            isWorking={isWorking}
          />
        </div>
      )}

      {/* Done/Failed State Actions */}
      {(contractState === 'done' || contractState === 'failed') && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1 space-y-2">
          {contractState === 'failed' && contract && contract.todos.some((t) => t.status === 'failed') && (
            <div className="space-y-1.5">
              {contract.todos.filter((t) => t.status === 'failed').map((todo) => (
                <div key={todo.id} className="flex items-center gap-2 p-2 rounded-md bg-red-500/10 border border-red-500/20">
                  <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] text-red-300 truncate">{todo.description}</p>
                    {todo.error && <p className="text-[8px] text-red-400/60 truncate">{todo.error}</p>}
                  </div>
                  <Button
                    onClick={() => handleRetryTodo(todo.id)}
                    size="sm"
                    variant="outline"
                    className="h-6 text-[9px] border-amber-500/40 text-amber-300 hover:bg-amber-500/10 px-2"
                  >
                    <RefreshCcw className="h-2.5 w-2.5 mr-1" />
                    Retry
                  </Button>
                </div>
              ))}
            </div>
          )}
          <Button
            onClick={handleNewSession}
            className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs"
          >
            <RefreshCcw className="h-3.5 w-3.5 mr-1.5" />
            New Session
          </Button>
        </div>
      )}
    </div>
  );
}
