/**
 * useSSE — Server-Sent Events hook for KantorKu backend
 *
 * Connects to /events/stream/{sessionId} on the Python backend
 * for real-time event streaming without WebSocket.
 * Auto-reconnects on disconnect.
 */

'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { type OfficeEvent } from '@/lib/kantorku/types';

interface UseSSEReturn {
  connected: boolean;
  error: string | null;
  reconnect: () => void;
}

const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_BASE_DELAY = 1000;

const EVENT_TYPES = [
  'briefing_opened',
  'plan_drafted',
  'plan_revised',
  'contract_ready',
  'contract_accepted',
  'task_assigned',
  'task_started',
  'task_done',
  'task_failed',
  'worker_speak_up',
  'worker_dm',
  'worker_broadcast',
  'context_fetch_start',
  'context_fetch_done',
  'context_requested',
  'context_delivered',
  'verify_design_start',
  'verify_design_done',
  'verify_engineer_start',
  'verify_engineer_done',
  'error_logged',
  'skill_updated',
  'manager_message',
  'manager_question',
  'llm_stream_start',
  'llm_stream_chunk',
  'llm_stream_done',
  'work_started',
  'work_done',
  'error',
];

export function useSSE(sessionId: string | null, enabled: boolean): UseSSEReturn {
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const connectedRef = useRef(false);

  const addOfficeEvent = useKantorkuStore((s) => s.addOfficeEvent);
  const setActiveSession = useKantorkuStore((s) => s.setActiveSession);
  const setSseConnected = useKantorkuStore((s) => s.setSseConnected);

  // Get backend URL from settings — fallback to environment variable
  const backendUrl = typeof window !== 'undefined'
    ? (localStorage.getItem('kantorku_backend_url') || process.env.NEXT_PUBLIC_KANTORKU_BACKEND_URL || '')
    : '';

  const isConfigured = !!(backendUrl && enabled && sessionId);

  const getReconnectDelay = useCallback(() => {
    const delay = RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current);
    return Math.min(delay, 30000);
  }, []);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  // Main effect — manages the SSE connection lifecycle
  useEffect(() => {
    if (!isConfigured) {
      cleanup();
      connectedRef.current = false;
      setSseConnected(false);
      return;
    }

    // Clean up existing connection
    cleanup();

    const url = `${backendUrl}/events/stream/${sessionId}`;
    let disposed = false;

    const createConnection = () => {
      try {
        const source = new EventSource(url);
        eventSourceRef.current = source;

        source.onopen = () => {
          if (disposed) return;
          connectedRef.current = true;
          setSseConnected(true);
          setError(null);
          reconnectAttemptsRef.current = 0;
        };

        source.onmessage = (msg) => {
          if (disposed) return;
          try {
            const data = JSON.parse(msg.data) as OfficeEvent;
            addOfficeEvent(data);
            if (data.session_id) {
              setActiveSession(data.session_id);
            }
          } catch {
            // Non-JSON message, ignore
          }
        };

        // Handle named events
        for (const eventType of EVENT_TYPES) {
          source.addEventListener(eventType, (msg: MessageEvent) => {
            if (disposed) return;
            try {
              const data = JSON.parse(msg.data) as OfficeEvent;
              addOfficeEvent(data);
            } catch {
              // Non-JSON message, ignore
            }
          });
        }

        source.onerror = () => {
          if (disposed) return;
          connectedRef.current = false;
          setSseConnected(false);
          setError('SSE connection error');

          if (source.readyState === EventSource.CLOSED) {
            if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
              const delay = getReconnectDelay();
              reconnectTimeoutRef.current = setTimeout(() => {
                if (disposed) return;
                reconnectAttemptsRef.current += 1;
                setError('Reconnecting...');
                createConnection();
              }, delay);
            } else {
              setError('Max reconnection attempts reached');
            }
          }
        };
      } catch (err) {
        if (disposed) return;
        connectedRef.current = false;
        setSseConnected(false);
        // Use queueMicrotask to avoid synchronous setState in effect
        queueMicrotask(() => {
          if (!disposed) {
            setError(err instanceof Error ? err.message : 'Failed to connect');
          }
        });
      }
    };

    createConnection();

    return () => {
      disposed = true;
      cleanup();
    };
  }, [isConfigured, backendUrl, sessionId, cleanup, addOfficeEvent, setActiveSession, setSseConnected, getReconnectDelay]);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    setError(null);
    connectedRef.current = false;
  }, []);

  return {
    connected: isConfigured && connectedRef.current,
    error,
    reconnect,
  };
}
