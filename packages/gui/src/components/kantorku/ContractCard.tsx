'use client';

import { Contract, TodoItem, ApprovalGate } from '@/lib/kantorku/types';
import { CONTRACT_STATE_LABELS, WORKERS } from '@/lib/kantorku/workers-data';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Check, RotateCcw, X, Clock, Loader2, ArrowRight, DollarSign, AlertTriangle, Shield, ChevronDown, ChevronRight, RefreshCw, Eye } from 'lucide-react';
import React, { useState, useCallback } from 'react';
import { Textarea } from '@/components/ui/textarea';

interface ContractCardProps {
  contract: Contract;
  onAccept: () => void;
  onRevise: (feedback: string) => void;
  onReject: () => void;
  onRetryTodo?: (todoId: string) => void;
  isWorking: boolean;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  in_progress: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  done: 'bg-green-500/20 text-green-300 border-green-500/30',
  failed: 'bg-red-500/20 text-red-300 border-red-500/30',
  blocked: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

const priorityColors: Record<string, string> = {
  low: 'border-slate-500/30 text-slate-400 bg-slate-500/10',
  medium: 'border-amber-500/30 text-amber-300 bg-amber-500/10',
  high: 'border-orange-500/30 text-orange-300 bg-orange-500/10',
  critical: 'border-red-500/30 text-red-300 bg-red-500/10',
};

const priorityIcons: Record<string, string> = {
  low: '▽',
  medium: '◇',
  high: '◈',
  critical: '◆',
};

export const ContractCard = React.memo(function ContractCard({ contract, onAccept, onRevise, onReject, onRetryTodo, isWorking }: ContractCardProps) {
  const { approvalGates } = useKantorkuStore();
  const [showDetails, setShowDetails] = useState(false);
  const [showRevisionDialog, setShowRevisionDialog] = useState(false);
  const [revisionText, setRevisionText] = useState('');
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());

  const toggleError = useCallback((todoId: string) => {
    setExpandedErrors((prev) => {
      const next = new Set(prev);
      if (next.has(todoId)) next.delete(todoId);
      else next.add(todoId);
      return next;
    });
  }, []);

  const handleSubmitRevision = useCallback(() => {
    if (revisionText.trim()) {
      onRevise(revisionText.trim());
      setRevisionText('');
      setShowRevisionDialog(false);
    }
  }, [revisionText, onRevise]);

  const todoCounts = {
    total: contract.todos.length,
    pending: contract.todos.filter((t) => t.status === 'pending').length,
    in_progress: contract.todos.filter((t) => t.status === 'in_progress').length,
    done: contract.todos.filter((t) => t.status === 'done').length,
    failed: contract.todos.filter((t) => t.status === 'failed').length,
    blocked: contract.todos.filter((t) => t.status === 'blocked').length,
  };

  const progressPercent = todoCounts.total > 0
    ? Math.round((todoCounts.done / todoCounts.total) * 100)
    : 0;

  // Budget indicator
  const budgetUsed = contract.budget_limit
    ? ((contract.team_approved ? 0.5 : 0) / contract.budget_limit) * 100
    : 0;

  // Revision count
  const revisionCount = contract.team_feedback_rounds?.length || 0;

  // Get todos with dependencies
  const todosWithDeps = contract.todos.filter((t) => t.depends_on.length > 0);
  const todosById = Object.fromEntries(contract.todos.map((t) => [t.id, t]));

  // Relevant approval gates for this contract
  const contractGates = approvalGates.length > 0
    ? approvalGates
    : contract.approval_gates || [];

  // Worker vote status for team approval
  const workerVotes = contract.todos
    .filter((t) => t.assigned_to)
    .reduce((acc, t) => {
      const w = WORKERS.find((wk) => wk.id === t.assigned_to);
      if (w) {
        acc[t.assigned_to] = {
          emoji: w.emoji || '👤',
          name: w.id,
          color: w.color || '#94a3b8',
          status: t.status === 'done' ? 'approved' : t.status === 'failed' ? 'rejected' : 'pending',
        };
      }
      return acc;
    }, {} as Record<string, { emoji: string; name: string; color: string; status: string }>);

  return (
    <Card className="border-cyan-500/30 bg-slate-900/80 backdrop-blur-sm shadow-[0_0_15px_rgba(6,182,212,0.15)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-cyan-300 text-sm font-mono">
            📜 CONTRACT
          </CardTitle>
          <div className="flex items-center gap-1.5">
            {revisionCount > 0 && (
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300">
                v{revisionCount + 1}
              </Badge>
            )}
            <Badge
              variant="outline"
              className="border-cyan-500/40 text-cyan-300 bg-cyan-500/10 text-[9px] px-1.5"
            >
              {CONTRACT_STATE_LABELS[contract.state] || contract.state}
            </Badge>
          </div>
        </div>
        <h3 className="text-white font-semibold text-base mt-1">
          {contract.title}
        </h3>
        {contract.description && (
          <p className="text-slate-400 text-xs mt-1">{contract.description}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Budget Indicator */}
        {contract.budget_limit && (
          <div className="p-2 rounded-md bg-slate-800/60 border border-slate-700/30">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <DollarSign className="h-3 w-3 text-green-400" />
                <span className="text-[10px] text-slate-400 font-mono">BUDGET</span>
              </div>
              <span className="text-[10px] text-green-300 font-mono">
                ${contract.budget_limit.toFixed(2)} limit
              </span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  budgetUsed > 80 ? 'bg-red-500' : budgetUsed > 50 ? 'bg-amber-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(budgetUsed, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Todo Progress */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-400">Progress</span>
            <span className="text-slate-300 font-mono">{progressPercent}% ({todoCounts.done}/{todoCounts.total})</span>
          </div>
          <Progress value={progressPercent} className="h-2 bg-slate-800 [&>div]:bg-gradient-to-r [&>div]:from-cyan-500 [&>div]:to-green-500" />
          <div className="flex items-center gap-2 text-[9px]">
            {todoCounts.pending > 0 && <span className="text-yellow-400 font-mono">{todoCounts.pending} pending</span>}
            {todoCounts.in_progress > 0 && <span className="text-cyan-400 font-mono">{todoCounts.in_progress} active</span>}
            {todoCounts.done > 0 && <span className="text-green-400 font-mono">{todoCounts.done} done</span>}
            {todoCounts.failed > 0 && <span className="text-red-400 font-mono">{todoCounts.failed} failed</span>}
            {todoCounts.blocked > 0 && <span className="text-slate-400 font-mono">{todoCounts.blocked} blocked</span>}
          </div>
        </div>

        {/* Todo List */}
        <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar pr-1">
          {contract.todos.map((todo: TodoItem) => {
            const assignedWorker = WORKERS.find((w) => w.id === todo.assigned_to);
            const depNames = todo.depends_on
              .map((depId) => todosById[depId])
              .filter(Boolean)
              .map((dep) => dep.description.slice(0, 30));

            return (
              <div
                key={todo.id}
                className={`p-2 rounded-md bg-slate-800/60 border border-slate-700/30 ${
                  todo.status === 'in_progress' ? 'border-l-2 border-l-cyan-500' :
                  todo.status === 'failed' ? 'border-l-2 border-l-red-500' :
                  todo.status === 'blocked' ? 'border-l-2 border-l-slate-500' : ''
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 flex-shrink-0">
                    {todo.status === 'done' ? (
                      <Check className="h-3.5 w-3.5 text-green-400" />
                    ) : todo.status === 'in_progress' ? (
                      <Loader2 className="h-3.5 w-3.5 text-cyan-400 animate-spin" />
                    ) : todo.status === 'failed' ? (
                      <X className="h-3.5 w-3.5 text-red-400" />
                    ) : todo.status === 'blocked' ? (
                      <AlertTriangle className="h-3.5 w-3.5 text-slate-400" />
                    ) : (
                      <Clock className="h-3.5 w-3.5 text-slate-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-300 leading-tight">
                      {todo.description}
                    </p>
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      {todo.assigned_to && assignedWorker && (
                        <span className="text-[9px] text-cyan-400 font-mono">
                          {assignedWorker.emoji} → {todo.assigned_to}
                        </span>
                      )}
                      {todo.priority && (
                        <Badge
                          variant="outline"
                          className={`text-[8px] px-1 py-0 h-3.5 font-mono ${priorityColors[todo.priority]}`}
                        >
                          {priorityIcons[todo.priority]} {todo.priority}
                        </Badge>
                      )}
                      <Badge
                        variant="outline"
                        className={`text-[9px] px-1 py-0 h-3.5 ${statusColors[todo.status] || ''}`}
                      >
                        {todo.status}
                      </Badge>
                    </div>

                    {/* Dependency Arrows */}
                    {depNames.length > 0 && (
                      <div className="mt-1 flex items-start gap-1">
                        <ArrowRight className="h-2.5 w-2.5 text-slate-500 mt-0.5 flex-shrink-0 rotate-180" />
                        <div className="space-y-0.5">
                          {depNames.map((depName, i) => (
                            <span key={i} className="text-[8px] text-slate-500 block">
                              depends: {depName}{depName.length >= 30 ? '...' : ''}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actual time tracking */}
                    {(todo.estimated_time_ms || todo.actual_time_ms) && (
                      <div className="mt-1 flex items-center gap-1.5">
                        <Clock className="h-2.5 w-2.5 text-slate-500" />
                        {todo.estimated_time_ms && (
                          <span className="text-[8px] text-slate-500 font-mono">
                            est: {(todo.estimated_time_ms / 1000).toFixed(1)}s
                          </span>
                        )}
                        {todo.actual_time_ms && (
                          <span className={`text-[8px] font-mono ${
                            todo.actual_time_ms > (todo.estimated_time_ms || Infinity)
                              ? 'text-red-400'
                              : 'text-green-400'
                          }`}>
                            actual: {(todo.actual_time_ms / 1000).toFixed(1)}s
                          </span>
                        )}
                      </div>
                    )}

                    {/* Error details for failed todos */}
                    {todo.status === 'failed' && todo.error && (
                      <div className="mt-1">
                        <button
                          onClick={() => toggleError(todo.id)}
                          className="flex items-center gap-1 text-[8px] text-red-400/80 hover:text-red-300 transition-colors"
                        >
                          <Eye className="h-2.5 w-2.5" />
                          {expandedErrors.has(todo.id) ? 'Hide Error' : 'View Error Details'}
                          {expandedErrors.has(todo.id) ? (
                            <ChevronDown className="h-2.5 w-2.5" />
                          ) : (
                            <ChevronRight className="h-2.5 w-2.5" />
                          )}
                        </button>
                        {expandedErrors.has(todo.id) && (
                          <div className="mt-1 p-1.5 rounded bg-red-500/10 border border-red-500/20">
                            <pre className="text-[8px] text-red-300/80 font-mono whitespace-pre-wrap break-all">{todo.error}</pre>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Retry button for failed todos */}
                    {todo.status === 'failed' && onRetryTodo && (
                      <button
                        onClick={() => onRetryTodo(todo.id)}
                        className="mt-1 flex items-center gap-1 text-[8px] text-amber-400/80 hover:text-amber-300 transition-colors"
                      >
                        <RefreshCw className="h-2.5 w-2.5" />
                        Retry Task
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Dependency Overview */}
        {todosWithDeps.length > 0 && (
          <div className="p-2 rounded-md bg-slate-800/40 border border-slate-700/20">
            <div className="flex items-center gap-1.5 mb-1">
              <ArrowRight className="h-3 w-3 text-slate-400" />
              <span className="text-[10px] text-slate-400 font-mono">DEPENDENCIES</span>
            </div>
            <div className="space-y-0.5">
              {todosWithDeps.map((todo) => (
                <div key={todo.id} className="flex items-center gap-1 text-[8px]">
                  <span className="text-slate-400 truncate max-w-[80px]">{todo.description.slice(0, 25)}</span>
                  <ArrowRight className="h-2 w-2 text-slate-600" />
                  {todo.depends_on.map((depId) => (
                    <span key={depId} className="text-slate-500 font-mono">
                      {todosById[depId]?.description.slice(0, 20) || depId}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Approval Gates Section */}
        {contractGates.length > 0 && (
          <div className="p-2 rounded-md bg-slate-800/40 border border-slate-700/20">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Shield className="h-3 w-3 text-teal-400" />
              <span className="text-[10px] text-teal-400 font-mono">APPROVAL GATES</span>
            </div>
            <div className="space-y-1">
              {contractGates.map((gate: ApprovalGate) => (
                <div key={gate.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    {gate.status === 'approved' ? (
                      <Check className="h-3 w-3 text-green-400" />
                    ) : gate.status === 'rejected' ? (
                      <X className="h-3 w-3 text-red-400" />
                    ) : (
                      <Clock className="h-3 w-3 text-amber-400" />
                    )}
                    <span className="text-[9px] text-slate-300 font-mono">{gate.gate_type}</span>
                    <span className="text-[8px] text-slate-500">by {gate.approver}</span>
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-[8px] px-1 py-0 h-3.5 ${
                      gate.status === 'approved' ? 'border-green-500/30 text-green-300' :
                      gate.status === 'rejected' ? 'border-red-500/30 text-red-300' :
                      gate.status === 'skipped' ? 'border-slate-600/30 text-slate-400' :
                      'border-amber-500/30 text-amber-300'
                    }`}
                  >
                    {gate.status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Team Approval Status */}
        {Object.keys(workerVotes).length > 0 && (
          <div className="p-2 rounded-md bg-slate-800/40 border border-slate-700/20">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Shield className="h-3 w-3 text-violet-400" />
              <span className="text-[10px] text-violet-400 font-mono">TEAM APPROVAL</span>
              {contract.team_approved && (
                <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-green-500/30 text-green-300">
                  ✓ Approved
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.values(workerVotes).map((vote) => (
                <div
                  key={vote.name}
                  className="flex items-center gap-1 px-1.5 py-0.5 rounded border border-slate-700/30 bg-slate-900/60"
                >
                  <span className="text-[10px]">{vote.emoji}</span>
                  <span className="text-[9px] font-mono" style={{ color: vote.color }}>{vote.name}</span>
                  {vote.status === 'approved' ? (
                    <Check className="h-2.5 w-2.5 text-green-400" />
                  ) : vote.status === 'rejected' ? (
                    <X className="h-2.5 w-2.5 text-red-400" />
                  ) : (
                    <Clock className="h-2.5 w-2.5 text-slate-500" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Revision History Indicator */}
        {revisionCount > 0 && (
          <div className="flex items-center gap-1.5 text-[9px] text-slate-500">
            <RotateCcw className="h-3 w-3" />
            <span className="font-mono">{revisionCount} revision{revisionCount > 1 ? 's' : ''}</span>
          </div>
        )}

        {/* Revision Inline Dialog */}
        {showRevisionDialog && (
          <div className="p-2.5 rounded-md bg-amber-500/10 border border-amber-500/30 space-y-2">
            <div className="flex items-center gap-1.5">
              <RotateCcw className="h-3 w-3 text-amber-400" />
              <span className="text-[10px] text-amber-400 font-mono font-semibold">REVISION REQUEST</span>
            </div>
            <Textarea
              value={revisionText}
              onChange={(e) => setRevisionText(e.target.value)}
              placeholder="Describe what you'd like to revise..."
              className="min-h-[60px] text-xs bg-slate-900/80 border-slate-700/50 text-slate-200 placeholder:text-slate-600 resize-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  handleSubmitRevision();
                }
                if (e.key === 'Escape') {
                  setShowRevisionDialog(false);
                  setRevisionText('');
                }
              }}
            />
            <div className="flex gap-2">
              <Button
                onClick={handleSubmitRevision}
                size="sm"
                disabled={!revisionText.trim()}
                className="flex-1 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white border-0 text-xs"
              >
                Submit Revision
              </Button>
              <Button
                onClick={() => { setShowRevisionDialog(false); setRevisionText(''); }}
                size="sm"
                variant="outline"
                className="border-slate-600/50 text-slate-400 hover:bg-slate-800/50 text-xs"
              >
                Cancel
              </Button>
            </div>
            <span className="text-[8px] text-slate-600">Ctrl+Enter to submit · Esc to cancel</span>
          </div>
        )}

        {/* Actions */}
        {contract.state === 'contract_presented' && !isWorking && !showRevisionDialog && (
          <div className="flex gap-2 pt-1">
            <Button
              onClick={onAccept}
              size="sm"
              className="flex-1 bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white border-0 text-xs"
            >
              <Check className="h-3.5 w-3.5 mr-1" />
              Accept
            </Button>
            <Button
              onClick={() => setShowRevisionDialog(true)}
              size="sm"
              variant="outline"
              className="flex-1 border-amber-500/40 text-amber-300 hover:bg-amber-500/10 text-xs"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" />
              Revise
            </Button>
            <Button
              onClick={onReject}
              size="sm"
              variant="outline"
              className="border-red-500/40 text-red-300 hover:bg-red-500/10 text-xs"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {/* Working indicator */}
        {isWorking && (
          <div className="flex items-center gap-2 text-xs text-cyan-400 pt-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span className="font-mono">Executing contract...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
});
