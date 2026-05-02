'use client';

import { OfficeEvent } from '@/lib/kantorku/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useEffect, useRef, useMemo, useState } from 'react';
import { Filter, ChevronDown, ChevronRight, Clock, AlertTriangle, AlertCircle, Info, XCircle, CheckCircle2 } from 'lucide-react';

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

// Severity mapping based on event type
function getEventSeverity(type: string): 'info' | 'warn' | 'error' | 'success' {
  if (type.includes('failed') || type.includes('error')) return 'error';
  if (type.includes('done') || type.includes('accepted') || type.includes('ready')) return 'success';
  if (type.includes('decision') || type.includes('broadcast') || type.includes('escalat')) return 'warn';
  return 'info';
}

const SEVERITY_CONFIG: Record<string, { color: string; icon: typeof Info; label: string }> = {
  info: { color: '#06b6d4', icon: Info, label: 'INFO' },
  warn: { color: '#f59e0b', icon: AlertTriangle, label: 'WARN' },
  error: { color: '#ef4444', icon: XCircle, label: 'ERROR' },
  success: { color: '#10b981', icon: CheckCircle2, label: 'OK' },
};

function formatTimestamp(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (isToday) return time;
  return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${time}`;
}

export function OfficeEventLog({ events }: OfficeEventLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');
  const [workerFilter, setWorkerFilter] = useState<string>('all');
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Collect unique event types and workers
  const eventTypes = useMemo(() => {
    const types = new Set<string>();
    events.forEach((e) => types.add(e.type));
    return Array.from(types).sort();
  }, [events]);

  const workerIds = useMemo(() => {
    const ids = new Set<string>();
    events.forEach((e) => {
      if (e.from_id) ids.add(e.from_id);
    });
    return Array.from(ids).sort();
  }, [events]);

  // Filtered events
  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (eventTypeFilter !== 'all' && e.type !== eventTypeFilter) return false;
      if (workerFilter !== 'all' && e.from_id !== workerFilter) return false;
      return true;
    });
  }, [events, eventTypeFilter, workerFilter]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [filteredEvents.length]);

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Events</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-500 font-mono">
              {filteredEvents.length}/{events.length}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-3 w-3" />
          </Button>
        </div>

        {showFilters && (
          <div className="space-y-1">
            {/* Event type filter */}
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-[8px] text-slate-500 font-mono">Type:</span>
              <Badge
                variant="outline"
                className={`text-[7px] px-1 py-0 h-3.5 cursor-pointer font-mono ${
                  eventTypeFilter === 'all'
                    ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                    : 'border-slate-700/30 text-slate-500 hover:border-slate-500/40'
                }`}
                onClick={() => setEventTypeFilter('all')}
              >
                All
              </Badge>
              {eventTypes.map((type) => (
                <Badge
                  key={type}
                  variant="outline"
                  className={`text-[7px] px-1 py-0 h-3.5 cursor-pointer font-mono ${
                    eventTypeFilter === type
                      ? ''
                      : 'border-slate-700/30 text-slate-500 hover:border-slate-500/40 opacity-70'
                  }`}
                  style={eventTypeFilter === type ? {
                    borderColor: `${eventTypeColors[type] || '#94a3b8'}40`,
                    color: eventTypeColors[type] || '#94a3b8',
                    backgroundColor: `${eventTypeColors[type] || '#94a3b8'}10`,
                  } : undefined}
                  onClick={() => setEventTypeFilter(type)}
                >
                  {type}
                </Badge>
              ))}
            </div>
            {/* Worker filter */}
            {workerIds.length > 0 && (
              <div className="flex items-center gap-1 flex-wrap">
                <span className="text-[8px] text-slate-500 font-mono">From:</span>
                <Badge
                  variant="outline"
                  className={`text-[7px] px-1 py-0 h-3.5 cursor-pointer font-mono ${
                    workerFilter === 'all'
                      ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                      : 'border-slate-700/30 text-slate-500 hover:border-slate-500/40'
                  }`}
                  onClick={() => setWorkerFilter('all')}
                >
                  All
                </Badge>
                {workerIds.map((id) => (
                  <Badge
                    key={id}
                    variant="outline"
                    className={`text-[7px] px-1 py-0 h-3.5 cursor-pointer font-mono ${
                      workerFilter === id
                        ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                        : 'border-slate-700/30 text-slate-500 hover:border-slate-500/40 opacity-70'
                    }`}
                    onClick={() => setWorkerFilter(id)}
                  >
                    {id}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Events list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-1.5">
        {filteredEvents.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
            <span className="text-2xl">📡</span>
            <p className="text-center text-slate-600">
              {events.length === 0 ? 'Office events will stream here.' : 'No events match the current filters.'}
            </p>
          </div>
        )}
        {filteredEvents.map((event, idx) => {
          const color = eventTypeColors[event.type] || '#94a3b8';
          const severity = getEventSeverity(event.type);
          const severityConfig = SEVERITY_CONFIG[severity];
          const isExpanded = expandedIdx === idx;
          const SeverityIcon = severityConfig.icon;

          return (
            <div
              key={`${event.type}-${idx}`}
              className="border-b border-slate-800/50 last:border-0 cursor-pointer hover:bg-slate-800/20 rounded-sm transition-colors"
              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
            >
              <div className="flex items-start gap-2 py-1.5">
                {/* Severity indicator */}
                <div
                  className="h-4 w-0.5 rounded-full mt-0.5 flex-shrink-0"
                  style={{ backgroundColor: severityConfig.color, boxShadow: `0 0 4px ${severityConfig.color}40` }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <SeverityIcon className="h-2.5 w-2.5 flex-shrink-0" style={{ color: severityConfig.color }} />
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
                    <span className="text-[8px] text-slate-600 font-mono ml-auto flex-shrink-0">
                      {formatTimestamp(event.timestamp)}
                    </span>
                    {isExpanded ? (
                      <ChevronDown className="h-2.5 w-2.5 text-slate-500 flex-shrink-0" />
                    ) : (
                      <ChevronRight className="h-2.5 w-2.5 text-slate-500 flex-shrink-0" />
                    )}
                  </div>
                  {event.content && !isExpanded && (
                    <p className="text-[10px] text-slate-400 mt-0.5 leading-tight break-words">
                      {typeof event.content === 'string'
                        ? event.content.substring(0, 120)
                        : JSON.stringify(event.content).substring(0, 120)}
                    </p>
                  )}
                  {/* Expanded event details */}
                  {isExpanded && (
                    <div className="mt-1.5 p-2 rounded bg-slate-900/60 border border-slate-700/20 space-y-1">
                      {event.content && (
                        <div>
                          <p className="text-[8px] text-slate-500 uppercase">Content</p>
                          <p className="text-[9px] text-slate-300 break-words">
                            {typeof event.content === 'string' ? event.content : JSON.stringify(event.content, null, 2)}
                          </p>
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-1">
                        {event.trace_id && (
                          <div>
                            <p className="text-[8px] text-slate-500 uppercase">Trace ID</p>
                            <p className="text-[8px] text-slate-300 font-mono truncate">{event.trace_id}</p>
                          </div>
                        )}
                        {event.duration_ms !== undefined && (
                          <div>
                            <p className="text-[8px] text-slate-500 uppercase">Duration</p>
                            <p className="text-[8px] text-cyan-300 font-mono">{event.duration_ms}ms</p>
                          </div>
                        )}
                        {event.session_id && (
                          <div>
                            <p className="text-[8px] text-slate-500 uppercase">Session</p>
                            <p className="text-[8px] text-slate-300 font-mono truncate">{event.session_id}</p>
                          </div>
                        )}
                        {event.model && (
                          <div>
                            <p className="text-[8px] text-slate-500 uppercase">Model</p>
                            <p className="text-[8px] text-slate-300 font-mono truncate">{event.model}</p>
                          </div>
                        )}
                        {event.error && (
                          <div className="col-span-2">
                            <p className="text-[8px] text-red-400 uppercase">Error</p>
                            <p className="text-[8px] text-red-300 break-words">{event.error}</p>
                          </div>
                        )}
                        {event.reason && (
                          <div>
                            <p className="text-[8px] text-slate-500 uppercase">Reason</p>
                            <p className="text-[8px] text-slate-300 break-words">{event.reason}</p>
                          </div>
                        )}
                        {event.approved !== undefined && (
                          <div>
                            <p className="text-[8px] text-slate-500 uppercase">Approved</p>
                            <p className={`text-[8px] font-mono ${event.approved ? 'text-green-300' : 'text-red-300'}`}>
                              {event.approved ? 'Yes' : 'No'}
                            </p>
                          </div>
                        )}
                      </div>
                      {/* Full metadata */}
                      {Object.keys(event).filter(k => !['type', 'from_id', 'to_id', 'content', 'timestamp', 'trace_id', 'duration_ms', 'session_id', 'model', 'error', 'reason', 'approved'].includes(k)).length > 0 && (
                        <div>
                          <p className="text-[8px] text-slate-500 uppercase">Metadata</p>
                          <pre className="text-[8px] text-slate-400 font-mono overflow-x-auto max-h-24 overflow-y-auto custom-scrollbar">
                            {JSON.stringify(
                              Object.fromEntries(
                                Object.entries(event).filter(([k]) => !['type', 'from_id', 'to_id', 'content', 'timestamp', 'trace_id', 'duration_ms', 'session_id', 'model', 'error', 'reason', 'approved'].includes(k))
                              ),
                              null,
                              2
                            )}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
