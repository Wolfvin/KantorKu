'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
} from 'lucide-react';
import { SQUADS } from '@/lib/kantorku/workers-data';

export function DashboardZone() {
  const {
    costReport,
    healthStatus,
    circuitBreakers,
    workers,
    officeEvents,
    contractState,
    metricsSummary,
  } = useKantorkuStore();

  // Prepare cost data for charts
  const costByModel = costReport
    ? Object.entries(costReport.by_model).map(([model, data]) => ({
        model: model.split('/').pop() || model,
        cost: Number(data.cost.toFixed(4)),
        calls: data.calls,
        tokens: data.tokens,
      }))
    : [];

  // Token usage data
  const tokenData = costReport
    ? Object.entries(costReport.by_model).map(([model, data]) => ({
        model: model.split('/').pop() || model,
        tokens: data.tokens,
      }))
    : [];

  // Worker status distribution
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

  // Event type counts
  const eventTypeCounts: Record<string, number> = {};
  officeEvents.forEach((e) => {
    eventTypeCounts[e.type] = (eventTypeCounts[e.type] || 0) + 1;
  });
  const eventData = Object.entries(eventTypeCounts)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  // Circuit breaker colors
  const cbStateColors: Record<string, string> = {
    closed: '#10b981',
    open: '#ef4444',
    half_open: '#f59e0b',
  };

  const totalEvents = officeEvents.length;
  const totalCost = costReport?.total_cost || 0;
  const totalTokens = costReport
    ? costReport.total_input_tokens + costReport.total_output_tokens
    : 0;

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
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-2">
          <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/30 text-center">
            <DollarSign className="h-3.5 w-3.5 text-green-400 mx-auto mb-1" />
            <p className="text-sm font-bold text-green-300 font-mono">
              ${totalCost.toFixed(4)}
            </p>
            <p className="text-[9px] text-slate-500">Total Cost</p>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/30 text-center">
            <Cpu className="h-3.5 w-3.5 text-cyan-400 mx-auto mb-1" />
            <p className="text-sm font-bold text-cyan-300 font-mono">
              {totalTokens > 1000 ? `${(totalTokens / 1000).toFixed(1)}k` : totalTokens}
            </p>
            <p className="text-[9px] text-slate-500">Total Tokens</p>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/30 text-center">
            <Activity className="h-3.5 w-3.5 text-amber-400 mx-auto mb-1" />
            <p className="text-sm font-bold text-amber-300 font-mono">{totalEvents}</p>
            <p className="text-[9px] text-slate-500">Events</p>
          </div>
        </div>

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
                <div
                  key={name}
                  className="flex items-center justify-between py-1 border-t border-slate-700/20"
                >
                  <span className="text-[10px] text-slate-400 font-mono">{name}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] text-slate-500">
                      {data.latency_ms}ms
                    </span>
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
              <p className="text-[9px] text-slate-600">
                Health data will appear after first request.
              </p>
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
                <div
                  key={cb.provider}
                  className="flex items-center justify-between py-1 border-t border-slate-700/20 first:border-0"
                >
                  <span className="text-[10px] text-slate-400 font-mono">
                    {cb.provider}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{
                        backgroundColor: cbStateColors[cb.state],
                        boxShadow: `0 0 4px ${cbStateColors[cb.state]}60`,
                      }}
                    />
                    <span
                      className="text-[9px] font-mono"
                      style={{ color: cbStateColors[cb.state] }}
                    >
                      {cb.state}
                    </span>
                    {cb.failure_count > 0 && (
                      <span className="text-[8px] text-red-400">
                        ({cb.failure_count} failures)
                      </span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full bg-green-400 shadow-[0_0_4px_#10b98160]" />
                <span className="text-[9px] text-slate-500">
                  All circuits closed (normal)
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cost Chart */}
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
                  <XAxis
                    dataKey="model"
                    tick={{ fontSize: 8, fill: '#94a3b8' }}
                    axisLine={{ stroke: '#334155' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 8, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      fontSize: '10px',
                    }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Bar dataKey="cost" fill="#10b981" radius={[2, 2, 0, 0]} />
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
                  <XAxis
                    dataKey="model"
                    tick={{ fontSize: 8, fill: '#94a3b8' }}
                    axisLine={{ stroke: '#334155' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 8, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      fontSize: '10px',
                    }}
                  />
                  <Bar dataKey="tokens" fill="#06b6d4" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Worker Distribution */}
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
                    <Pie
                      data={workerStatusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={20}
                      outerRadius={35}
                      dataKey="value"
                      stroke="none"
                    >
                      {workerStatusData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1">
                  {workerStatusData.map((d) => (
                    <div key={d.name} className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: d.color }}
                      />
                      <span className="text-[9px] text-slate-400">
                        {d.name}: {d.value}
                      </span>
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
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 8, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                  width={70}
                />
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
              <CardTitle className="text-[10px] font-mono text-slate-400">
                EVENT DISTRIBUTION
              </CardTitle>
            </CardHeader>
            <CardContent className="p-2.5 pt-1">
              <ResponsiveContainer width="100%" height={100}>
                <BarChart data={eventData} barSize={12}>
                  <XAxis
                    dataKey="type"
                    tick={{ fontSize: 6, fill: '#94a3b8' }}
                    axisLine={{ stroke: '#334155' }}
                    tickLine={false}
                    angle={-30}
                    textAnchor="end"
                    height={30}
                  />
                  <YAxis
                    tick={{ fontSize: 8, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    width={20}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Sessions */}
        <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Zap className="h-3 w-3 text-cyan-400" />
              ACTIVE SESSION
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2.5 pt-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-400 font-mono">default</span>
              <Badge
                variant="outline"
                className={`text-[8px] px-1 py-0 h-3.5 ${
                  contractState === 'working'
                    ? 'border-cyan-500/30 text-cyan-300'
                    : contractState === 'done'
                    ? 'border-green-500/30 text-green-300'
                    : 'border-slate-600/30 text-slate-400'
                }`}
              >
                {contractState}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Metrics Summary */}
        {metricsSummary && (
          <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
            <CardHeader className="p-2.5 pb-1">
              <CardTitle className="text-[10px] font-mono text-slate-400">
                METRICS SUMMARY
              </CardTitle>
            </CardHeader>
            <CardContent className="p-2.5 pt-1 space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-500">Total Calls</span>
                <span className="text-slate-300 font-mono">{metricsSummary.total_calls}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-500">Avg Latency</span>
                <span className="text-slate-300 font-mono">{metricsSummary.avg_latency_ms.toFixed(1)}ms</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-500">Success Rate</span>
                <span className="text-green-300 font-mono">
                  {(metricsSummary.success_rate * 100).toFixed(1)}%
                </span>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
