'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { ClientChatPanel } from './ChatPanel';
import { ContractCard } from './ContractCard';
import { Badge } from '@/components/ui/badge';
import { CONTRACT_STATE_LABELS } from '@/lib/kantorku/workers-data';
import { MessageSquare, FileText, Zap } from 'lucide-react';

export function LobbyZone() {
  const {
    clientMessages,
    contract,
    contractState,
    isManagerThinking,
    isWorking,
    intakeResult,
    addClientMessage,
    setContract,
    setContractState,
    setManagerThinking,
    setWorking,
    addOfficeEvent,
    updateWorkerStatus,
    addWorkersMessage,
    updateTodoStatus,
    addCostEntry,
    setIntakeResult,
    setBriefingResult,
    addDiscussionRound,
    addSession,
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

      // Send to chat API
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
          session_id: 'default',
        }),
      });

      const data = await response.json();

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
          session_id: 'default',
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
    } finally {
      setManagerThinking(false);
    }
  };

  const handleAccept = async () => {
    if (!contract) return;

    setContractState('working');
    setWorking(true);
    addOfficeEvent({
      type: 'contract_accepted',
      from_id: 'conductor',
      content: contract.title,
      session_id: 'default',
    });

    // Mark relevant workers as busy
    for (const todo of contract.todos) {
      if (todo.assigned_to) {
        updateWorkerStatus(todo.assigned_to, 'busy', todo.description);
      }
    }

    try {
      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract,
          session_id: 'default',
        }),
      });

      const data = await response.json();

      if (data.events) {
        // Process events sequentially
        for (const event of data.events) {
          // Add a small delay for visual effect
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
              timestamp: event.timestamp as string || new Date().toISOString(),
            });
          }

          // Update task status
          if (event.type === 'task_started' && event.to_id) {
            updateTodoStatus(
              contract.todos.find(
                (t) => t.assigned_to === event.to_id && t.status === 'pending'
              )?.id || '',
              'in_progress'
            );
          }

          if (event.type === 'task_done' && event.from_id) {
            const todo = contract.todos.find(
              (t) => t.assigned_to === event.from_id && t.status === 'in_progress'
            );
            if (todo) {
              updateTodoStatus(todo.id, 'done');
            }
            updateWorkerStatus(event.from_id, 'idle', undefined);
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

      addDiscussionRound({
        round_number: 1,
        messages: useKantorkuStore.getState().workersMessages.slice(-5),
        summary: 'Briefing complete. Team is aligned.',
        decisions: ['Proceed with current plan'],
      });

      // Mark contract as done
      setContractState('done');
      contract.todos.forEach((t) => updateTodoStatus(t.id, 'done'));
      addCostEntry('conductor', 2000, 800, 0.05);
    } catch (error) {
      console.error('Execute error:', error);
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
          session_id: 'default',
        }),
      });

      const data = await response.json();

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
              className={`text-[9px] px-1.5 py-0 h-4 font-mono ${
                contractState === 'working'
                  ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                  : contractState === 'done'
                  ? 'border-green-500/40 text-green-300 bg-green-500/10'
                  : contractState === 'contract_presented'
                  ? 'border-amber-500/40 text-amber-300 bg-amber-500/10'
                  : 'border-slate-600/50 text-slate-400 bg-slate-800/30'
              }`}
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
            <span className="text-[10px] text-amber-400 font-mono font-semibold">
              INTAKE
            </span>
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
          </div>
          {intakeResult.summary && (
            <p className="text-[9px] text-slate-500 mt-1">{intakeResult.summary}</p>
          )}
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <ClientChatPanel
          messages={clientMessages}
          onSend={handleSendMessage}
          isThinking={isManagerThinking}
          disabled={isWorking}
        />
      </div>

      {/* Contract Card (if presented) */}
      {contract && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1">
          <ContractCard
            contract={contract}
            onAccept={handleAccept}
            onRevise={handleRevise}
            onReject={handleReject}
            isWorking={isWorking}
          />
        </div>
      )}
    </div>
  );
}
