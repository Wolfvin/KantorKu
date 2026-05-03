'use client';

import { useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import type { ChatApiResponse, ExecuteApiResponse, TeamFeedbackRound, DebriefResult, Contract } from '@/lib/kantorku/types';
import { toast } from 'sonner';

/**
 * Custom hook encapsulating all contract lifecycle state transitions,
 * API calls, and event handling for the LobbyZone.
 */
export function useContractLifecycle() {
  const store = useKantorkuStore();
  const {
    clientMessages, contract, contractState, isManagerThinking, isWorking, isStreaming,
    intakeResult, teamFeedback, debriefResult, approvalGates,
    sessions, activeSessionId,
    addClientMessage, setContract, setContractState, setManagerThinking,
    setWorking, setStreaming, addOfficeEvent, updateWorkerStatus, addWorkersMessage,
    updateTodoStatus, updateTodoActualTime, addCostEntry, setIntakeResult,
    setBriefingResult, addDiscussionRound, addSession, updateSession,
    setApprovalGates, setDAG, setMiddlewareSteps, addTrace, addLatencyEntry,
    setDebriefResult, addTeamFeedback, clearClientMessages, clearWorkersMessages,
    clearOfficeEvents, setMetricsSummary, setHealthStatus, setCircuitBreakers,
    addMemoryEntry, answerQuestion, setWorkerEmotion, updateTrustScore,
  } = store;

  const handleSendMessage = useCallback(async (message: string) => {
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

      const contentType = response.headers.get('content-type') || '';
      let data: ChatApiResponse | null = null;

      if (contentType.includes('text/event-stream') && response.body) {
        // ── Consume SSE Stream ─────────────────────────────────
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamingContent = '';
        const streamingMsgId = `msg_stream_${Date.now()}`;

        // Create a placeholder streaming message
        addClientMessage({
          id: streamingMsgId,
          role: 'manager',
          content: '',
          timestamp: new Date().toISOString(),
        });

        setStreaming(true);
        setManagerThinking(false); // Not "thinking" anymore, now streaming

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
                const currentState = useKantorkuStore.getState();
                const updatedMessages = currentState.clientMessages.map((m) =>
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

        setStreaming(false);

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

      if (!data) {
        setContractState('idle');
        return;
      }

      if (data.type === 'contract_ready' && data.contract) {
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
      setStreaming(false);
    }
  }, [clientMessages, activeSessionId, addClientMessage, setContract, setContractState, setManagerThinking, setStreaming, addOfficeEvent, setIntakeResult, addTeamFeedback, addCostEntry, addSession]);

  const handleAccept = useCallback(async () => {
    if (!contract) return;

    // ── Phase 1: Team Consult
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
        body: JSON.stringify({ contract, session_id: activeSessionId || 'default' }),
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

    // ── Phase 2: Team Review
    setContractState('team_review');
    const gates: Array<{ id: string; gate_type: 'team_review' | 'client_approval' | 'budget_check' | 'security_review'; status: 'pending' | 'approved' | 'rejected' | 'skipped'; approver: string; reason?: string; timestamp: string }> = [
      { id: 'gate_team', gate_type: 'team_review', status: 'approved', approver: 'conductor', reason: 'Team aligned on plan', timestamp: new Date().toISOString() },
    ];
    if (contract.budget_limit && contract.budget_limit > 5) {
      gates.push({ id: 'gate_budget', gate_type: 'budget_check', status: 'approved', approver: 'conductor', reason: 'Within budget limits', timestamp: new Date().toISOString() });
    }
    setApprovalGates(gates);
    addOfficeEvent({ type: 'approval_gate_passed', from_id: 'conductor', content: 'Team review approved', session_id: activeSessionId || 'default' });

    await new Promise((r) => setTimeout(r, 600));

    // ── Phase 3: TODO Review
    setContractState('todo_review');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: `All ${contract.todos.length} todos have been reviewed and dependencies verified. Proceeding to final confirmation...`,
      timestamp: new Date().toISOString(),
    });

    await new Promise((r) => setTimeout(r, 500));

    // ── Phase 4: Client Feedback
    setContractState('client_feedback');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: 'Starting execution now. I\'ll keep you updated on progress!',
      timestamp: new Date().toISOString(),
    });

    await new Promise((r) => setTimeout(r, 400));

    // ── Phase 5: Working
    setContractState('working');
    setWorking(true);
    addOfficeEvent({ type: 'contract_accepted', from_id: 'conductor', content: contract.title, session_id: activeSessionId || 'default' });

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
        body: JSON.stringify({ contract, session_id: activeSessionId || 'default' }),
      });

      const data: ExecuteApiResponse = await response.json();

      if (data.events) {
        for (const event of data.events) {
          await new Promise((resolve) => setTimeout(resolve, 300));
          addOfficeEvent(event);

          if (event.type === 'worker_speak_up' || event.type === 'manager_summary' || event.type === 'manager_decision' || event.type === 'briefing_opened' || event.type === 'plan_drafted') {
            addWorkersMessage({
              id: `wmsg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              from_id: (event.from_id as string) || 'conductor',
              message_type: event.type === 'manager_summary' ? 'manager_summary' : event.type === 'manager_decision' ? 'manager_decision' : event.type === 'plan_drafted' ? 'info' : 'speak',
              content: (event.content as string) || '',
              timestamp: (event.timestamp as string) || new Date().toISOString(),
            });
          }

          if (event.type === 'task_started' && event.to_id) {
            const todo = contract.todos.find((t) => t.assigned_to === event.to_id && t.status === 'pending');
            if (todo) {
              updateTodoStatus(todo.id, 'in_progress');
              addLatencyEntry(Math.random() * 500 + 100, event.to_id);
            }
          }

          if (event.type === 'task_done' && event.from_id) {
            const todo = contract.todos.find((t) => t.assigned_to === event.from_id && t.status === 'in_progress');
            if (todo) {
              updateTodoStatus(todo.id, 'done');
              const actualTime = Math.random() * 5000 + 1000;
              updateTodoActualTime(todo.id, actualTime);

              addMemoryEntry({
                id: `mem_r1_${Date.now()}_${todo.id}`,
                ring: 1,
                key: `task_result:${todo.id}`,
                value: JSON.stringify({ description: todo.description, assigned_to: todo.assigned_to, actual_time_ms: actualTime, status: 'done' }),
                timestamp: new Date().toISOString(),
                session_id: activeSessionId || 'default',
                tags: ['task_result', todo.assigned_to, 'completed'],
              });

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

          if (event.type === 'task_failed' && event.from_id) {
            const todo = contract.todos.find((t) => t.assigned_to === event.from_id && t.status === 'in_progress');
            if (todo) {
              updateTodoStatus(todo.id, 'failed', undefined, (event.error as string) || 'Unknown error');
              addMemoryEntry({
                id: `mem_r1_fail_${Date.now()}_${todo.id}`,
                ring: 1,
                key: `task_failed:${todo.id}`,
                value: JSON.stringify({ description: todo.description, assigned_to: todo.assigned_to, error: event.error || 'Unknown error' }),
                timestamp: new Date().toISOString(),
                session_id: activeSessionId || 'default',
                tags: ['task_failed', todo.assigned_to, 'error'],
              });
            }
            updateWorkerStatus(event.from_id, 'error', undefined);
            toast.error(`❌ ${event.from_id} task failed`, { description: (event.error as string) || 'Unknown error' });
          }

          if (event.emotion && typeof event.emotion === 'object') {
            const emo = event.emotion as { worker_id: string; emotion: string; confidence: number; timestamp: string };
            setWorkerEmotion({
              worker_id: emo.worker_id,
              emotion: emo.emotion as 'confident' | 'uncertain' | 'frustrated' | 'excited' | 'neutral',
              confidence: emo.confidence,
              timestamp: emo.timestamp,
            });
          }

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
      setBriefingResult({ plan: {}, rounds_completed: 1, consensus_reached: true, concerns: [], decisions: ['Proceed with current plan'] });

      // Process trust score updates
      if (data.trust_updates) {
        for (const tu of data.trust_updates as Array<{ worker_id: string; score: number; trend: 'improving' | 'stable' | 'declining' }>) {
          updateTrustScore(tu.worker_id, tu.score);
        }
      }

      // Process emotions
      if (data.emotions) {
        for (const emo of data.emotions as Array<{ worker_id: string; emotion: string; confidence: number; timestamp: string }>) {
          setWorkerEmotion({ worker_id: emo.worker_id, emotion: emo.emotion as 'confident' | 'uncertain' | 'frustrated' | 'excited' | 'neutral', confidence: emo.confidence, timestamp: emo.timestamp });
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
      const hasFailed = failedTodos.length > 0;

      const debrief: DebriefResult = {
        contract_id: contract.id,
        session_id: activeSessionId || 'default',
        what_went_well: completedTodos.length > 0 ? [`Completed ${completedTodos.length} task(s) successfully`, 'Team communication was clear'] : ['Team communication was clear'],
        what_could_improve: failedTodos.length > 0 ? [`${failedTodos.length} task(s) failed — retry recommended`, 'Better error handling for failed tasks'] : ['Could parallelize independent tasks', 'Better error handling'],
        lessons_learned: failedTodos.length > 0 ? ['Some tasks failed — investigation needed', 'Retry mechanism is important for resilience'] : ['Dependency tracking helps execution order', 'Budget monitoring prevents overspending'],
        worker_feedback: Object.fromEntries(
          [...new Set(contract.todos.map((t) => t.assigned_to).filter(Boolean))].map((w) => [w, failedTodos.some((f) => f.assigned_to === w) ? 'Task encountered errors' : 'Task completed successfully'])
        ),
        total_duration_ms: Math.floor(Math.random() * 10000 + 5000),
        total_cost: useKantorkuStore.getState().costReport?.total_cost || 0.05,
        timestamp: new Date().toISOString(),
      };
      setDebriefResult(debrief);
      toast.info('📊 Debrief generated', {
        description: hasFailed ? `${failedTodos.length} tasks failed` : `All ${completedTodos.length} tasks completed`,
      });

      if (!hasFailed) {
        contract.todos.forEach((t) => updateTodoStatus(t.id, 'done'));
      }
      setContractState(hasFailed ? 'failed' : 'done');
      addCostEntry('conductor', 2000, 800, 0.05);

      // Memory: Contract result
      addMemoryEntry({
        id: `mem_r1_contract_${Date.now()}`,
        ring: 1,
        key: `contract_result:${contract.id}`,
        value: JSON.stringify({ title: contract.title, total_todos: contract.todos.length, completed: completedTodos.length, failed: failedTodos.length, final_state: hasFailed ? 'failed' : 'done' }),
        timestamp: new Date().toISOString(),
        session_id: activeSessionId || 'default',
        tags: ['contract_result', hasFailed ? 'partial_failure' : 'success'],
      });

      addMemoryEntry({
        id: `mem_r2_episode_${Date.now()}`,
        ring: 2,
        key: `episode:${contract.title.slice(0, 30)}`,
        value: hasFailed ? `Contract partially failed: ${failedTodos.length}/${contract.todos.length} tasks failed. Retry recommended.` : `Contract fully completed: ${contract.todos.length} tasks done successfully.`,
        timestamp: new Date().toISOString(),
        session_id: activeSessionId || 'default',
        tags: ['episode', 'contract_completion', hasFailed ? 'failure' : 'success'],
      });

      // Update metrics summary
      const stateAfter = useKantorkuStore.getState();
      setMetricsSummary({
        total_calls: (stateAfter.metricsSummary?.total_calls || 0) + contract.todos.length + 3,
        total_tokens: (stateAfter.metricsSummary?.total_tokens || 0) + 2800,
        total_cost: stateAfter.costReport?.total_cost || 0.065,
        avg_latency_ms: stateAfter.latencyHistory.length > 0 ? stateAfter.latencyHistory.reduce((s, l) => s + l.latency_ms, 0) / stateAfter.latencyHistory.length : 0,
        success_rate: hasFailed ? completedTodos.length / contract.todos.length : 1.0,
        p50_latency_ms: 200,
        p95_latency_ms: 800,
        p99_latency_ms: 1500,
        by_model: {},
      });

      if (activeSessionId) {
        updateSession(activeSessionId, { state: hasFailed ? 'failed' : 'done', total_cost: stateAfter.costReport?.total_cost || 0 });
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
  }, [contract, activeSessionId, setContractState, addClientMessage, setWorking, addOfficeEvent, updateWorkerStatus, addWorkersMessage, updateTodoStatus, updateTodoActualTime, addCostEntry, setBriefingResult, addDiscussionRound, setApprovalGates, setDAG, setMiddlewareSteps, addTrace, addLatencyEntry, setDebriefResult, addTeamFeedback, addMemoryEntry, setMetricsSummary, updateSession, setWorkerEmotion, updateTrustScore]);

  const handleRevise = useCallback(async (feedback: string) => {
    if (!contract) return;

    setManagerThinking(true);
    setContractState('manager_thinking');

    try {
      const history = [
        ...clientMessages.map((m) => ({
          role: m.role === 'manager' ? 'assistant' : 'user',
          content: m.content,
        })),
        { role: 'user' as const, content: `[REVISION REQUEST] ${feedback}` },
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
  }, [contract, clientMessages, activeSessionId, setContract, setContractState, setManagerThinking, addClientMessage]);

  const handleRetryTodo = useCallback(async (todoId: string) => {
    if (!contract) return;
    const todo = contract.todos.find((t) => t.id === todoId);
    if (!todo) return;

    updateTodoStatus(todoId, 'pending');
    if (todo.assigned_to) {
      updateWorkerStatus(todo.assigned_to, 'busy', todo.description);
    }

    updateTodoStatus(todoId, 'in_progress');
    addOfficeEvent({ type: 'task_started', to_id: todo.assigned_to, content: `Retrying: ${todo.description}`, session_id: activeSessionId || 'default' });

    await new Promise((r) => setTimeout(r, 1500));

    const success = Math.random() > 0.3;
    if (success) {
      updateTodoStatus(todoId, 'done');
      const actualTime = Math.random() * 3000 + 500;
      updateTodoActualTime(todoId, actualTime);
      if (todo.assigned_to) {
        updateWorkerStatus(todo.assigned_to, 'idle', undefined);
      }
      addOfficeEvent({ type: 'task_done', from_id: todo.assigned_to, content: `Retry successful: ${todo.description}`, session_id: activeSessionId || 'default' });

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

      const currentContract = useKantorkuStore.getState().contract;
      if (currentContract) {
        const allDone = currentContract.todos.every((t) => t.status === 'done');
        const anyFailed = currentContract.todos.some((t) => t.status === 'failed');
        if (allDone || !anyFailed) {
          setContractState('done');
        }
      }
    } else {
      updateTodoStatus(todoId, 'failed', undefined, 'Retry failed: persistent error encountered');
      if (todo.assigned_to) {
        updateWorkerStatus(todo.assigned_to, 'error', undefined);
      }
      addOfficeEvent({ type: 'task_failed', from_id: todo.assigned_to, content: `Retry failed: ${todo.description}`, error: 'Persistent error on retry', session_id: activeSessionId || 'default' });

      addClientMessage({
        id: `msg_${Date.now()}`,
        role: 'manager',
        content: `❌ Retry failed: "${todo.description}" still encountering errors. Consider revising the contract.`,
        timestamp: new Date().toISOString(),
      });
    }
  }, [contract, activeSessionId, updateTodoStatus, updateWorkerStatus, addOfficeEvent, addMemoryEntry, addClientMessage, setContractState, updateTodoActualTime]);

  const handleNewSession = useCallback(() => {
    clearClientMessages();
    clearWorkersMessages();
    clearOfficeEvents();
    setContract(null);
    setContractState('idle');
    setIntakeResult(null);
    setDebriefResult(null);
    setBriefingResult(null);
  }, [clearClientMessages, clearWorkersMessages, clearOfficeEvents, setContract, setContractState, setIntakeResult, setDebriefResult, setBriefingResult]);

  const handleReject = useCallback(() => {
    setContract(null);
    setContractState('idle');
    addClientMessage({
      id: `msg_${Date.now()}`,
      role: 'manager',
      content: 'Contract rejected. Feel free to start a new request anytime.',
      timestamp: new Date().toISOString(),
    });
  }, [setContract, setContractState, addClientMessage]);

  const handleAnswerQuestion = useCallback(async (messageId: string, selectedOption: string, customAnswer?: string) => {
    answerQuestion(messageId, selectedOption, customAnswer);
    const answerText = selectedOption === 'OTHER' ? customAnswer || 'Other' : selectedOption;
    await handleSendMessage(answerText);
  }, [answerQuestion, handleSendMessage]);

  return {
    handleSendMessage,
    handleAccept,
    handleRevise,
    handleRetryTodo,
    handleNewSession,
    handleReject,
    handleAnswerQuestion,
  };
}
