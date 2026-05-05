'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useKantorkuStore } from '@/lib/kantorku/store';
import {
  Database,
  Shield,
  Gauge,
  RotateCcw,
  Cpu,
  DollarSign,
  BarChart3,
  HardDrive,
  ArrowRight,
  Zap,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  SkipForward,
} from 'lucide-react';

// ── Pipeline Step Types ─────────────────────────────────────────────
interface PipelineStep {
  id: string;
  label: string;
  icon: React.ElementType;
  status: 'active' | 'passed' | 'failed' | 'skipped';
  metric?: string;
  detail?: string;
}

// ── Pipeline Steps Configuration ────────────────────────────────────
function getPipelineSteps(): PipelineStep[] {
  const store = useKantorkuStore.getState();
  const { circuitBreakers, healthStatus, metricsSummary, costReport, middlewareSteps } = store;

  // Derive real metrics where available
  const cacheHitRate = metricsSummary?.total_calls
    ? ((metricsSummary.total_calls - (costReport?.entries?.length || 0)) / metricsSummary.total_calls * 100).toFixed(1)
    : '0.0';

  const cbState = circuitBreakers.length > 0
    ? circuitBreakers[0].state
    : 'closed';

  const rateLimitRemaining = healthStatus?.providers
    ? Object.values(healthStatus.providers).reduce((min, p) => Math.min(min, 100 - p.error_rate * 1000), 100).toFixed(0)
    : '100';

  const retryCount = middlewareSteps
    .filter((s) => s.type === 'retry')
    .length;

  return [
    {
      id: 'cache_check',
      label: 'Cache Check',
      icon: Database,
      status: middlewareSteps.some((s) => s.type === 'cache' && s.status === 'passed') ? 'passed'
        : middlewareSteps.some((s) => s.type === 'cache' && s.status === 'skipped') ? 'skipped' : 'active',
      metric: `${cacheHitRate}% hit`,
      detail: 'LLM response cache lookup',
    },
    {
      id: 'circuit_breaker',
      label: 'Circuit Breaker',
      icon: Shield,
      status: cbState === 'open' ? 'failed' : cbState === 'half_open' ? 'active' : 'passed',
      metric: cbState,
      detail: cbState === 'open' ? 'Circuit open — using fallback' : 'Circuit closed — normal',
    },
    {
      id: 'rate_limit',
      label: 'Rate Limit',
      icon: Gauge,
      status: middlewareSteps.some((s) => s.type === 'rate_limit' && s.status === 'passed') ? 'passed'
        : middlewareSteps.some((s) => s.type === 'rate_limit' && s.status === 'blocked') ? 'failed' : 'active',
      metric: `${rateLimitRemaining}% rem`,
      detail: 'Token bucket + semaphore',
    },
    {
      id: 'retry',
      label: 'Retry',
      icon: RotateCcw,
      status: retryCount > 0 ? 'active' : 'passed',
      metric: `${retryCount} retries`,
      detail: 'Exponential backoff',
    },
    {
      id: 'call_provider',
      label: 'Call Provider',
      icon: Cpu,
      status: 'active',
      metric: healthStatus?.is_healthy ? 'healthy' : 'degraded',
      detail: 'Provider dispatch',
    },
    {
      id: 'cost_track',
      label: 'Cost Track',
      icon: DollarSign,
      status: middlewareSteps.some((s) => s.type === 'cost_guard' && s.status === 'passed') ? 'passed' : 'active',
      metric: `$${(costReport?.total_cost || 0).toFixed(4)}`,
      detail: 'Per-model pricing',
    },
    {
      id: 'metrics',
      label: 'Metrics',
      icon: BarChart3,
      status: 'passed',
      metric: `${metricsSummary?.total_calls || 0} calls`,
      detail: 'Token + duration tracking',
    },
    {
      id: 'cache_store',
      label: 'Cache Store',
      icon: HardDrive,
      status: middlewareSteps.some((s) => s.type === 'cache' && s.status === 'passed') ? 'passed' : 'skipped',
      detail: 'Store response for reuse',
    },
    {
      id: 'fallback',
      label: 'Fallback',
      icon: Zap,
      status: circuitBreakers.some((cb) => cb.state === 'open') ? 'failed' : 'skipped',
      detail: 'Provider fallback chain',
    },
  ];
}

function StepStatusIcon({ status }: { status: PipelineStep['status'] }) {
  switch (status) {
    case 'passed':
      return <CheckCircle2 className="h-3 w-3 text-green-400" />;
    case 'failed':
      return <XCircle className="h-3 w-3 text-red-400" />;
    case 'active':
      return <div className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-pulse" />;
    case 'skipped':
      return <SkipForward className="h-3 w-3 text-slate-500" />;
  }
}

function stepBorderClass(status: PipelineStep['status']): string {
  switch (status) {
    case 'passed':
      return 'border-green-500/30 bg-green-500/5';
    case 'failed':
      return 'border-red-500/30 bg-red-500/5';
    case 'active':
      return 'border-cyan-500/30 bg-cyan-500/5';
    case 'skipped':
      return 'border-slate-700/30 bg-slate-800/30 border-dashed opacity-60';
  }
}

export function ProviderPipelinePanel() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const middlewareSteps = useKantorkuStore((s) => s.middlewareSteps);

  // Compute steps reactively from store state
  const steps = useMemo(() => getPipelineSteps(), [contractState, middlewareSteps]);

  return (
    <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
      <CardHeader className="p-2.5 pb-1">
        <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
          <ArrowRight className="h-3 w-3 text-teal-400" />
          PROVIDER ROUTER PIPELINE
        </CardTitle>
      </CardHeader>
      <CardContent className="p-2.5 pt-1">
        {steps.length > 0 ? (
          <div className="space-y-0">
            {/* Horizontal pipeline on larger screens, vertical on small */}
            <div className="flex flex-wrap items-center gap-1">
              {steps.map((step, idx) => {
                const Icon = step.icon;
                return (
                  <div key={step.id} className="flex items-center gap-1">
                    <div
                      className={`flex flex-col items-center p-1.5 rounded-md border min-w-[60px] ${stepBorderClass(step.status)} transition-all duration-300`}
                    >
                      <div className="flex items-center gap-1">
                        <StepStatusIcon status={step.status} />
                        <Icon className={`h-3 w-3 ${
                          step.status === 'passed' ? 'text-green-400' :
                          step.status === 'failed' ? 'text-red-400' :
                          step.status === 'active' ? 'text-cyan-400' :
                          'text-slate-500'
                        }`} />
                      </div>
                      <span className={`text-[8px] font-mono mt-0.5 text-center leading-tight ${
                        step.status === 'skipped' ? 'text-slate-600' :
                        step.status === 'failed' ? 'text-red-300' :
                        'text-slate-300'
                      }`}>
                        {step.label}
                      </span>
                      {step.metric && (
                        <Badge variant="outline" className={`text-[7px] px-0.5 py-0 h-3 mt-0.5 ${
                          step.status === 'active' ? 'border-cyan-500/30 text-cyan-300' :
                          step.status === 'failed' ? 'border-red-500/30 text-red-300' :
                          'border-slate-600/30 text-slate-400'
                        }`}>
                          {step.metric}
                        </Badge>
                      )}
                    </div>
                    {idx < steps.length - 1 && (
                      <ArrowRight className={`h-3 w-3 flex-shrink-0 ${
                        step.status === 'failed' ? 'text-red-400/40' : 'text-slate-600'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>
            {/* Detail row */}
            <div className="mt-2 grid grid-cols-3 gap-1">
              {steps.filter((s) => s.detail).map((step) => (
                <div key={`detail-${step.id}`} className="flex items-center gap-1 text-[8px]">
                  <StepStatusIcon status={step.status} />
                  <span className="text-slate-500 font-mono">{step.label}:</span>
                  <span className="text-slate-400 truncate">{step.detail}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-slate-600">
            <AlertTriangle className="h-3 w-3" />
            <p className="text-[9px]">Pipeline data will appear during contract execution.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
