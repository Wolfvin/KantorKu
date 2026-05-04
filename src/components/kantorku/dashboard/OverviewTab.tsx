'use client';

import { useMemo } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import {
  DollarSign,
  Activity,
  Cpu,
  Zap,
  Clock,
  CheckCircle2,
  Timer,
} from 'lucide-react';
import { SQUADS, WORKERS } from '@/lib/kantorku/workers-data';

function computePercentiles(values: number[]): { p50: number; p95: number; p99: number; avg: number } {
  if (values.length === 0) return { p50: 0, p95: 0, p99: 0, avg: 0 };
  const sorted = [...values].sort((a, b) => a - b);
  const p = (pct: number) => sorted[Math.floor(sorted.length * pct)];
  const avg = sorted.reduce((s, v) => s + v, 0) / sorted.length;
  return { p50: p(0.5), p95: p(0.95), p99: p(0.99), avg };
}

export function OverviewTab() {
  const {
    costReport,
    workers,
    officeEvents,
    contractState,
    metricsSummary,
    sessions,
    latencyHistory,
  } = useKantorkuStore();

  const computedPercentiles = useMemo(() => {
    const values = latencyHistory.map((e) => e.latency_ms).filter((v) => v > 0);
    return computePercentiles(values);
  }, [latencyHistory]);

  const totalCost = costReport?.total_cost || 0;
  const totalTokens = costReport
    ? costReport.total_input_tokens + costReport.total_output_tokens
    : 0;
  const totalEvents = officeEvents.length;
  const avgLatency = computedPercentiles.avg || (metricsSummary?.avg_latency_ms ?? 0);
  const successRate = metricsSummary?.success_rate ?? 0;
  const activeWorkers = workers.filter((w) => w.status === 'busy').length;

  const costByModel = costReport
    ? Object.entries(costReport.by_model).map(([model, data]) => ({
        model: model.split('/').pop() || model,
        cost: Number(data.cost.toFixed(4)),
        calls: data.calls,
        tokens: data.tokens,
      }))
    : [];

  const costByWorker = costReport
    ? Object.entries(costReport.by_worker).map(([workerId, data]) => {
        const w = WORKERS.find((wk) => wk.id === workerId);
        return {
          worker: w ? `${w.emoji} ${workerId}` : workerId,
          cost: Number(data.cost.toFixed(4)),
          calls: data.calls,
          tokens: data.tokens,
          color: w?.color || '#94a3b8',
        };
      })
    : [];

  const tokenData = costReport
    ? Object.entries(costReport.by_model).map(([model, data]) => ({
        model: model.split('/').pop() || model,
        tokens: data.tokens,
      }))
    : [];

  const workerStatusData = [
    { name: 'Idle', value: workers.filter((w) => w.status === 'idle').length, color: '#64748b' },
    { name: 'Busy', value: workers.filter((w) => w.status === 'busy').length, color: '#06b6d4' },
    { name: 'Error', value: workers.filter((w) => w.status === 'error').length, color: '#ef4444' },
    { name: 'Offline', value: workers.filter((w) => w.status === 'offline').length, color: '#334155' },
  ].filter((d) => d.value > 0);

  const squadData = SQUADS.map((s) => ({
    name: s.label,
    workers: workers.filter((w) => w.squad === s.id).length,
    color: s.color,
  }));

  const eventTypeCounts: Record<string, number> = {};
  officeEvents.forEach((e) => {
    eventTypeCounts[e.type] = (eventTypeCounts[e.type] || 0) + 1;
  });
  const eventData = Object.entries(eventTypeCounts)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  const latencyData = latencyHistory.slice(-30).map((entry) => ({
    time: new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    latency: entry.latency_ms,
    worker: entry.worker_id || '',
  }));

  const chartTooltipStyle = {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    fontSize: '10px',
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
      {/* Key Metrics Row */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { icon: DollarSign, color: 'text-green-400', value: `$${totalCost.toFixed(4)}`, label: 'Total Cost' },
          { icon: Cpu, color: 'text-cyan-400', value: totalTokens > 1000 ? `${(totalTokens / 1000).toFixed(1)}k` : String(totalTokens), label: 'Total Tokens' },
          { icon: Activity, color: 'text-amber-400', value: String(totalEvents), label: 'Events' },
          { icon: Clock, color: 'text-violet-400', value: `${avgLatency.toFixed(0)}ms`, label: 'Avg Latency' },
          { icon: CheckCircle2, color: 'text-green-400', value: `${(successRate * 100).toFixed(1)}%`, label: 'Success Rate' },
          { icon: Zap, color: 'text-cyan-400', value: `${activeWorkers}/${workers.length}`, label: 'Active Workers' },
        ].map(({ icon: Icon, color, value, label }) => (
          <div key={label} className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/30 text-center">
            <Icon className={`h-3.5 w-3.5 ${color} mx-auto mb-1`} />
            <p className={`text-sm font-bold font-mono ${color.replace('400', '300')}`}>{value}</p>
            <p className="text-[10px] text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Cost by Model Chart */}
      {costByModel.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <DollarSign className="h-3 w-3 text-green-400" />
              COST BY MODEL
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={costByModel} barSize={16}>
                <XAxis dataKey="model" tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                <YAxis tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={35} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: '#94a3b8' }} />
                <Bar dataKey="cost" fill="#10b981" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Cost by Worker Chart */}
      {costByWorker.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Cpu className="h-3 w-3 text-cyan-400" />
              COST BY WORKER
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={costByWorker} barSize={14}>
                <XAxis dataKey="worker" tick={{ fontSize: 7, fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                <YAxis tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={35} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: '#94a3b8' }} />
                <Bar dataKey="cost" radius={[2, 2, 0, 0]}>
                  {costByWorker.map((entry, idx) => (
                    <Cell key={`cw-${idx}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Token Usage Chart */}
      {tokenData.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Zap className="h-3 w-3 text-cyan-400" />
              TOKEN USAGE
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={tokenData} barSize={16}>
                <XAxis dataKey="model" tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                <YAxis tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={35} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="tokens" fill="#06b6d4" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Worker Status Pie */}
      {workerStatusData.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Activity className="h-3 w-3 text-violet-400" />
              WORKER STATUS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <div className="flex items-center gap-4">
              <ResponsiveContainer width={80} height={80}>
                <PieChart>
                  <Pie data={workerStatusData} cx="50%" cy="50%" innerRadius={20} outerRadius={35} dataKey="value" stroke="none">
                    {workerStatusData.map((entry, idx) => (
                      <Cell key={`ws-${idx}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1">
                {workerStatusData.map((d) => (
                  <div key={d.name} className="flex items-center gap-1.5">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                    <span className="text-[10px] text-slate-400">{d.name}: {d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Squad Distribution */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Cpu className="h-3 w-3 text-amber-400" />
            SQUAD DISTRIBUTION
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1">
          <ResponsiveContainer width="100%" height={80}>
            <BarChart data={squadData} layout="vertical" barSize={10}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={70} />
              <Bar dataKey="workers" radius={[0, 2, 2, 0]}>
                {squadData.map((entry, idx) => (
                  <Cell key={`sq-${idx}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Event Type Chart */}
      {eventData.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400">EVENT DISTRIBUTION</CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <ResponsiveContainer width="100%" height={100}>
              <BarChart data={eventData} barSize={12}>
                <XAxis dataKey="type" tick={{ fontSize: 6, fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} tickLine={false} angle={-30} textAnchor="end" height={30} />
                <YAxis tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={20} />
                <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Latency History Line Chart */}
      {latencyData.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Clock className="h-3 w-3 text-violet-400" />
              LATENCY HISTORY
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <ResponsiveContainer width="100%" height={100}>
              <LineChart data={latencyData}>
                <XAxis dataKey="time" tick={{ fontSize: 7, fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                <YAxis tick={{ fontSize: 8, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: '#94a3b8' }} />
                <Line type="monotone" dataKey="latency" stroke="#8b5cf6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Active Sessions List */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Zap className="h-3 w-3 text-cyan-400" />
            SESSIONS ({sessions.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 space-y-1 max-h-32 overflow-y-auto custom-scrollbar">
          {sessions.length > 0 ? sessions.map((s) => (
            <div key={s.session_id} className="flex items-center justify-between py-1 border-t border-slate-700/20 first:border-0">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-400 font-mono truncate max-w-[100px]">{s.session_id}</span>
                <span className="text-[9px] text-slate-500 truncate max-w-[80px]">{s.contract_title}</span>
              </div>
              <Badge variant="outline" className={`text-[8px] px-1 py-0 h-3.5 ${
                s.state === 'working' ? 'border-cyan-500/30 text-cyan-300' :
                s.state === 'done' ? 'border-green-500/30 text-green-300' :
                'border-slate-600/30 text-slate-400'
              }`}>
                {s.state}
              </Badge>
            </div>
          )) : (
            <p className="text-[9px] text-slate-600">No sessions yet. Start a conversation to create one.</p>
          )}
        </CardContent>
      </Card>

      {/* Metrics Summary Card */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Timer className="h-3 w-3 text-cyan-400" />
            LATENCY PERCENTILES (from {latencyHistory.length} samples)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 space-y-1">
          {[
            { label: 'Avg Latency', value: `${computedPercentiles.avg.toFixed(1)}ms`, color: 'text-slate-300' },
            { label: 'P50 Latency', value: `${computedPercentiles.p50.toFixed(1)}ms`, color: 'text-cyan-300' },
            { label: 'P95 Latency', value: `${computedPercentiles.p95.toFixed(1)}ms`, color: 'text-amber-300' },
            { label: 'P99 Latency', value: `${computedPercentiles.p99.toFixed(1)}ms`, color: 'text-red-300' },
            { label: 'Success Rate', value: `${((metricsSummary?.success_rate ?? 0) * 100).toFixed(1)}%`, color: 'text-green-300' },
            { label: 'Total Calls', value: String(metricsSummary?.total_calls ?? latencyHistory.length), color: 'text-slate-300' },
          ].map(({ label, value, color }) => (
            <div key={label} className="flex justify-between text-[10px]">
              <span className="text-slate-500">{label}</span>
              <span className={`font-mono ${color}`}>{value}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
