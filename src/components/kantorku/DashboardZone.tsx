'use client';

import { useState, useMemo } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
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
  Heart,
  Shield,
  Cpu,
  Zap,
  TrendingUp,
  Clock,
  Eye,
  Server,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Info,
  Bell,
  FileText,
  AlertOctagon,
  GitBranch,
  Timer,
  Target,
  Plus,
} from 'lucide-react';
import { SQUADS } from '@/lib/kantorku/workers-data';
import { WORKERS } from '@/lib/kantorku/workers-data';
import type { TraceEntry, MiddlewareStep } from '@/lib/kantorku/types';

// ── Percentile computation ──────────────────────────────────────────
function computePercentiles(values: number[]): { p50: number; p95: number; p99: number; avg: number } {
  if (values.length === 0) return { p50: 0, p95: 0, p99: 0, avg: 0 };
  const sorted = [...values].sort((a, b) => a - b);
  const p = (pct: number) => sorted[Math.floor(sorted.length * pct)];
  const avg = sorted.reduce((s, v) => s + v, 0) / sorted.length;
  return {
    p50: p(0.5),
    p95: p(0.95),
    p99: p(0.99),
    avg,
  };
}

// ── Span tree builder ───────────────────────────────────────────────
interface SpanNode {
  trace: TraceEntry;
  children: SpanNode[];
}

function buildSpanTree(traces: TraceEntry[]): SpanNode[] {
  const map = new Map<string, SpanNode>();
  const roots: SpanNode[] = [];

  // Create all nodes
  traces.forEach((t) => {
    map.set(t.span_id, { trace: t, children: [] });
  });

  // Build tree
  traces.forEach((t) => {
    const node = map.get(t.span_id)!;
    if (t.parent_span_id && map.has(t.parent_span_id)) {
      map.get(t.parent_span_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return roots;
}

// ── Overview Tab ────────────────────────────────────────────────────
function OverviewTab() {
  const {
    costReport,
    workers,
    officeEvents,
    contractState,
    metricsSummary,
    sessions,
    latencyHistory,
  } = useKantorkuStore();

  // Compute real percentiles from latency history
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

  // Cost by Model
  const costByModel = costReport
    ? Object.entries(costReport.by_model).map(([model, data]) => ({
        model: model.split('/').pop() || model,
        cost: Number(data.cost.toFixed(4)),
        calls: data.calls,
        tokens: data.tokens,
      }))
    : [];

  // Cost by Worker
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

  // Token usage
  const tokenData = costReport
    ? Object.entries(costReport.by_model).map(([model, data]) => ({
        model: model.split('/').pop() || model,
        tokens: data.tokens,
      }))
    : [];

  // Worker status pie
  const workerStatusData = [
    { name: 'Idle', value: workers.filter((w) => w.status === 'idle').length, color: '#64748b' },
    { name: 'Busy', value: workers.filter((w) => w.status === 'busy').length, color: '#06b6d4' },
    { name: 'Error', value: workers.filter((w) => w.status === 'error').length, color: '#ef4444' },
    { name: 'Offline', value: workers.filter((w) => w.status === 'offline').length, color: '#334155' },
  ].filter((d) => d.value > 0);

  // Squad distribution
  const squadData = SQUADS.map((s) => ({
    name: s.label,
    workers: workers.filter((w) => w.squad === s.id).length,
    color: s.color,
  }));

  // Event type distribution
  const eventTypeCounts: Record<string, number> = {};
  officeEvents.forEach((e) => {
    eventTypeCounts[e.type] = (eventTypeCounts[e.type] || 0) + 1;
  });
  const eventData = Object.entries(eventTypeCounts)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  // Latency history chart
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
                  {costByWorker.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
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
                    {workerStatusData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
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
                {squadData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
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

      {/* Metrics Summary Card with real percentiles */}
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

// ── Span Tree Node Renderer ─────────────────────────────────────────
function SpanTreeNode({ node, depth = 0, highlightedTraceId }: { node: SpanNode; depth?: number; highlightedTraceId: string | null }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const t = node.trace;
  const isHighlighted = highlightedTraceId === t.trace_id;
  const statusColor = t.status === 'ok' ? '#22c55e' : t.status === 'error' ? '#ef4444' : t.status === 'timeout' ? '#f59e0b' : '#94a3b8';

  return (
    <div className={`${isHighlighted ? 'bg-cyan-500/10 rounded' : ''}`}>
      <div
        className="flex items-center gap-1 py-0.5 px-1 cursor-pointer hover:bg-slate-700/20 rounded"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        {node.children.length > 0 ? (
          expanded ? <ChevronDown className="h-2.5 w-2.5 text-slate-500" /> : <ChevronRight className="h-2.5 w-2.5 text-slate-500" />
        ) : (
          <span className="w-2.5" />
        )}
        <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: statusColor, boxShadow: `0 0 4px ${statusColor}60` }} />
        <span className="text-[9px] font-mono text-slate-300 truncate">{t.operation}</span>
        {t.duration_ms != null && (
          <span className="text-[8px] font-mono text-slate-500">{t.duration_ms}ms</span>
        )}
        {t.worker_id && (
          <span className="text-[8px] font-mono text-cyan-400/60">{t.worker_id}</span>
        )}
      </div>
      {expanded && node.children.map((child) => (
        <SpanTreeNode key={child.trace.span_id} node={child} depth={depth + 1} highlightedTraceId={highlightedTraceId} />
      ))}
    </div>
  );
}

// ── Trace Timeline Bar ──────────────────────────────────────────────
function TraceTimeline({ traces, selectedTraceId, onSelectTrace }: { traces: TraceEntry[]; selectedTraceId: string | null; onSelectTrace: (id: string) => void }) {
  if (traces.length === 0) return <p className="text-[9px] text-slate-600">No traces to display on timeline.</p>;

  // Find time range
  const times = traces.filter((t) => t.start_time).map((t) => new Date(t.start_time).getTime());
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times, minTime + 1000); // At least 1s range

  const timelineWidth = 100; // percentage

  const getPosition = (startTime: string) => {
    const t = new Date(startTime).getTime();
    return ((t - minTime) / (maxTime - minTime)) * timelineWidth;
  };

  const getWidth = (durationMs?: number) => {
    if (!durationMs) return 1;
    return Math.max(0.5, (durationMs / (maxTime - minTime)) * timelineWidth);
  };

  return (
    <div className="space-y-0.5">
      {/* Time axis labels */}
      <div className="flex justify-between text-[7px] text-slate-600 font-mono">
        <span>{new Date(minTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
        <span>{new Date(maxTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
      </div>
      {traces.filter((t) => t.start_time).map((trace) => {
        const left = getPosition(trace.start_time);
        const width = getWidth(trace.duration_ms);
        const statusColor = trace.status === 'ok' ? '#22c55e' : trace.status === 'error' ? '#ef4444' : '#f59e0b';
        const isSelected = selectedTraceId === trace.trace_id;

        return (
          <div
            key={trace.trace_id}
            className={`flex items-center gap-1 cursor-pointer rounded-sm transition-colors ${isSelected ? 'bg-cyan-500/10' : 'hover:bg-slate-700/20'}`}
            onClick={() => onSelectTrace(trace.trace_id)}
          >
            <span className="text-[7px] text-slate-500 font-mono w-20 truncate flex-shrink-0" title={trace.operation}>
              {trace.operation}
            </span>
            <div className="flex-1 h-3 bg-slate-900/60 rounded-sm relative">
              <div
                className="absolute top-0.5 h-2 rounded-sm"
                style={{
                  left: `${left}%`,
                  width: `${width}%`,
                  backgroundColor: statusColor,
                  opacity: isSelected ? 1 : 0.7,
                  boxShadow: isSelected ? `0 0 4px ${statusColor}80` : 'none',
                }}
                title={`${trace.operation} ${trace.duration_ms ?? '?'}ms`}
              />
            </div>
            <span className="text-[7px] font-mono flex-shrink-0" style={{ color: statusColor }}>
              {trace.duration_ms ?? '?'}ms
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Observability Tab ───────────────────────────────────────────────
function ObservabilityTab() {
  const { traces, middlewareSteps, activeTraceId, setActiveTraceId, officeEvents, latencyHistory } = useKantorkuStore();
  const [traceFilter, setTraceFilter] = useState<'all' | 'ok' | 'error' | 'timeout'>('all');
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);
  const [highlightedTraceId, setHighlightedTraceId] = useState<string | null>(null);

  const filteredTraces = traces.filter(
    (t) => traceFilter === 'all' || t.status === traceFilter
  );

  // Compute real percentiles from latency history
  const computedPercentiles = useMemo(() => {
    const values = latencyHistory.map((e) => e.latency_ms).filter((v) => v > 0);
    return computePercentiles(values);
  }, [latencyHistory]);

  // Build span tree from traces
  const spanTreeRoots = useMemo(() => buildSpanTree(traces), [traces]);

  // Correlate traces with events
  const relatedEvents = useMemo(() => {
    if (!highlightedTraceId) return [];
    return officeEvents.filter((e) => e.trace_id === highlightedTraceId);
  }, [highlightedTraceId, officeEvents]);

  const statusIcon = (status: string) => {
    switch (status) {
      case 'ok': return <CheckCircle2 className="h-3 w-3 text-green-400" />;
      case 'error': return <XCircle className="h-3 w-3 text-red-400" />;
      case 'timeout': return <Clock className="h-3 w-3 text-amber-400" />;
      default: return <Activity className="h-3 w-3 text-slate-400" />;
    }
  };

  const stepStatusIcon = (status: string) => {
    switch (status) {
      case 'passed': return <CheckCircle2 className="h-3 w-3 text-green-400" />;
      case 'blocked': return <XCircle className="h-3 w-3 text-red-400" />;
      case 'skipped': return <ArrowRight className="h-3 w-3 text-slate-500" />;
      case 'error': return <AlertTriangle className="h-3 w-3 text-amber-400" />;
      default: return null;
    }
  };

  const handleTraceSelect = (traceId: string) => {
    setHighlightedTraceId(highlightedTraceId === traceId ? null : traceId);
    setActiveTraceId(highlightedTraceId === traceId ? null : traceId);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
      {/* Real Percentile Stats */}
      <div className="grid grid-cols-4 gap-1.5">
        {[
          { label: 'P50', value: computedPercentiles.p50, color: 'text-cyan-300', unit: 'ms' },
          { label: 'P95', value: computedPercentiles.p95, color: 'text-amber-300', unit: 'ms' },
          { label: 'P99', value: computedPercentiles.p99, color: 'text-red-300', unit: 'ms' },
          { label: 'Samples', value: latencyHistory.length, color: 'text-slate-300', unit: '' },
        ].map(({ label, value, color, unit }) => (
          <div key={label} className="p-1.5 rounded bg-slate-800/60 border border-slate-700/30 text-center">
            <p className="text-[8px] text-slate-500 uppercase">{label}</p>
            <p className={`text-[11px] font-bold font-mono ${color}`}>
              {typeof value === 'number' && unit === 'ms' ? value.toFixed(1) : value}
              {unit && <span className="text-[8px] text-slate-500 ml-0.5">{unit}</span>}
            </p>
          </div>
        ))}
      </div>

      {/* Trace Filter */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-slate-400 font-mono">FILTER:</span>
        {(['all', 'ok', 'error', 'timeout'] as const).map((f) => (
          <Button
            key={f}
            variant="ghost"
            size="sm"
            onClick={() => setTraceFilter(f)}
            className={`h-5 px-2 text-[9px] font-mono ${
              traceFilter === f
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {f === 'all' ? 'ALL' : f.toUpperCase()}
          </Button>
        ))}
        <span className="text-[9px] text-slate-600 font-mono ml-auto">
          {filteredTraces.length} traces
        </span>
      </div>

      {/* Trace Timeline */}
      {traces.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Timer className="h-3 w-3 text-cyan-400" />
              TRACE TIMELINE
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1 max-h-48 overflow-y-auto custom-scrollbar">
            <TraceTimeline
              traces={filteredTraces.slice(-20)}
              selectedTraceId={highlightedTraceId}
              onSelectTrace={handleTraceSelect}
            />
          </CardContent>
        </Card>
      )}

      {/* Span Tree Visualization */}
      {traces.length > 0 && (
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <GitBranch className="h-3 w-3 text-teal-400" />
              SPAN TREE
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 border-teal-500/30 text-teal-300 font-mono">
                {traces.length} spans
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1 max-h-56 overflow-y-auto custom-scrollbar">
            {spanTreeRoots.length > 0 ? spanTreeRoots.map((root) => (
              <SpanTreeNode key={root.trace.span_id} node={root} highlightedTraceId={highlightedTraceId} />
            )) : (
              <p className="text-[9px] text-slate-600">No span tree data available.</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Traces List */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Eye className="h-3 w-3 text-cyan-400" />
            RECENT TRACES
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 max-h-64 overflow-y-auto custom-scrollbar space-y-1">
          {filteredTraces.length > 0 ? filteredTraces.map((trace: TraceEntry) => (
            <div key={trace.trace_id}>
              <button
                onClick={() => {
                  setExpandedTrace(expandedTrace === trace.trace_id ? null : trace.trace_id);
                  handleTraceSelect(trace.trace_id);
                }}
                className={`w-full text-left p-2 rounded-md bg-slate-900/60 border transition-colors ${
                  highlightedTraceId === trace.trace_id
                    ? 'border-cyan-500/40 bg-cyan-500/5'
                    : 'border-slate-700/20 hover:border-slate-600/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 min-w-0">
                    {statusIcon(trace.status)}
                    <span className="text-[10px] font-mono text-slate-300 truncate">
                      {trace.operation}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {trace.duration_ms != null && (
                      <span className="text-[9px] font-mono text-slate-500">
                        {trace.duration_ms}ms
                      </span>
                    )}
                    {expandedTrace === trace.trace_id ? (
                      <ChevronDown className="h-3 w-3 text-slate-500" />
                    ) : (
                      <ChevronRight className="h-3 w-3 text-slate-500" />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {trace.worker_id && (
                    <span className="text-[9px] font-mono text-cyan-400">
                      {trace.worker_id}
                    </span>
                  )}
                  {trace.model && (
                    <span className="text-[9px] font-mono text-slate-500">
                      {trace.model.split('/').pop()}
                    </span>
                  )}
                  {(trace.input_tokens != null || trace.output_tokens != null) && (
                    <span className="text-[9px] font-mono text-slate-600">
                      {(trace.input_tokens || 0) + (trace.output_tokens || 0)} tok
                    </span>
                  )}
                </div>
              </button>

              {/* Expanded trace details */}
              {expandedTrace === trace.trace_id && (
                <div className="p-2 ml-3 border-l-2 border-cyan-500/20 space-y-1">
                  <div className="grid grid-cols-2 gap-1">
                    <div className="flex justify-between text-[9px]">
                      <span className="text-slate-500">trace_id</span>
                      <span className="text-slate-300 font-mono truncate ml-2">{trace.trace_id.slice(0, 12)}...</span>
                    </div>
                    <div className="flex justify-between text-[9px]">
                      <span className="text-slate-500">span_id</span>
                      <span className="text-slate-300 font-mono truncate ml-2">{trace.span_id.slice(0, 12)}...</span>
                    </div>
                    {trace.parent_span_id && (
                      <div className="flex justify-between text-[9px] col-span-2">
                        <span className="text-slate-500">parent_span_id</span>
                        <span className="text-slate-300 font-mono truncate ml-2">{trace.parent_span_id.slice(0, 12)}...</span>
                      </div>
                    )}
                    {trace.cost_usd != null && (
                      <div className="flex justify-between text-[9px]">
                        <span className="text-slate-500">cost</span>
                        <span className="text-green-300 font-mono">${trace.cost_usd.toFixed(6)}</span>
                      </div>
                    )}
                    {trace.start_time && (
                      <div className="flex justify-between text-[9px]">
                        <span className="text-slate-500">started</span>
                        <span className="text-slate-300 font-mono">{new Date(trace.start_time).toLocaleTimeString()}</span>
                      </div>
                    )}
                  </div>

                  {/* Trace-to-Event Correlation */}
                  {relatedEvents.length > 0 && (
                    <div className="mt-1.5 p-1.5 rounded bg-slate-900/40 border border-cyan-500/10">
                      <p className="text-[8px] text-cyan-400 font-mono uppercase mb-0.5">
                        <Target className="h-2.5 w-2.5 inline mr-0.5" />
                        Related Events ({relatedEvents.length})
                      </p>
                      <div className="space-y-0.5 max-h-24 overflow-y-auto custom-scrollbar">
                        {relatedEvents.map((evt, i) => (
                          <div key={i} className="flex items-center gap-1 text-[8px]">
                            <div className="h-1 w-1 rounded-full bg-cyan-400/60" />
                            <span className="text-slate-400 font-mono">{evt.type}</span>
                            {evt.from_id && <span className="text-slate-500">from: {evt.from_id}</span>}
                            {evt.duration_ms !== undefined && <span className="text-slate-500">{evt.duration_ms}ms</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )) : (
            <p className="text-[9px] text-slate-600">No traces recorded. Execute a contract to see traces.</p>
          )}
        </CardContent>
      </Card>

      {/* Request Flow / Middleware Pipeline */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <ArrowRight className="h-3 w-3 text-teal-400" />
            MIDDLEWARE PIPELINE
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 max-h-48 overflow-y-auto custom-scrollbar">
          {middlewareSteps.length > 0 ? (
            <div className="space-y-1">
              {middlewareSteps.map((step: MiddlewareStep, idx: number) => (
                <div key={`${step.name}-${idx}`} className="flex items-center gap-2 p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {stepStatusIcon(step.status)}
                    <span className="text-[9px] font-mono text-slate-500">
                      {idx + 1}.
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono text-slate-300">
                        {step.name}
                      </span>
                      <Badge
                        variant="outline"
                        className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-400"
                      >
                        {step.type}
                      </Badge>
                    </div>
                    {step.detail && (
                      <p className="text-[9px] text-slate-500 truncate">{step.detail}</p>
                    )}
                  </div>
                  <span className="text-[9px] font-mono text-slate-500 flex-shrink-0">
                    {step.duration_ms}ms
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[9px] text-slate-600">Middleware pipeline will be displayed after execution.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Infrastructure Tab ──────────────────────────────────────────────
function InfrastructureTab() {
  const {
    healthStatus,
    circuitBreakers,
    approvalGates,
    escalations,
    bulletinBoard,
    workers,
    resolveEscalation,
    addBulletinEntry,
  } = useKantorkuStore();

  const cbStateColors: Record<string, string> = {
    closed: '#10b981',
    open: '#ef4444',
    half_open: '#f59e0b',
  };

  const [showBulletinForm, setShowBulletinForm] = useState(false);
  const [bulletinTitle, setBulletinTitle] = useState('');
  const [bulletinContent, setBulletinContent] = useState('');
  const [bulletinType, setBulletinType] = useState<'announcement' | 'sop' | 'rule' | 'alert'>('announcement');
  const [bulletinPriority, setBulletinPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');

  const activeBulletin = bulletinBoard.filter((b) => b.active);
  const unresolvedEscalations = escalations.filter((e) => !e.resolved);

  const handleAddBulletin = () => {
    if (!bulletinTitle.trim() || !bulletinContent.trim()) return;
    addBulletinEntry({
      id: `blt-${Date.now()}`,
      type: bulletinType,
      title: bulletinTitle.trim(),
      content: bulletinContent.trim(),
      priority: bulletinPriority,
      created_at: new Date().toISOString(),
      active: true,
    });
    setBulletinTitle('');
    setBulletinContent('');
    setBulletinType('announcement');
    setBulletinPriority('medium');
    setShowBulletinForm(false);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
      {/* Health Status */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Heart className="h-3 w-3 text-red-400" />
            HEALTH STATUS
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1">
          <div className="flex items-center gap-2 mb-2">
            <div
              className={`h-2.5 w-2.5 rounded-full ${
                healthStatus?.is_healthy
                  ? 'bg-green-400 shadow-[0_0_6px_#10b981]'
                  : 'bg-red-400 shadow-[0_0_6px_#ef4444]'
              }`}
            />
            <span className="text-xs text-slate-300">
              {healthStatus?.is_healthy ? 'Healthy' : healthStatus?.message || 'Unknown'}
            </span>
          </div>
          {healthStatus?.providers &&
            Object.entries(healthStatus.providers).map(([name, data]) => (
              <div key={name} className="flex items-center justify-between py-1 border-t border-slate-700/20">
                <span className="text-[10px] text-slate-400 font-mono">{name}</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[9px] text-slate-500">{data.latency_ms}ms</span>
                  <span className="text-[9px] text-slate-600">{(data.error_rate * 100).toFixed(1)}% err</span>
                  <Badge
                    variant="outline"
                    className={`text-[8px] px-1 py-0 h-3.5 ${
                      data.status === 'healthy'
                        ? 'border-green-500/30 text-green-300'
                        : 'border-red-500/30 text-red-300'
                    }`}
                  >
                    {data.status}
                  </Badge>
                </div>
              </div>
            ))}
          {!healthStatus?.providers && (
            <p className="text-[9px] text-slate-600">Health data will appear after first request.</p>
          )}
        </CardContent>
      </Card>

      {/* Circuit Breakers */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Shield className="h-3 w-3 text-amber-400" />
            CIRCUIT BREAKERS
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1">
          {circuitBreakers.length > 0 ? (
            circuitBreakers.map((cb) => (
              <div key={cb.provider} className="flex items-center justify-between py-1 border-t border-slate-700/20 first:border-0">
                <span className="text-[10px] text-slate-400 font-mono">{cb.provider}</span>
                <div className="flex items-center gap-1.5">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: cbStateColors[cb.state], boxShadow: `0 0 4px ${cbStateColors[cb.state]}60` }}
                  />
                  <span className="text-[9px] font-mono" style={{ color: cbStateColors[cb.state] }}>
                    {cb.state}
                  </span>
                  {cb.failure_count > 0 && (
                    <span className="text-[8px] text-red-400">({cb.failure_count} failures)</span>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-green-400 shadow-[0_0_4px_#10b98160]" />
              <span className="text-[9px] text-slate-500">All circuits closed (normal)</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Approval Gates */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="h-3 w-3 text-teal-400" />
            APPROVAL GATES ({approvalGates.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 max-h-40 overflow-y-auto custom-scrollbar space-y-1">
          {approvalGates.length > 0 ? approvalGates.map((gate) => (
            <div key={gate.id} className="flex items-center justify-between p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-[10px] text-slate-300 font-mono truncate">{gate.gate_type}</span>
                <span className="text-[9px] text-slate-500">by {gate.approver}</span>
              </div>
              <Badge
                variant="outline"
                className={`text-[8px] px-1 py-0 h-3.5 flex-shrink-0 ${
                  gate.status === 'approved' ? 'border-green-500/30 text-green-300' :
                  gate.status === 'rejected' ? 'border-red-500/30 text-red-300' :
                  gate.status === 'skipped' ? 'border-slate-600/30 text-slate-400' :
                  'border-amber-500/30 text-amber-300'
                }`}
              >
                {gate.status}
              </Badge>
            </div>
          )) : (
            <p className="text-[9px] text-slate-600">No approval gates active.</p>
          )}
        </CardContent>
      </Card>

      {/* Escalations */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <AlertOctagon className="h-3 w-3 text-red-400" />
            ESCALATIONS ({unresolvedEscalations.length} unresolved)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 max-h-32 overflow-y-auto custom-scrollbar space-y-1">
          {escalations.length > 0 ? escalations.map((esc) => (
            <div
              key={esc.id}
              className={`p-1.5 rounded border ${
                !esc.resolved
                  ? esc.severity === 'critical'
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-amber-500/10 border-amber-500/30'
                  : 'bg-slate-900/60 border-slate-700/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 min-w-0">
                  {!esc.resolved && <AlertTriangle className="h-3 w-3 text-amber-400 flex-shrink-0" />}
                  <span className="text-[10px] text-slate-300 truncate">{esc.reason}</span>
                </div>
                <Badge
                  variant="outline"
                  className={`text-[8px] px-1 py-0 h-3.5 flex-shrink-0 ${
                    esc.severity === 'critical' ? 'border-red-500/30 text-red-300' :
                    esc.severity === 'warning' ? 'border-amber-500/30 text-amber-300' :
                    'border-slate-600/30 text-slate-400'
                  }`}
                >
                  {esc.severity}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-[9px] text-slate-500 font-mono">{esc.from_worker}</span>
                {esc.resolved ? (
                  <span className="text-[9px] text-green-400 font-mono">resolved</span>
                ) : (
                  <button
                    onClick={() => resolveEscalation(esc.id)}
                    className="ml-auto flex items-center gap-0.5 text-[9px] text-slate-400 hover:text-green-400 transition-colors"
                    title="Resolve escalation"
                  >
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Resolve</span>
                  </button>
                )}
              </div>
            </div>
          )) : (
            <p className="text-[9px] text-slate-600">No escalations.</p>
          )}
        </CardContent>
      </Card>

      {/* Bulletin Board */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Bell className="h-3 w-3 text-cyan-400" />
            BULLETIN BOARD ({activeBulletin.length} active)
            <button
              onClick={() => setShowBulletinForm(!showBulletinForm)}
              className="ml-auto h-4 w-4 flex items-center justify-center rounded bg-slate-700/50 hover:bg-cyan-500/30 text-slate-400 hover:text-cyan-300 transition-colors"
              title="Add bulletin"
            >
              <Plus className="h-2.5 w-2.5" />
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 max-h-40 overflow-y-auto custom-scrollbar space-y-1">
          {showBulletinForm && (
            <div className="p-2 rounded bg-slate-900/80 border border-cyan-500/20 space-y-1.5">
              <input
                type="text"
                value={bulletinTitle}
                onChange={(e) => setBulletinTitle(e.target.value)}
                placeholder="Title"
                className="w-full bg-slate-800/60 border border-slate-700/30 rounded px-1.5 py-0.5 text-[10px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/40"
              />
              <textarea
                value={bulletinContent}
                onChange={(e) => setBulletinContent(e.target.value)}
                placeholder="Content"
                rows={2}
                className="w-full bg-slate-800/60 border border-slate-700/30 rounded px-1.5 py-0.5 text-[10px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/40 resize-none"
              />
              <div className="flex items-center gap-1.5">
                <select
                  value={bulletinType}
                  onChange={(e) => setBulletinType(e.target.value as 'announcement' | 'sop' | 'rule' | 'alert')}
                  className="bg-slate-800/60 border border-slate-700/30 rounded px-1 py-0.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/40"
                >
                  <option value="announcement">announcement</option>
                  <option value="sop">sop</option>
                  <option value="rule">rule</option>
                  <option value="alert">alert</option>
                </select>
                <select
                  value={bulletinPriority}
                  onChange={(e) => setBulletinPriority(e.target.value as 'low' | 'medium' | 'high' | 'critical')}
                  className="bg-slate-800/60 border border-slate-700/30 rounded px-1 py-0.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/40"
                >
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="critical">critical</option>
                </select>
                <button
                  onClick={handleAddBulletin}
                  disabled={!bulletinTitle.trim() || !bulletinContent.trim()}
                  className="ml-auto px-2 py-0.5 text-[10px] bg-cyan-500/20 text-cyan-300 rounded hover:bg-cyan-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Submit
                </button>
              </div>
            </div>
          )}
          {activeBulletin.length > 0 ? activeBulletin.map((entry) => (
            <div key={entry.id} className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-300">{entry.title}</span>
                <Badge
                  variant="outline"
                  className={`text-[8px] px-1 py-0 h-3.5 ${
                    entry.priority === 'critical' ? 'border-red-500/30 text-red-300' :
                    entry.priority === 'high' ? 'border-amber-500/30 text-amber-300' :
                    'border-slate-600/30 text-slate-400'
                  }`}
                >
                  {entry.type}
                </Badge>
              </div>
              <p className="text-[9px] text-slate-500 mt-0.5">{entry.content}</p>
            </div>
          )) : (
            <p className="text-[9px] text-slate-600">No active bulletins.</p>
          )}
        </CardContent>
      </Card>

      {/* SOP Rules Display */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <FileText className="h-3 w-3 text-teal-400" />
            SOP RULES
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 space-y-1">
          {[
            'All contracts require team review before execution',
            'Budget over $5.00 requires client approval gate',
            'Critical tasks must be verified by verifier_engineer',
            'Failed tasks trigger automatic escalation',
            'Security-sensitive tasks require auditor approval',
          ].map((rule, i) => (
            <div key={i} className="flex items-start gap-1.5 py-0.5">
              <Info className="h-2.5 w-2.5 text-teal-400 mt-0.5 flex-shrink-0" />
              <span className="text-[9px] text-slate-400">{rule}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Worker Infrastructure Summary */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Server className="h-3 w-3 text-slate-400" />
            WORKER INFRASTRUCTURE
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 max-h-40 overflow-y-auto custom-scrollbar space-y-0.5">
          {workers.map((w) => (
            <div key={w.id} className="flex items-center justify-between py-0.5">
              <div className="flex items-center gap-1.5">
                <span className="text-[9px]">{w.emoji}</span>
                <span className="text-[9px] text-slate-400 font-mono">{w.id}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] text-slate-600 font-mono truncate max-w-[80px]">
                  {w.model.split('/').pop()}
                </span>
                <div className={`h-1.5 w-1.5 rounded-full ${
                  w.status === 'idle' ? 'bg-green-400' :
                  w.status === 'busy' ? 'bg-cyan-400' :
                  w.status === 'error' ? 'bg-red-400' :
                  'bg-slate-600'
                }`} />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main DashboardZone ──────────────────────────────────────────────
export function DashboardZone() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-slate-700/50 bg-slate-900/50">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-white">DASHBOARD</h2>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="overview" className="h-full flex flex-col">
          <TabsList className="flex-shrink-0 mx-3 mt-2 bg-slate-800/60 border border-slate-700/30 h-7 p-0.5">
            <TabsTrigger value="overview" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Activity className="h-3 w-3 mr-1" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="observability" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Eye className="h-3 w-3 mr-1" />
              Observability
            </TabsTrigger>
            <TabsTrigger value="infrastructure" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Server className="h-3 w-3 mr-1" />
              Infra
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="flex-1 overflow-hidden mt-0">
            <OverviewTab />
          </TabsContent>
          <TabsContent value="observability" className="flex-1 overflow-hidden mt-0">
            <ObservabilityTab />
          </TabsContent>
          <TabsContent value="infrastructure" className="flex-1 overflow-hidden mt-0">
            <InfrastructureTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
