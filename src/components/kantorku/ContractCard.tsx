'use client';

import { Contract, TodoItem } from '@/lib/kantorku/types';
import { CONTRACT_STATE_LABELS } from '@/lib/kantorku/workers-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Check, RotateCcw, X, Clock, Loader2 } from 'lucide-react';

interface ContractCardProps {
  contract: Contract;
  onAccept: () => void;
  onRevise: (feedback: string) => void;
  onReject: () => void;
  isWorking: boolean;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  in_progress: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  done: 'bg-green-500/20 text-green-300 border-green-500/30',
  failed: 'bg-red-500/20 text-red-300 border-red-500/30',
};

export function ContractCard({ contract, onAccept, onRevise, onReject, isWorking }: ContractCardProps) {
  const todoCounts = {
    total: contract.todos.length,
    pending: contract.todos.filter((t) => t.status === 'pending').length,
    in_progress: contract.todos.filter((t) => t.status === 'in_progress').length,
    done: contract.todos.filter((t) => t.status === 'done').length,
    failed: contract.todos.filter((t) => t.status === 'failed').length,
  };

  return (
    <Card className="border-cyan-500/30 bg-slate-900/80 backdrop-blur-sm shadow-[0_0_15px_rgba(6,182,212,0.15)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-cyan-300 text-sm font-mono">
            📜 CONTRACT
          </CardTitle>
          <Badge
            variant="outline"
            className="border-cyan-500/40 text-cyan-300 bg-cyan-500/10 text-xs"
          >
            {CONTRACT_STATE_LABELS[contract.state] || contract.state}
          </Badge>
        </div>
        <h3 className="text-white font-semibold text-base mt-1">
          {contract.title}
        </h3>
        {contract.description && (
          <p className="text-slate-400 text-xs mt-1">{contract.description}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Todo Progress */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-green-500 rounded-full transition-all duration-500"
              style={{
                width: `${
                  todoCounts.total
                    ? (todoCounts.done / todoCounts.total) * 100
                    : 0
                }%`,
              }}
            />
          </div>
          <span className="text-slate-400 font-mono">
            {todoCounts.done}/{todoCounts.total}
          </span>
        </div>

        {/* Todo List */}
        <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar pr-1">
          {contract.todos.map((todo: TodoItem) => (
            <div
              key={todo.id}
              className="flex items-start gap-2 p-2 rounded-md bg-slate-800/60 border border-slate-700/30"
            >
              <div className="mt-0.5">
                {todo.status === 'done' ? (
                  <Check className="h-3.5 w-3.5 text-green-400" />
                ) : todo.status === 'in_progress' ? (
                  <Loader2 className="h-3.5 w-3.5 text-cyan-400 animate-spin" />
                ) : todo.status === 'failed' ? (
                  <X className="h-3.5 w-3.5 text-red-400" />
                ) : (
                  <Clock className="h-3.5 w-3.5 text-slate-500" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-300 leading-tight">
                  {todo.description}
                </p>
                <div className="flex items-center gap-1.5 mt-1">
                  {todo.assigned_to && (
                    <span className="text-[10px] text-cyan-400 font-mono">
                      → {todo.assigned_to}
                    </span>
                  )}
                  <Badge
                    variant="outline"
                    className={`text-[9px] px-1 py-0 h-4 ${statusColors[todo.status] || ''}`}
                  >
                    {todo.status}
                  </Badge>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Team Approval */}
        {contract.team_approved && (
          <div className="flex items-center gap-1.5 text-xs text-green-400">
            <Check className="h-3.5 w-3.5" />
            <span>Team Approved</span>
          </div>
        )}

        {/* Actions */}
        {contract.state === 'contract_presented' && !isWorking && (
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
              onClick={() => {
                const feedback = prompt('What would you like to revise?');
                if (feedback) onRevise(feedback);
              }}
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
      </CardContent>
    </Card>
  );
}
