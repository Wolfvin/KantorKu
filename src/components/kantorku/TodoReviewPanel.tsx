'use client';

import { useMemo } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { WORKERS } from '@/lib/kantorku/workers-data';
import type { TodoItem } from '@/lib/kantorku/types';
import {
  ClipboardCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ChevronRight,
  Zap,
} from 'lucide-react';

interface TodoReview {
  todo: TodoItem;
  understood: boolean;
  concern: string;
  suggestion: string;
  can_execute: boolean;
  estimated_effort: string;
}

// Generate simulated review data for each todo
function generateTodoReviews(todos: TodoItem[]): TodoReview[] {
  return todos.map((todo) => {
    const hasDeps = todo.depends_on.length > 0;
    const isComplex = todo.description.length > 80;
    const random = Math.random();

    return {
      todo,
      understood: random > 0.15,
      concern: random < 0.15
        ? 'Need clarification on acceptance criteria'
        : hasDeps && random < 0.3
        ? 'Dependency timing may cause bottleneck'
        : '',
      suggestion: isComplex
        ? 'Consider splitting into subtasks'
        : random > 0.7
        ? 'Can start immediately'
        : '',
      can_execute: random > 0.1,
      estimated_effort: todo.estimated_time_ms
        ? `${(todo.estimated_time_ms / 1000).toFixed(1)}s`
        : isComplex
        ? '~5s'
        : '~2s',
    };
  });
}

export function TodoReviewPanel() {
  const { contract, contractState } = useKantorkuStore();

  const reviews = useMemo(() => {
    if (!contract || contract.todos.length === 0) return [];
    return generateTodoReviews(contract.todos);
  }, [contract]);

  const allUnderstood = reviews.length > 0 && reviews.every((r) => r.understood);
  const hasConcerns = reviews.some((r) => r.concern);
  const hasBlockers = reviews.some((r) => !r.can_execute);
  const readyCount = reviews.filter((r) => r.can_execute).length;

  // Group by worker
  const workerGroups = useMemo(() => {
    const groups: Record<string, TodoReview[]> = {};
    reviews.forEach((review) => {
      const workerId = review.todo.assigned_to || 'unassigned';
      if (!groups[workerId]) groups[workerId] = [];
      groups[workerId].push(review);
    });
    return groups;
  }, [reviews]);

  if (!contract || reviews.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-2">
        <ClipboardCheck className="h-8 w-8 text-slate-600/50" />
        <p className="text-[11px] text-center text-slate-600">
          No todos to review.<br />
          Accept a contract to see the review phase.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <ClipboardCheck className="h-3.5 w-3.5 text-teal-400" />
          <span className="text-[11px] font-mono text-slate-400 uppercase">Sprint Review</span>
          <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-teal-500/30 text-teal-300 font-mono">
            {reviews.length} todos
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {allUnderstood && !hasBlockers && (
            <Badge variant="outline" className="text-[8px] px-1.5 py-0 h-4 border-green-500/30 text-green-300 bg-green-500/10 font-mono">
              ✅ Ready to proceed
            </Badge>
          )}
          {hasBlockers && (
            <Badge variant="outline" className="text-[8px] px-1.5 py-0 h-4 border-red-500/30 text-red-300 bg-red-500/10 font-mono">
              🚫 {reviews.length - readyCount} blocker(s)
            </Badge>
          )}
          {hasConcerns && !hasBlockers && (
            <Badge variant="outline" className="text-[8px] px-1.5 py-0 h-4 border-amber-500/30 text-amber-300 bg-amber-500/10 font-mono">
              ⚠️ {reviews.filter((r) => r.concern).length} concern(s)
            </Badge>
          )}
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 rounded bg-green-500/10 border border-green-500/20 text-center">
          <p className="text-xs font-bold text-green-300 font-mono">{readyCount}</p>
          <p className="text-[9px] text-slate-500">Ready</p>
        </div>
        <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-center">
          <p className="text-xs font-bold text-amber-300 font-mono">{reviews.filter((r) => r.concern).length}</p>
          <p className="text-[9px] text-slate-500">Concerns</p>
        </div>
        <div className="p-2 rounded bg-red-500/10 border border-red-500/20 text-center">
          <p className="text-xs font-bold text-red-300 font-mono">{reviews.filter((r) => !r.can_execute).length}</p>
          <p className="text-[9px] text-slate-500">Blocked</p>
        </div>
      </div>

      {/* Per-Worker Reviews */}
      {Object.entries(workerGroups).map(([workerId, workerReviews]) => {
        const worker = WORKERS.find((w) => w.id === workerId);
        const workerReady = workerReviews.every((r) => r.understood && r.can_execute);
        const workerConcerns = workerReviews.filter((r) => r.concern);

        return (
          <Card key={workerId} className="bg-slate-800/40 border-slate-700/30 backdrop-blur-sm">
            <CardContent className="p-3 space-y-2">
              {/* Worker Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{worker?.emoji || '🤖'}</span>
                  <span className="text-[11px] font-mono font-semibold" style={{ color: worker?.color || '#94a3b8' }}>
                    {workerId}
                  </span>
                  <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 border-slate-600/50 text-slate-400">
                    {worker?.squad || 'unknown'}
                  </Badge>
                </div>
                <div className="flex items-center gap-1">
                  {workerReady ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                  ) : workerConcerns.length > 0 ? (
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-400" />
                  )}
                  <span className={`text-[9px] font-mono ${
                    workerReady ? 'text-green-400' : workerConcerns.length > 0 ? 'text-amber-400' : 'text-red-400'
                  }`}>
                    {workerReady ? 'READY' : workerConcerns.length > 0 ? 'CONCERNS' : 'BLOCKED'}
                  </span>
                </div>
              </div>

              {/* Todo List */}
              <div className="space-y-1.5">
                {workerReviews.map((review) => {
                  const statusColor = review.can_execute
                    ? review.concern
                      ? 'text-amber-400'
                      : 'text-green-400'
                    : 'text-red-400';
                  const statusBg = review.can_execute
                    ? review.concern
                      ? 'bg-amber-500/5 border-amber-500/20'
                      : 'bg-green-500/5 border-green-500/20'
                    : 'bg-red-500/5 border-red-500/20';
                  const statusIcon = review.can_execute
                    ? review.concern
                      ? <AlertTriangle className="h-3 w-3 text-amber-400" />
                      : <CheckCircle2 className="h-3 w-3 text-green-400" />
                    : <XCircle className="h-3 w-3 text-red-400" />;

                  return (
                    <div
                      key={review.todo.id}
                      className={`p-2 rounded border ${statusBg}`}
                    >
                      <div className="flex items-start gap-1.5">
                        {statusIcon}
                        <div className="flex-1 min-w-0">
                          <p className="text-[11px] text-slate-300 leading-tight break-words">
                            {review.todo.description}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`text-[9px] font-mono ${statusColor}`}>
                              {review.understood ? '✅ Understood' : '❌ Needs clarification'}
                            </span>
                            <span className="text-[9px] font-mono text-slate-500">
                              Effort: {review.estimated_effort}
                            </span>
                            {review.todo.priority && (
                              <Badge variant="outline" className={`text-[7px] px-1 py-0 h-3 ${
                                review.todo.priority === 'critical' ? 'border-red-500/30 text-red-300' :
                                review.todo.priority === 'high' ? 'border-amber-500/30 text-amber-300' :
                                'border-slate-600/50 text-slate-400'
                              }`}>
                                {review.todo.priority}
                              </Badge>
                            )}
                          </div>
                          {review.concern && (
                            <div className="mt-1 flex items-start gap-1">
                              <AlertTriangle className="h-2.5 w-2.5 text-amber-400 flex-shrink-0 mt-0.5" />
                              <p className="text-[9px] text-amber-300/80">{review.concern}</p>
                            </div>
                          )}
                          {review.suggestion && (
                            <div className="mt-0.5 flex items-start gap-1">
                              <Zap className="h-2.5 w-2.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                              <p className="text-[9px] text-cyan-300/60">{review.suggestion}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        );
      })}

      {/* Concerns Section */}
      {hasConcerns && (
        <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <div className="flex items-center gap-1.5 mb-1.5">
            <AlertTriangle className="h-3 w-3 text-amber-400" />
            <span className="text-[11px] text-amber-400 font-mono font-semibold">CONCERNS</span>
          </div>
          <div className="space-y-1">
            {reviews.filter((r) => r.concern).map((review) => (
              <div key={review.todo.id} className="flex items-start gap-1.5">
                <span className="text-[9px] text-amber-400 font-mono flex-shrink-0">{review.todo.assigned_to}:</span>
                <p className="text-[9px] text-amber-300/80">{review.concern}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ready Indicator */}
      <div className={`p-2.5 rounded-lg border ${
        allUnderstood && !hasBlockers
          ? 'bg-green-500/10 border-green-500/20'
          : 'bg-slate-800/40 border-slate-700/20'
      }`}>
        <div className="flex items-center gap-2">
          {allUnderstood && !hasBlockers ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              <div>
                <p className="text-[11px] text-green-300 font-medium">All workers understand their tasks</p>
                <p className="text-[9px] text-green-400/60">Ready to proceed with execution</p>
              </div>
            </>
          ) : (
            <>
              <Clock className="h-4 w-4 text-amber-400" />
              <div>
                <p className="text-[11px] text-amber-300 font-medium">Waiting for all workers to confirm</p>
                <p className="text-[9px] text-amber-400/60">
                  {readyCount}/{reviews.length} tasks ready
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
