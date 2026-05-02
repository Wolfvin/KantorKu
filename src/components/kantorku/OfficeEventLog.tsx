'use client';

import { OfficeEvent } from '@/lib/kantorku/types';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useEffect, useRef } from 'react';

interface OfficeEventLogProps {
  events: OfficeEvent[];
}

const eventTypeColors: Record<string, string> = {
  briefing_opened: '#06b6d4',
  plan_drafted: '#8b5cf6',
  worker_speak_up: '#22c55e',
  manager_summary: '#f59e0b',
  manager_decision: '#ec4899',
  task_assigned: '#3b82f6',
  task_started: '#06b6d4',
  task_done: '#10b981',
  task_failed: '#ef4444',
  verify_start: '#8b5cf6',
  verify_done: '#10b981',
  contract_ready: '#06b6d4',
  contract_accepted: '#10b981',
  contract_done: '#10b981',
  manager_message: '#06b6d4',
  worker_broadcast: '#f59e0b',
  error_logged: '#ef4444',
};

export function OfficeEventLog({ events }: OfficeEventLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-1.5">
      {events.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
          <span className="text-2xl">📡</span>
          <p className="text-center text-slate-600">
            Office events will stream here.
          </p>
        </div>
      )}
      {events.map((event, idx) => {
        const color = eventTypeColors[event.type] || '#94a3b8';
        return (
          <div
            key={`${event.type}-${idx}`}
            className="flex items-start gap-2 py-1 border-b border-slate-800/50 last:border-0"
          >
            <div
              className="h-1.5 w-1.5 rounded-full mt-1.5 flex-shrink-0"
              style={{ backgroundColor: color, boxShadow: `0 0 4px ${color}60` }}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className="text-[8px] px-1 py-0 h-3.5"
                  style={{
                    borderColor: `${color}40`,
                    color,
                    backgroundColor: `${color}10`,
                  }}
                >
                  {event.type}
                </Badge>
                {event.from_id && (
                  <span className="text-[9px] text-slate-500 font-mono">
                    from: {event.from_id}
                  </span>
                )}
              </div>
              {event.content && (
                <p className="text-[10px] text-slate-400 mt-0.5 leading-tight break-words">
                  {typeof event.content === 'string'
                    ? event.content.substring(0, 120)
                    : JSON.stringify(event.content).substring(0, 120)}
                </p>
              )}
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
