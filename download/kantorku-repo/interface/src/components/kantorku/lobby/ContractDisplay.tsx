'use client';

import { Contract, TodoItem, ApprovalGate } from '@/lib/kantorku/types';
import { CONTRACT_STATE_LABELS, WORKERS } from '@/lib/kantorku/workers-data';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Check, RotateCcw, X, Clock, Loader2, ArrowRight, DollarSign, AlertTriangle, Shield, ChevronDown, ChevronRight, RefreshCw, Eye } from 'lucide-react';
import React, { useState, useCallback } from 'react';
import { Textarea } from '@/components/ui/textarea';

interface ContractDisplayProps {
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

export const ContractDisplay = React.memo(function ContractDisplay({ contract, onAccept, onRevise, onReject, onRetryTodo, isWorking }: ContractDisplayProps) {
  const [showRevisionDialog, setShowRevisionDialog] = useState(false);
  const [revisionText, setRevisionText] = useState('');
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());

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

  const revisionCount = contract.team_feedback_rounds?.length || 0;

  return (
    <div className="space-y-2">
      {/* Title + State */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white truncate flex-1">{contract.title}</h3>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {revisionCount > 0 && (
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300">
              v{revisionCount + 1}
            </Badge>
          )}
          <Badge variant="outline" className="border-cyan-500/40 text-cyan-300 bg-cyan-500/10 text-[9px] px-1.5">
            {CONTRACT_STATE_LABELS[contract.state] || contract.state}
          </Badge>
        </div>
      </div>

      {/* Budget */}
      {contract.budget_limit && (
        <div className="p-1.5 rounded-md bg-slate-800/60 border border-slate-700/30">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1">
              <DollarSign className="h-2.5 w-2.5 text-green-400" />
              <span className="text-[9px] text-slate-400 font-mono">BUDGET</span>
            </div>
            <span className="text-[9px] text-green-300 font-mono">${contract.budget_limit.toFixed(2)}</span>
          </div>
          <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-green-500" style={{ width: '10%' }} />
          </div>
        </div>
      )}

      {/* Progress */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[9px]">
          <span className="text-slate-400">Progres</span>
          <span className="text-slate-300 font-mono">{progressPercent}% ({todoCounts.done}/{todoCounts.total})</span>
        </div>
        <Progress value={progressPercent} className="h-1.5 bg-slate-800 [&>div]:bg-gradient-to-r [&>div]:from-cyan-500 [&>div]:to-green-500" />
      </div>

      {/* Actions */}
      {contract.state === 'contract_presented' && !isWorking && !showRevisionDialog && (
        <div className="flex gap-1.5">
          <Button onClick={onAccept} size="sm" className="flex-1 bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white border-0 text-[10px] h-6">
            <Check className="h-3 w-3 mr-1" />Terima
          </Button>
          <Button onClick={() => setShowRevisionDialog(true)} size="sm" variant="outline" className="flex-1 border-amber-500/40 text-amber-300 hover:bg-amber-500/10 text-[10px] h-6">
            <RotateCcw className="h-3 w-3 mr-1" />Revisi
          </Button>
          <Button onClick={onReject} size="sm" variant="outline" className="border-red-500/40 text-red-300 hover:bg-red-500/10 text-[10px] h-6 px-2">
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}

      {isWorking && (
        <div className="flex items-center gap-1.5 text-[10px] text-cyan-400">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span className="font-mono">Menjalankan kontrak...</span>
        </div>
      )}

      {/* Revision dialog */}
      {showRevisionDialog && (
        <div className="p-2 rounded-md bg-amber-500/10 border border-amber-500/30 space-y-1.5">
          <Textarea
            value={revisionText}
            onChange={(e) => setRevisionText(e.target.value)}
            placeholder="Deskripsikan revisi yang diinginkan..."
            className="min-h-[40px] text-[11px] bg-slate-900/80 border-slate-700/50 text-slate-200 placeholder:text-slate-600 resize-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmitRevision();
              if (e.key === 'Escape') { setShowRevisionDialog(false); setRevisionText(''); }
            }}
          />
          <div className="flex gap-1.5">
            <Button onClick={handleSubmitRevision} size="sm" disabled={!revisionText.trim()} className="flex-1 bg-amber-600 hover:bg-amber-500 text-white text-[10px] h-5">
              Kirim Revisi
            </Button>
            <Button onClick={() => { setShowRevisionDialog(false); setRevisionText(''); }} size="sm" variant="outline" className="border-slate-600/50 text-slate-400 text-[10px] h-5">
              Batal
            </Button>
          </div>
        </div>
      )}
    </div>
  );
});
