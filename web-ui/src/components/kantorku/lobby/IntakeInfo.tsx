'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Zap } from 'lucide-react';

export function IntakeInfo() {
  const { intakeResult } = useKantorkuStore();

  if (!intakeResult) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-slate-800/60 border border-slate-700/30" role="region" aria-label="Intake information">
      <div className="flex items-center gap-1.5 mb-1">
        <Zap className="h-3 w-3 text-amber-400" />
        <span className="text-[10px] text-amber-400 font-mono font-semibold">INTAKE</span>
      </div>
      <div className="flex flex-wrap gap-1">
        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300">
          {intakeResult.type}
        </Badge>
        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-cyan-500/30 text-cyan-300">
          {intakeResult.urgency}
        </Badge>
        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-violet-500/30 text-violet-300">
          {intakeResult.estimated_complexity}
        </Badge>
        {intakeResult.estimated_workers && intakeResult.estimated_workers.length > 0 && (
          <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-teal-500/30 text-teal-300">
            ~{intakeResult.estimated_workers.length} workers
          </Badge>
        )}
        {intakeResult.estimated_duration_ms && (
          <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-500/30 text-slate-300">
            ~{(intakeResult.estimated_duration_ms / 1000).toFixed(0)}s
          </Badge>
        )}
      </div>
      {intakeResult.summary && (
        <p className="text-[9px] text-slate-500 mt-1">{intakeResult.summary}</p>
      )}
    </div>
  );
}
