'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  CheckCircle2, AlertTriangle, Lightbulb,
  Clock, DollarSign, User, FileText,
} from 'lucide-react';

export function DebriefSection() {
  const { debriefResult, contract, workers } = useKantorkuStore();

  if (!debriefResult) return null;

  const getWorkerEmoji = (id: string) => {
    const w = workers.find((wk) => wk.id === id);
    return w?.emoji || '🤖';
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <div className="space-y-2">
      {/* Stats */}
      <div className="grid grid-cols-2 gap-1.5">
        <div className="text-center p-1.5 rounded bg-slate-900/60">
          <p className="text-xs font-bold text-cyan-300 font-mono">
            {formatDuration(debriefResult.total_duration_ms)}
          </p>
          <p className="text-[8px] text-slate-500">Durasi</p>
        </div>
        <div className="text-center p-1.5 rounded bg-slate-900/60">
          <p className="text-xs font-bold text-green-300 font-mono">
            ${debriefResult.total_cost.toFixed(4)}
          </p>
          <p className="text-[8px] text-slate-500">Biaya</p>
        </div>
      </div>

      {/* What Went Well */}
      {debriefResult.what_went_well.length > 0 && (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1">
            <CheckCircle2 className="h-2.5 w-2.5 text-green-400" />
            <span className="text-[9px] text-green-400 font-mono font-semibold">BERJALAN BAIK</span>
          </div>
          {debriefResult.what_went_well.map((item, i) => (
            <div key={i} className="flex items-start gap-1.5 ml-3">
              <div className="h-1 w-1 rounded-full bg-green-400 mt-1 flex-shrink-0" />
              <span className="text-[9px] text-slate-300">{item}</span>
            </div>
          ))}
        </div>
      )}

      {/* Improvements */}
      {debriefResult.what_could_improve.length > 0 && (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1">
            <AlertTriangle className="h-2.5 w-2.5 text-amber-400" />
            <span className="text-[9px] text-amber-400 font-mono font-semibold">PERLU DIPERBAIKI</span>
          </div>
          {debriefResult.what_could_improve.map((item, i) => (
            <div key={i} className="flex items-start gap-1.5 ml-3">
              <div className="h-1 w-1 rounded-full bg-amber-400 mt-1 flex-shrink-0" />
              <span className="text-[9px] text-slate-300">{item}</span>
            </div>
          ))}
        </div>
      )}

      {/* Lessons */}
      {debriefResult.lessons_learned.length > 0 && (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1">
            <Lightbulb className="h-2.5 w-2.5 text-cyan-400" />
            <span className="text-[9px] text-cyan-400 font-mono font-semibold">PELAJARAN</span>
          </div>
          {debriefResult.lessons_learned.map((item, i) => (
            <div key={i} className="flex items-start gap-1.5 ml-3">
              <div className="h-1 w-1 rounded-full bg-cyan-400 mt-1 flex-shrink-0" />
              <span className="text-[9px] text-slate-300">{item}</span>
            </div>
          ))}
        </div>
      )}

      {/* Worker Feedback */}
      {Object.keys(debriefResult.worker_feedback).length > 0 && (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1">
            <User className="h-2.5 w-2.5 text-violet-400" />
            <span className="text-[9px] text-violet-400 font-mono font-semibold">FEEDBACK WORKER</span>
          </div>
          {Object.entries(debriefResult.worker_feedback).map(([workerId, feedback]) => (
            <div key={workerId} className="ml-3 flex items-start gap-1">
              <span className="text-[9px]">{getWorkerEmoji(workerId)}</span>
              <span className="text-[9px] text-slate-300">{feedback}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
