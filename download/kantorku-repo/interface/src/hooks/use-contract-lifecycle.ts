'use client';

import { useState, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import type { ChatApiResponse, ExecuteApiResponse, TeamFeedbackRound, DebriefResult, Contract, TodoItem } from '@/lib/kantorku/types';
import { toast } from 'sonner';

/**
 * Custom hook encapsulating all contract lifecycle state transitions,
 * API calls, and event handling for the LobbyZone.
 */
export function useContractLifecycle() {
  const store = useKantorkuStore();
  const {
    clientMessages, contract, contractState, isManagerThinking, isWorking,
    intakeResult, teamFeedback, debriefResult, approvalGates,
    sessions, activeSessionId,
    addClientMessage, setContract, setContractState, setManagerThinking,
    setWorking, addOfficeEvent, updateWorkerStatus, addWorkersMessage,
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
      const intakePromise = fetch('/api/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      }).then((r) => r.json()).catch(() => null);

      const history = clientMessages.map((m) => ({
        role: m.role === 'manager' ? 'assistant' : 'user',
        content: m.content,
      }));

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history, session_id: activeSessionId || 'default', stream: true }),
      });

      const contentType = response.headers.get('content-type') || '';
      let data: ChatApiResponse | null = null;

      if (contentType.includes('text/event-stream') && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamingContent = '';
        let streamingMsgId = `msg_stream_${Date.now()}`;

        addClientMessage({ id: streamingMsgId, role: 'manager', content: '', timestamp: new Date().toISOString() });

        let buffer = '';
        while (reader) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;
            try {
              const sseData = JSON.parse(jsonStr);
              if (sseData.type === 'chunk') {
                streamingContent += sseData.content;
                const s = useKantorkuStore.getState();
                useKantorkuStore.setState({
                  clientMessages: s.clientMessages.map((m) =>
                    m.id === streamingMsgId ? { ...m, content: streamingContent } : m
                  ),
                });
              } else if (sseData.type === 'done' && sseData.response) {
                data = sseData.response as ChatApiResponse;
              } else if (sseData.type === 'error') {
                toast.error('LLM Stream Error', { description: sseData.message });
              }
            } catch {}
          }
        }

        const s = useKantorkuStore.getState();
        useKantorkuStore.setState({ clientMessages: s.clientMessages.filter((m) => m.id !== streamingMsgId) });

        if (!data) data = { type: 'manager_message', content: streamingContent };
      } else {
        data = await response.json();
      }

      const intakeData = await intakePromise;
      if (intakeData && !intakeData.error) setIntakeResult(intakeData);

      if (data.type === 'contract_ready' && data.contract) {
        setContract(data.contract);
        setContractState('contract_presented');
        addClientMessage({
          id: `msg_${Date.now()}`, role: 'manager',
          content: `Saya sudah menyiapkan kontrak untuk "${data.contract.title}". Silakan tinjau dan beri tahu jika ada perubahan.`,
          timestamp: new Date().toISOString(),
        });
        addOfficeEvent({ type: 'contract_ready', from_id: 'conductor', content: data.contract.title, session_id: activeSessionId || 'default' });
        toast.success('📋 Kontrak siap ditinjau', { description: data.contract.title, duration: 5000 });
        if (!activeSessionId) {
          const sid = `session_${Date.now()}`;
          addSession({ session_id: sid, state: 'contract_presented', contract_title: data.contract.title, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), message_count: 1, total_cost: 0 });
        }
      } else if (data.type === 'team_feedback' && data.team_feedback) {
        setContractState('team_consult');
        data.team_feedback.forEach((fb: TeamFeedbackRound) => addTeamFeedback(fb));
        addClientMessage({ id: `msg_${Date.now()}`, role: 'manager', content: 'Tim kami memberikan feedback untuk permintaan ini...', source: 'team_feedback', timestamp: new Date().toISOString() });
        toast.info('👥 Konsultasi tim sedang berlangsung');
      } else if (data.type === 'question' && data.question) {
        setContractState('clarifying');
        addClientMessage({ id: `msg_${Date.now()}`, role: 'manager', content: data.content || data.question.question, timestamp: new Date().toISOString(), question: data.question });
        toast.info('❓ Manager memiliki pertanyaan', { description: data.question.question, duration: 6000 });
      } else if (data.type === 'manager_message' && data.content) {
        setContractState('clarifying');
        addClientMessage({ id: `msg_${Date.now()}`, role: 'manager', content: data.content, timestamp: new Date().toISOString() });
      }

      addCostEntry('conductor', 500, 200, 0.015);
    } catch (error) {
      console.error('Chat error:', error);
      setContractState('idle');
      addClientMessage({ id: `msg_${Date.now()}`, role: 'manager', content: 'Maaf, terjadi kesalahan. Silakan coba lagi.', timestamp: new Date().toISOString() });
      toast.error('❌ Chat error', { description: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setManagerThinking(false);
    }
  }, [clientMessages, activeSessionId, addClientMessage, setContract, setContractState, setManagerThinking, addOfficeEvent, setIntakeResult, addTeamFeedback, addCostEntry, addSession]);

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
    addClientMessage({ id: `msg_${Date.now()}`, role: 'manager', content: 'Kontrak ditolak. Silakan mulai permintaan baru.', timestamp: new Date().toISOString() });
  }, [setContract, setContractState, addClientMessage]);

  const handleAnswerQuestion = useCallback(async (messageId: string, selectedOption: string, customAnswer?: string) => {
    answerQuestion(messageId, selectedOption, customAnswer);
    const answerText = selectedOption === 'OTHER' ? customAnswer || 'Other' : selectedOption;
    await handleSendMessage(answerText);
  }, [answerQuestion, handleSendMessage]);

  return {
    handleSendMessage,
    handleNewSession,
    handleReject,
    handleAnswerQuestion,
  };
}
