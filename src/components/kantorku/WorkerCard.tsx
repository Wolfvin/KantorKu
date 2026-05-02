'use client';

import { WorkerIdentity } from '@/lib/kantorku/types';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface WorkerCardProps {
  worker: WorkerIdentity;
  compact?: boolean;
}

const statusStyles: Record<string, { dot: string; bg: string; text: string }> = {
  idle: { dot: 'bg-slate-500', bg: 'bg-slate-800/60', text: 'text-slate-400' },
  busy: { dot: 'bg-cyan-400 animate-pulse', bg: 'bg-cyan-950/40', text: 'text-cyan-300' },
  error: { dot: 'bg-red-400', bg: 'bg-red-950/40', text: 'text-red-300' },
  offline: { dot: 'bg-slate-700', bg: 'bg-slate-900/60', text: 'text-slate-600' },
};

export function WorkerCard({ worker, compact = false }: WorkerCardProps) {
  const style = statusStyles[worker.status || 'idle'] || statusStyles.idle;

  if (compact) {
    return (
      <div
        className={`flex items-center gap-2 px-2 py-1.5 rounded-md ${style.bg} border border-slate-700/30 transition-all duration-300`}
        style={{
          boxShadow: worker.status === 'busy' ? `0 0 8px ${worker.color}33` : 'none',
        }}
      >
        <span className="text-sm">{worker.emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            <span className="text-xs font-mono text-slate-300 truncate">
              {worker.id}
            </span>
          </div>
          {worker.current_task && (
            <p className="text-[9px] text-slate-500 truncate mt-0.5">
              {worker.current_task}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <Card
      className={`${style.bg} border-slate-700/30 backdrop-blur-sm transition-all duration-300 hover:border-slate-600/50`}
      style={{
        boxShadow: worker.status === 'busy' ? `0 0 12px ${worker.color}22` : 'none',
      }}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-2.5">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-lg text-lg"
            style={{ backgroundColor: `${worker.color}20` }}
          >
            {worker.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${style.dot}`} />
              <span className="text-sm font-mono text-white font-medium">
                {worker.id}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">{worker.role}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <Badge
                variant="outline"
                className="text-[9px] px-1.5 py-0 h-4 border-slate-600/50 text-slate-500"
              >
                {worker.squad}
              </Badge>
              <Badge
                variant="outline"
                className={`text-[9px] px-1.5 py-0 h-4 ${style.text}`}
                style={{ borderColor: `${worker.color}40` }}
              >
                {worker.status || 'idle'}
              </Badge>
            </div>
            {worker.current_task && (
              <p className="text-[10px] text-cyan-400/80 mt-1.5 truncate font-mono">
                ⚡ {worker.current_task}
              </p>
            )}
            <p className="text-[9px] text-slate-600 mt-1 truncate" title={worker.model}>
              {worker.model}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
