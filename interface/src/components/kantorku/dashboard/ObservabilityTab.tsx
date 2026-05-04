'use client';

import { useState, useMemo } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  AlertTriangle,
  Eye,
  Timer,
  GitBranch,
  Target,
} from 'lucide-react';
import type { TraceEntry, MiddlewareStep } from '@/lib/kantorku/types';
import { LifecycleHooksPanel } from '../LifecycleHooksPanel';

function computePercentiles(values: number[]): { p50: number; p95: number; p99: number; avg: number } {
  if (values.length === 0) return { p50: 0, p95: 0, p99: 0, avg: 0 };
  const sorted = [...values].sort((a, b) => a - b);
  const p = (pct: number) => sorted[Math.floor(sorted.length * pct)];
  const avg = sorted.reduce((s, v) => s + v, 0) / sorted.length;
  return { p50: p(0.5), p95: p(0.95), p99: p(0.99), avg };
}

interface SpanNode {
  trace: TraceEntry;
  children: SpanNode[];
}

function buildSpanTree(traces: TraceEntry[]): SpanNode[] {
  const map = new Map<string, SpanNode>();
  const roots: SpanNode[] = [];
  traces.forEach((t) => {
    map.set(t.span_id, { trace: t, children: [] });
  });
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

function TraceTimeline({ traces, selectedTraceId, onSelectTrace }: { traces: TraceEntry[]; selectedTraceId: string | null; onSelectTrace: (id: string) => void }) {
  if (traces.length === 0) return <p className="text-[9px] text-slate-600">No traces to display on timeline.</p>;

  const times = traces.filter((t) => t.start_time).map((t) => new Date(t.start_time).getTime());
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times, minTime + 1000);

  const getPosition = (startTime: string) => {
    const t = new Date(startTime).getTime();
    return ((t - minTime) / (maxTime - minTime)) * 100;
  };

  const getWidth = (durationMs?: number) => {
    if (!durationMs) return 1;
    return Math.max(0.5, (durationMs / (maxTime - minTime)) * 100);
  };

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[9px] text-slate-600 font-mono">
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
            <span className="text-[9px] text-slate-500 font-mono w-20 truncate flex-shrink-0" title={trace.operation}>
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
            <span className="text-[9px] font-mono flex-shrink-0" style={{ color: statusColor }}>
              {trace.duration_ms ?? '?'}ms
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function ObservabilityTab() {
  const { traces, middlewareSteps, activeTraceId, setActiveTraceId, officeEvents, latencyHistory } = useKantorkuStore();
  const [traceFilter, setTraceFilter] = useState<'all' | 'ok' | 'error' | 'timeout'>('all');
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);
  const [highlightedTraceId, setHighlightedTraceId] = useState<string | null>(null);

  const filteredTraces = traces.filter(
    (t) => traceFilter === 'all' || t.status === traceFilter
  );

  const computedPercentiles = useMemo(() => {
    const values = latencyHistory.map((e) => e.latency_ms).filter((v) => v > 0);
    return computePercentiles(values);
  }, [latencyHistory]);

  const spanTreeRoots = useMemo(() => buildSpanTree(traces), [traces]);

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

                  {relatedEvents.length > 0 && (
                    <div className="mt-1.5 p-1.5 rounded bg-slate-900/40 border border-cyan-500/10">
                      <p className="text-[8px] text-cyan-400 font-mono uppercase mb-0.5">
                        <Target className="h-2.5 w-2.5 inline mr-0.5" />
                        Related Events ({relatedEvents.length})
                      </p>
                      <div className="space-y-0.5 max-h-24 overflow-y-auto custom-scrollbar">
                        {relatedEvents.map((evt, i) => (
                          <div key={`evt-${i}`} className="flex items-center gap-1 text-[8px]">
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

      {/* Middleware Pipeline */}
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

      {/* Lifecycle Hooks */}
      <LifecycleHooksPanel />
    </div>
  );
}
