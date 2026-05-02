'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useKantorkuStore } from '@/lib/kantorku/store';
import {
  Layers,
  Activity,
  Clock,
  Database,
  Zap,
  Inbox,
  CircleDot,
  Loader2,
} from 'lucide-react';

// ── Pool Worker Instance Types ──────────────────────────────────────
interface PoolWorkerState {
  id: number;
  status: 'idle' | 'fetching' | 'delivering';
  currentTask?: string;
  latencyMs?: number;
  fetchType?: 'proactive' | 'reactive';
}

// ── Queue Item Types ────────────────────────────────────────────────
interface QueueItem {
  id: string;
  type: 'prefetch' | 'reactive';
  query: string;
  workerId?: string;
}

// ── Derive pool state from store ────────────────────────────────────
function getPoolState(): {
  workers: PoolWorkerState[];
  queue: QueueItem[];
  avgDeliveryMs: number;
} {
  const store = useKantorkuStore.getState();
  const { latencyHistory, workers, contractState, officeEvents } = store;

  // Derive context delivery time from latency history
  const contextLatencies = latencyHistory.filter((l) => l.worker_id === 'context_pool');
  const avgDeliveryMs = contextLatencies.length > 0
    ? contextLatencies.reduce((s, l) => s + l.latency_ms, 0) / contextLatencies.length
    : 0;

  // Simulate pool worker states based on contract state
  const isActive = contractState === 'working' || contractState === 'team_consult';
  const activeWorkers = workers.filter((w) => w.status === 'busy').length;

  const poolWorkers: PoolWorkerState[] = [
    {
      id: 0,
      status: isActive && activeWorkers > 0 ? 'fetching' : 'idle',
      currentTask: isActive && activeWorkers > 0 ? 'context:codebase' : undefined,
      latencyMs: avgDeliveryMs || (isActive ? Math.random() * 800 + 200 : 0),
      fetchType: 'proactive',
    },
    {
      id: 1,
      status: isActive && activeWorkers > 1 ? 'delivering' : 'idle',
      currentTask: isActive && activeWorkers > 1 ? 'context:patterns' : undefined,
      latencyMs: avgDeliveryMs || (isActive ? Math.random() * 600 + 150 : 0),
      fetchType: 'reactive',
    },
    {
      id: 2,
      status: 'idle',
      latencyMs: 0,
    },
  ];

  // Simulate queue items
  const queue: QueueItem[] = isActive ? [
    { id: 'q-1', type: 'prefetch', query: 'WebSocket reconnect patterns' },
    { id: 'q-2', type: 'reactive', query: 'Rate limiter implementation', workerId: 'coder_backend' },
  ] : [];

  return { workers: poolWorkers, queue, avgDeliveryMs };
}

const statusColors: Record<PoolWorkerState['status'], string> = {
  idle: '#64748b',
  fetching: '#06b6d4',
  delivering: '#10b981',
};

const statusLabels: Record<PoolWorkerState['status'], string> = {
  idle: 'Idle',
  fetching: 'Fetching',
  delivering: 'Delivering',
};

export function ContextPoolPanel() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const workers = useKantorkuStore((s) => s.workers);

  // Compute pool state reactively
  const poolState = useMemo(() => getPoolState(), [contractState, workers]);

  return (
    <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
      <CardHeader className="p-2.5 pb-1">
        <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
          <Layers className="h-3 w-3 text-violet-400" />
          CONTEXT POOL (DeepSeek)
        </CardTitle>
      </CardHeader>
      <CardContent className="p-2.5 pt-1 space-y-2">
        {/* Pool Worker Instances */}
        <div className="grid grid-cols-3 gap-1.5">
          {poolState.workers.map((pw) => (
            <div
              key={`pool-${pw.id}`}
              className={`p-1.5 rounded-md border ${
                pw.status === 'fetching'
                  ? 'border-cyan-500/30 bg-cyan-500/5'
                  : pw.status === 'delivering'
                  ? 'border-green-500/30 bg-green-500/5'
                  : 'border-slate-700/30 bg-slate-900/40'
              } transition-all duration-300`}
            >
              <div className="flex items-center gap-1 mb-1">
                <div
                  className={`h-2 w-2 rounded-full ${
                    pw.status === 'fetching' ? 'bg-cyan-400 animate-pulse' :
                    pw.status === 'delivering' ? 'bg-green-400' :
                    'bg-slate-600'
                  }`}
                  style={pw.status !== 'idle' ? { boxShadow: `0 0 4px ${statusColors[pw.status]}60` } : undefined}
                />
                <span className="text-[8px] font-mono text-slate-400">Worker {pw.id}</span>
              </div>
              <div className="flex items-center gap-1">
                <Badge
                  variant="outline"
                  className="text-[7px] px-0.5 py-0 h-3"
                  style={{
                    borderColor: `${statusColors[pw.status]}40`,
                    color: statusColors[pw.status],
                  }}
                >
                  {statusLabels[pw.status]}
                </Badge>
                {pw.fetchType && (
                  <Badge
                    variant="outline"
                    className={`text-[7px] px-0.5 py-0 h-3 ${
                      pw.fetchType === 'proactive'
                        ? 'border-amber-500/30 text-amber-300'
                        : 'border-violet-500/30 text-violet-300'
                    }`}
                  >
                    {pw.fetchType === 'proactive' ? '⚡' : '🔄'}
                  </Badge>
                )}
              </div>
              {pw.latencyMs > 0 && (
                <div className="flex items-center gap-0.5 mt-1">
                  <Clock className="h-2 w-2 text-slate-500" />
                  <span className="text-[7px] font-mono text-slate-500">{pw.latencyMs.toFixed(0)}ms</span>
                </div>
              )}
              {pw.currentTask && (
                <p className="text-[7px] text-slate-500 truncate mt-0.5">{pw.currentTask}</p>
              )}
            </div>
          ))}
        </div>

        {/* FIFO Queue */}
        <div className="p-1.5 rounded-md bg-slate-900/60 border border-slate-700/20">
          <div className="flex items-center gap-1 mb-1">
            <Inbox className="h-2.5 w-2.5 text-violet-400" />
            <span className="text-[8px] font-mono text-violet-400">FIFO QUEUE</span>
            <Badge variant="outline" className="text-[7px] px-0.5 py-0 h-3 border-slate-600/30 text-slate-400 ml-auto">
              {poolState.queue.length} pending
            </Badge>
          </div>
          {poolState.queue.length > 0 ? (
            <div className="space-y-0.5 max-h-16 overflow-y-auto custom-scrollbar">
              {poolState.queue.map((item) => (
                <div key={item.id} className="flex items-center gap-1 text-[8px]">
                  <CircleDot className={`h-2 w-2 flex-shrink-0 ${
                    item.type === 'prefetch' ? 'text-amber-400' : 'text-violet-400'
                  }`} />
                  <span className="text-slate-400 font-mono truncate">{item.query}</span>
                  {item.workerId && (
                    <span className="text-slate-600 font-mono ml-auto flex-shrink-0">→ {item.workerId}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[8px] text-slate-600">Queue empty — pool workers on standby.</p>
          )}
        </div>

        {/* Delivery Metrics */}
        <div className="grid grid-cols-3 gap-1.5">
          <div className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20 text-center">
            <Activity className="h-2.5 w-2.5 text-cyan-400 mx-auto mb-0.5" />
            <p className="text-[9px] font-bold font-mono text-cyan-300">{poolState.avgDeliveryMs.toFixed(0)}ms</p>
            <p className="text-[7px] text-slate-600">Avg Delivery</p>
          </div>
          <div className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20 text-center">
            <Database className="h-2.5 w-2.5 text-green-400 mx-auto mb-0.5" />
            <p className="text-[9px] font-bold font-mono text-green-300">Ring 1</p>
            <p className="text-[7px] text-slate-600">Cache Store</p>
          </div>
          <div className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20 text-center">
            <Zap className="h-2.5 w-2.5 text-amber-400 mx-auto mb-0.5" />
            <p className="text-[9px] font-bold font-mono text-amber-300">3</p>
            <p className="text-[7px] text-slate-600">Pool Size</p>
          </div>
        </div>

        {/* Fetch type legend */}
        <div className="flex items-center gap-3 text-[8px] text-slate-500">
          <div className="flex items-center gap-1">
            <span className="text-amber-400">⚡</span>
            <span>Proactive (prefetch)</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-violet-400">🔄</span>
            <span>Reactive (on-demand)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
