import { useCallback, useEffect, useRef, useState } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import type { OfficeEvent } from '@/lib/kantorku/types';

interface UseWebSocketOptions {
  url: string;
  sessionId?: string;
  enabled?: boolean;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export function useWebSocket({ url, sessionId, enabled = true }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => {});
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');

  const connect = useCallback(() => {
    if (!enabled || !url) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
    }

    setConnectionState('connecting');

    const wsUrl = sessionId ? `${url}?session_id=${sessionId}` : url;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState('connected');
      useKantorkuStore.setState({
        isBackendConnected: true,
        sseConnected: true,
      });
    };

    ws.onclose = () => {
      setConnectionState('disconnected');
      useKantorkuStore.setState({
        isBackendConnected: false,
        sseConnected: false,
      });
      // Auto-reconnect after 3 seconds
      if (enabled) {
        reconnectTimerRef.current = setTimeout(() => {
          // Re-read the latest connect function from the ref
          connectRef.current();
        }, 3000);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (e) {
        console.error('[WebSocket] Message parse error:', e);
      }
    };

    ws.onerror = () => {
      setConnectionState('disconnected');
    };
  }, [url, sessionId, enabled]);

  // Keep the connect ref up to date via effect
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null; // Prevent auto-reconnect
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionState('disconnected');
    useKantorkuStore.setState({
      isBackendConnected: false,
      sseConnected: false,
    });
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connectionState, send, disconnect, reconnect: connect };
}

function handleWebSocketMessage(data: { type: string; [key: string]: unknown }) {
  const store = useKantorkuStore.getState();

  switch (data.type) {
    case 'manager_message': {
      store.addClientMessage({
        id: `msg_ws_${Date.now()}`,
        role: 'manager',
        content: (data.content as string) || '',
        timestamp: new Date().toISOString(),
      });
      break;
    }

    case 'contract_ready': {
      if (data.contract) {
        store.setContract(data.contract as Parameters<typeof store.setContract>[0]);
        store.setContractState('contract_presented');
      }
      break;
    }

    case 'work_started': {
      store.setContractState('working');
      break;
    }

    case 'work_done': {
      store.setContractState('done');
      break;
    }

    case 'worker_speak_up':
    case 'task_assigned':
    case 'task_started':
    case 'task_done':
    case 'task_failed': {
      const event: OfficeEvent = {
        type: data.type,
        from_id: (data.from_id as string) || (data.worker as string) || '',
        content: (data.content as string) || (data.message as string) || '',
        timestamp: new Date().toISOString(),
      };
      store.addOfficeEvent(event);

      // Also add to workers chat for certain types
      if (data.type === 'worker_speak_up' || data.type === 'task_done' || data.type === 'task_failed') {
        store.addWorkersMessage({
          id: `wmsg_ws_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          from_id: event.from_id || 'unknown',
          message_type: data.type === 'task_done' ? 'agreement' : data.type === 'task_failed' ? 'concern' : 'speak',
          content: event.content || '',
          timestamp: new Date().toISOString(),
        });
      }
      break;
    }

    case 'question': {
      store.addClientMessage({
        id: `msg_ws_q_${Date.now()}`,
        role: 'manager',
        content: (data.content as string) || (data.question as string) || '',
        timestamp: new Date().toISOString(),
        question: data.question as unknown as Parameters<typeof store.addClientMessage>[0]['question'],
      });
      break;
    }

    case 'heartbeat': {
      // Server heartbeat, just acknowledge
      break;
    }

    default: {
      // Unknown message type - add as office event
      store.addOfficeEvent({
        type: data.type,
        from_id: (data.from_id as string) || 'system',
        content: (data.content as string) || JSON.stringify(data),
        timestamp: new Date().toISOString(),
      });
    }
  }
}
