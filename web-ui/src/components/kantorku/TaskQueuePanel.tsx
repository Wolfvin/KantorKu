'use client';

import { useState, useMemo, useEffect } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { WORKERS } from '@/lib/kantorku/workers-data';
import type { TodoItem } from '@/lib/kantorku/types';
import {
  ListOrdered, RefreshCw, XCircle, RotateCcw, AlertTriangle,
  Clock, CheckCircle2, Loader2, ChevronDown, ChevronRight,
  Radio, Archive,
} from 'lucide-react';

type TaskState = 'PENDING' | 'IN_PROGRESS' | 'DONE' | 'FAILED' | 'RETRYING' | 'CANCELLED' | 'DEAD_LETTER';

interface QueueTask {
  id: string;
  description: string;
  assigned_to: string;
  priority: 'high' | 'medium' | 'low' | 'critical';
  state: TaskState;
  retryCount: number;
  maxRetries: number;
  createdAt: string;
  updatedAt: string;
  error?: string;
}

const STATE_CONFIG: Record<TaskState, { color: string; bg: string; border: string; icon: typeof Clock }> = {
  PENDING: { color: 'text-amber-300', bg: 'bg-amber-500/10', border: 'border-amber-500/30', icon: Clock },
  IN_PROGRESS: { color: 'text-cyan-300', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', icon: Loader2 },
  DONE: { color: 'text-green-300', bg: 'bg-green-500/10', border: 'border-green-500/30', icon: CheckCircle2 },
  FAILED: { color: 'text-red-300', bg: 'bg-red-500/10', border: 'border-red-500/30', icon: XCircle },
  RETRYING: { color: 'text-amber-300', bg: 'bg-amber-500/10', border: 'border-amber-500/30', icon: RotateCcw },
  CANCELLED: { color: 'text-slate-400', bg: 'bg-slate-500/10', border: 'border-slate-500/30', icon: XCircle },
  DEAD_LETTER: { color: 'text-red-400', bg: 'bg-red-900/20', border: 'border-red-500/40', icon: AlertTriangle },
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'border-purple-500/30 text-purple-300 bg-purple-500/10',
  high: 'border-red-500/30 text-red-300 bg-red-500/10',
  medium: 'border-amber-500/30 text-amber-300 bg-amber-500/10',
  low: 'border-slate-500/30 text-slate-400 bg-slate-500/10',
};

function todoStateToTaskState(status: TodoItem['status'], retryCount: number, maxRetries: number): TaskState {
  if (status === 'pending') return 'PENDING';
  if (status === 'in_progress') return 'IN_PROGRESS';
  if (status === 'done') return 'DONE';
  if (status === 'failed') {
    if (retryCount >= maxRetries) return 'DEAD_LETTER';
    if (retryCount > 0) return 'RETRYING';
    return 'FAILED';
  }
  if (status === 'blocked') return 'CANCELLED';
  return 'PENDING';
}

export function TaskQueuePanel() {
  const { contract, updateTodoStatus, updateWorkerStatus, addOfficeEvent, activeSessionId } = useKantorkuStore();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [retryCounts, setRetryCounts] = useState<Record<string, number>>({});

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      setRefreshTick((t) => t + 1);
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  // Build queue tasks from contract todos
  const queueTasks: QueueTask[] = useMemo(() => {
    if (!contract) return [];
    return contract.todos.map((todo) => {
      const retries = retryCounts[todo.id] || 0;
      const maxRetries = 3;
      return {
        id: todo.id,
        description: todo.description,
        assigned_to: todo.assigned_to,
        priority: todo.priority || 'medium',
        state: todoStateToTaskState(todo.status, retries, maxRetries),
        retryCount: retries,
        maxRetries,
        createdAt: todo.started_at || contract.created_at,
        updatedAt: todo.completed_at || contract.updated_at,
        error: todo.error,
      };
    });
  }, [contract, retryCounts, refreshTick]);

  // Sort by priority then state
  const priorityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const stateOrder: Record<TaskState, number> = {
    IN_PROGRESS: 0, PENDING: 1, RETRYING: 2, FAILED: 3,
    DEAD_LETTER: 4, DONE: 5, CANCELLED: 6,
  };

  const sortedTasks = useMemo(() => {
    return [...queueTasks].sort((a, b) => {
      const stateDiff = (stateOrder[a.state] ?? 99) - (stateOrder[b.state] ?? 99);
      if (stateDiff !== 0) return stateDiff;
      return (priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1);
    });
  }, [queueTasks]);

  // Active queue (not done/cancelled)
  const activeQueue = sortedTasks.filter((t) => t.state !== 'DONE' && t.state !== 'CANCELLED');
  // Dead letter queue
  const deadLetterQueue = sortedTasks.filter((t) => t.state === 'DEAD_LETTER');
  // Completed
  const completedTasks = sortedTasks.filter((t) => t.state === 'DONE');

  const handleRetry = (taskId: string) => {
    setRetryCounts((prev) => ({ ...prev, [taskId]: (prev[taskId] || 0) + 1 }));
    updateTodoStatus(taskId, 'pending');
    const todo = contract?.todos.find((t) => t.id === taskId);
    if (todo?.assigned_to) {
      updateWorkerStatus(todo.assigned_to, 'busy', todo.description);
    }
    addOfficeEvent({
      type: 'task_started',
      to_id: todo?.assigned_to,
      content: `Retrying task: ${todo?.description}`,
      session_id: activeSessionId || 'default',
    });
  };

  const handleCancel = (taskId: string) => {
    updateTodoStatus(taskId, 'blocked', undefined, 'Cancelled by user');
    addOfficeEvent({
      type: 'task_failed',
      from_id: contract?.todos.find((t) => t.id === taskId)?.assigned_to,
      content: `Task cancelled: ${contract?.todos.find((t) => t.id === taskId)?.description}`,
      session_id: activeSessionId || 'default',
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <ListOrdered className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Antrian Tugas</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-500 font-mono">
              {queueTasks.length}
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <div className={`h-1.5 w-1.5 rounded-full ${autoRefresh ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} />
            <span className="text-[8px] text-slate-600 font-mono">
              {autoRefresh ? 'auto' : 'off'}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="h-4 w-4 p-0 text-slate-500 hover:text-cyan-400"
            >
              <RefreshCw className="h-2.5 w-2.5" />
            </Button>
          </div>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-2 mt-1.5 text-[9px] font-mono">
          <span className="text-amber-300">{activeQueue.filter((t) => t.state === 'PENDING').length} pending</span>
          <span className="text-cyan-300">{activeQueue.filter((t) => t.state === 'IN_PROGRESS').length} active</span>
          <span className="text-green-300">{completedTasks.length} done</span>
          <span className="text-red-300">{deadLetterQueue.length} dead</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
        {queueTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <ListOrdered className="h-8 w-8 text-slate-600/50 mb-2" />
            <p className="text-[10px] text-center text-slate-600">
              Belum ada tugas dalam antrian.<br />
              Terima kontrak untuk memulai.
            </p>
          </div>
        ) : (
          <>
            {/* Active Queue */}
            {activeQueue.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Radio className="h-3 w-3 text-cyan-400" />
                  <span className="text-[10px] font-mono text-cyan-300 uppercase">Antrian Aktif</span>
                  <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 border-cyan-500/30 text-cyan-300">
                    {activeQueue.length}
                  </Badge>
                </div>
                <div className="space-y-1">
                  {activeQueue.map((task) => {
                    const config = STATE_CONFIG[task.state];
                    const StateIcon = config.icon;
                    const isExpanded = expandedId === task.id;
                    const worker = WORKERS.find((w) => w.id === task.assigned_to);

                    return (
                      <div
                        key={task.id}
                        className={`p-2 rounded-md ${config.bg} ${config.border} border cursor-pointer transition-colors`}
                        onClick={() => setExpandedId(isExpanded ? null : task.id)}
                      >
                        <div className="flex items-center gap-1.5">
                          <StateIcon className={`h-3 w-3 ${config.color} ${task.state === 'IN_PROGRESS' ? 'animate-spin' : ''}`} />
                          <Badge variant="outline" className={`text-[8px] px-1 py-0 h-3 font-mono ${PRIORITY_COLORS[task.priority]}`}>
                            {task.priority}
                          </Badge>
                          <span className="text-[11px] text-slate-300 truncate flex-1">
                            {task.description}
                          </span>
                          <Badge variant="outline" className={`text-[8px] px-1 py-0 h-3.5 ${config.border} ${config.color} font-mono`}>
                            {task.state}
                          </Badge>
                          {isExpanded ? <ChevronDown className="h-2.5 w-2.5 text-slate-500" /> : <ChevronRight className="h-2.5 w-2.5 text-slate-500" />}
                        </div>

                        {isExpanded && (
                          <div className="mt-1.5 pt-1.5 border-t border-slate-700/20 space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] font-mono" style={{ color: worker?.color || '#94a3b8' }}>
                                {worker?.emoji || '🤖'} {task.assigned_to}
                              </span>
                            </div>
                            {task.error && (
                              <p className="text-[10px] text-red-300/80 font-mono bg-red-500/10 p-1 rounded">{task.error}</p>
                            )}
                            <div className="flex items-center gap-1 text-[9px] text-slate-500 font-mono">
                              <span>Retry: {task.retryCount}/{task.maxRetries}</span>
                            </div>
                            <div className="flex gap-1.5 mt-1">
                              {(task.state === 'FAILED' || task.state === 'RETRYING') && task.retryCount < task.maxRetries && (
                                <Button onClick={(e) => { e.stopPropagation(); handleRetry(task.id); }} size="sm" className="h-5 text-[9px] bg-amber-600 hover:bg-amber-500 text-white px-2">
                                  <RotateCcw className="h-2.5 w-2.5 mr-0.5" /> Retry
                                </Button>
                              )}
                              {task.state === 'PENDING' && (
                                <Button onClick={(e) => { e.stopPropagation(); handleCancel(task.id); }} size="sm" variant="outline" className="h-5 text-[9px] border-red-500/40 text-red-300 hover:bg-red-500/10 px-2">
                                  <XCircle className="h-2.5 w-2.5 mr-0.5" /> Batal
                                </Button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Dead Letter Queue */}
            {deadLetterQueue.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Archive className="h-3 w-3 text-red-400" />
                  <span className="text-[10px] font-mono text-red-300 uppercase">Dead Letter Queue</span>
                  <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 border-red-500/30 text-red-300">
                    {deadLetterQueue.length}
                  </Badge>
                </div>
                <div className="space-y-1">
                  {deadLetterQueue.map((task) => {
                    const worker = WORKERS.find((w) => w.id === task.assigned_to);
                    return (
                      <div key={task.id} className="p-2 rounded-md bg-red-900/10 border border-red-500/20">
                        <div className="flex items-center gap-1.5">
                          <AlertTriangle className="h-3 w-3 text-red-400" />
                          <span className="text-[11px] text-red-300 truncate flex-1">{task.description}</span>
                          <span className="text-[9px] text-slate-500 font-mono">{task.assigned_to}</span>
                        </div>
                        {task.error && (
                          <p className="text-[9px] text-red-300/60 font-mono mt-1">{task.error}</p>
                        )}
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-[8px] text-slate-600 font-mono">Max retries ({task.maxRetries}) exceeded</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Completed */}
            {completedTasks.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <CheckCircle2 className="h-3 w-3 text-green-400" />
                  <span className="text-[10px] font-mono text-green-300 uppercase">Selesai</span>
                  <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 border-green-500/30 text-green-300">
                    {completedTasks.length}
                  </Badge>
                </div>
                <div className="space-y-0.5">
                  {completedTasks.map((task) => (
                    <div key={task.id} className="flex items-center gap-1.5 px-2 py-1 rounded bg-green-500/5 border border-green-500/10">
                      <CheckCircle2 className="h-2.5 w-2.5 text-green-400" />
                      <span className="text-[10px] text-slate-400 truncate flex-1">{task.description}</span>
                      <span className="text-[8px] text-slate-600 font-mono">{task.assigned_to}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
