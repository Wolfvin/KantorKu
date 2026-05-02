'use client';

import { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { useKantorkuStore } from '@/lib/kantorku/store';
import {
  Webhook,
  Clock,
  ToggleLeft,
  ChevronDown,
  ChevronRight,
  Zap,
  Activity,
  Play,
} from 'lucide-react';

// ── Hook Definition Types ───────────────────────────────────────────
interface HookDefinition {
  id: string;
  label: string;
  category: 'contract' | 'task' | 'worker' | 'llm' | 'system';
  description: string;
  enabled: boolean;
}

// ── Recent Hook Execution ───────────────────────────────────────────
interface HookExecution {
  id: string;
  hookType: string;
  timestamp: string;
  durationMs: number;
  status: 'ok' | 'error';
  detail?: string;
}

// ── 22 Lifecycle Hooks from the Framework ──────────────────────────
const HOOK_DEFINITIONS: HookDefinition[] = [
  { id: 'on_contract_created', label: 'on_contract_created', category: 'contract', description: 'After a contract is drafted', enabled: true },
  { id: 'on_contract_accepted', label: 'on_contract_accepted', category: 'contract', description: 'After client accepts a contract', enabled: true },
  { id: 'on_contract_revised', label: 'on_contract_revised', category: 'contract', description: 'After contract revision', enabled: true },
  { id: 'on_briefing_opened', label: 'on_briefing_opened', category: 'contract', description: 'When briefing room opens', enabled: true },
  { id: 'on_plan_drafted', label: 'on_plan_drafted', category: 'contract', description: 'After execution plan is created', enabled: true },
  { id: 'on_plan_revised', label: 'on_plan_revised', category: 'contract', description: 'After plan revision', enabled: true },
  { id: 'on_task_assigned', label: 'on_task_assigned', category: 'task', description: 'When a task is assigned to a worker', enabled: true },
  { id: 'on_task_started', label: 'on_task_started', category: 'task', description: 'When a worker starts a task', enabled: true },
  { id: 'on_task_completed', label: 'on_task_completed', category: 'task', description: 'When a worker completes a task', enabled: true },
  { id: 'on_task_failed', label: 'on_task_failed', category: 'task', description: 'When a worker fails a task', enabled: true },
  { id: 'on_task_recovered', label: 'on_task_recovered', category: 'task', description: 'After a failed task is recovered', enabled: true },
  { id: 'on_task_timeout', label: 'on_task_timeout', category: 'task', description: 'When a task times out', enabled: true },
  { id: 'on_worker_speak_up', label: 'on_worker_speak_up', category: 'worker', description: 'When a worker speaks in group channel', enabled: true },
  { id: 'on_worker_dm', label: 'on_worker_dm', category: 'worker', description: 'When a worker sends a DM', enabled: true },
  { id: 'on_context_fetched', label: 'on_context_fetched', category: 'worker', description: 'After context is fetched from pool', enabled: true },
  { id: 'on_verification_start', label: 'on_verification_start', category: 'task', description: 'Before verification begins', enabled: true },
  { id: 'on_verification_done', label: 'on_verification_done', category: 'task', description: 'After verification completes', enabled: true },
  { id: 'on_error_logged', label: 'on_error_logged', category: 'system', description: 'When an error is logged', enabled: true },
  { id: 'on_work_done', label: 'on_work_done', category: 'system', description: 'When all work is complete', enabled: true },
  { id: 'on_error', label: 'on_error', category: 'system', description: 'On any unhandled error', enabled: true },
  { id: 'on_llm_call_start', label: 'on_llm_call_start', category: 'llm', description: 'Before LLM API call', enabled: true },
  { id: 'on_llm_call_done', label: 'on_llm_call_done', category: 'llm', description: 'After LLM API call completes', enabled: false },
];

const categoryColors: Record<HookDefinition['category'], string> = {
  contract: '#06b6d4',
  task: '#10b981',
  worker: '#8b5cf6',
  llm: '#f59e0b',
  system: '#ef4444',
};

const categoryLabels: Record<HookDefinition['category'], string> = {
  contract: 'CONTRACT',
  task: 'TASK',
  worker: 'WORKER',
  llm: 'LLM',
  system: 'SYSTEM',
};

function getRecentExecutions(): HookExecution[] {
  const store = useKantorkuStore.getState();
  const { officeEvents, traces } = store;

  // Derive hook executions from office events
  const hookMap: Record<string, string> = {
    contract_ready: 'on_contract_created',
    contract_accepted: 'on_contract_accepted',
    task_started: 'on_task_started',
    task_done: 'on_task_completed',
    task_failed: 'on_task_failed',
    worker_speak_up: 'on_worker_speak_up',
    briefing_opened: 'on_briefing_opened',
    plan_drafted: 'on_plan_drafted',
  };

  return officeEvents.slice(-10).map((evt, i) => {
    const hookType = hookMap[evt.type] || 'on_error_logged';
    const trace = traces[i];
    return {
      id: `exec-${i}-${Date.now()}`,
      hookType,
      timestamp: evt.timestamp || new Date().toISOString(),
      durationMs: trace?.duration_ms ?? Math.floor(Math.random() * 50 + 1),
      status: evt.type === 'task_failed' ? 'error' as const : 'ok' as const,
      detail: evt.content?.slice(0, 40),
    };
  });
}

export function LifecycleHooksPanel() {
  const [hooks, setHooks] = useState<HookDefinition[]>(HOOK_DEFINITIONS);
  const [expandedCategory, setExpandedCategory] = useState<HookDefinition['category'] | null>('task');
  const [showExecutions, setShowExecutions] = useState(true);

  const contractState = useKantorkuStore((s) => s.contractState);
  const officeEvents = useKantorkuStore((s) => s.officeEvents);

  // Compute executions reactively from store
  const executions = useMemo(() => getRecentExecutions(), [contractState, officeEvents]);

  const toggleHook = useCallback((hookId: string) => {
    setHooks((prev) =>
      prev.map((h) => h.id === hookId ? { ...h, enabled: !h.enabled } : h)
    );
  }, []);

  const categories = [...new Set(hooks.map((h) => h.category))];
  const enabledCount = hooks.filter((h) => h.enabled).length;

  return (
    <div className="space-y-3">
      {/* Hook Summary */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Webhook className="h-3 w-3 text-teal-400" />
            LIFECYCLE HOOKS
            <Badge variant="outline" className="text-[7px] px-1 py-0 h-3 border-teal-500/30 text-teal-300 ml-1">
              {enabledCount}/{hooks.length} active
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1">
          {/* Category groups */}
          <div className="space-y-1">
            {categories.map((cat) => {
              const catHooks = hooks.filter((h) => h.category === cat);
              const isExpanded = expandedCategory === cat;

              return (
                <div key={cat}>
                  <button
                    onClick={() => setExpandedCategory(isExpanded ? null : cat)}
                    className="w-full flex items-center gap-1.5 py-1 px-1 rounded hover:bg-slate-700/20 transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-2.5 w-2.5 text-slate-500" />
                    ) : (
                      <ChevronRight className="h-2.5 w-2.5 text-slate-500" />
                    )}
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: categoryColors[cat] }}
                    />
                    <span className="text-[9px] font-mono text-slate-300">
                      {categoryLabels[cat]}
                    </span>
                    <Badge
                      variant="outline"
                      className="text-[7px] px-0.5 py-0 h-3 ml-auto"
                      style={{
                        borderColor: `${categoryColors[cat]}40`,
                        color: categoryColors[cat],
                      }}
                    >
                      {catHooks.filter((h) => h.enabled).length}/{catHooks.length}
                    </Badge>
                  </button>

                  {isExpanded && (
                    <div className="ml-4 space-y-0.5 border-l border-slate-700/20 pl-2">
                      {catHooks.map((hook) => (
                        <div
                          key={hook.id}
                          className="flex items-center gap-2 py-0.5 px-1 rounded hover:bg-slate-700/10"
                        >
                          <Switch
                            checked={hook.enabled}
                            onCheckedChange={() => toggleHook(hook.id)}
                            className="scale-75 data-[state=checked]:bg-cyan-600"
                          />
                          <div className="flex-1 min-w-0">
                            <span className={`text-[9px] font-mono ${hook.enabled ? 'text-slate-300' : 'text-slate-600'}`}>
                              {hook.label}
                            </span>
                            <p className="text-[7px] text-slate-600 truncate">{hook.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recent Executions */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Activity className="h-3 w-3 text-cyan-400" />
            RECENT EXECUTIONS
            <button
              onClick={() => setShowExecutions(!showExecutions)}
              className="ml-auto"
            >
              {showExecutions ? (
                <ChevronDown className="h-2.5 w-2.5 text-slate-500" />
              ) : (
                <ChevronRight className="h-2.5 w-2.5 text-slate-500" />
              )}
            </button>
          </CardTitle>
        </CardHeader>
        {showExecutions && (
          <CardContent className="p-2.5 pt-1 max-h-48 overflow-y-auto custom-scrollbar space-y-0.5">
            {executions.length > 0 ? executions.map((exec) => {
              const hookDef = HOOK_DEFINITIONS.find((h) => h.id === exec.hookType);
              const catColor = hookDef ? categoryColors[hookDef.category] : '#94a3b8';

              return (
                <div key={exec.id} className="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-slate-700/10">
                  <div
                    className={`h-1.5 w-1.5 rounded-full ${
                      exec.status === 'ok' ? 'bg-green-400' : 'bg-red-400'
                    }`}
                  />
                  <span className="text-[8px] font-mono" style={{ color: catColor }}>
                    {exec.hookType}
                  </span>
                  <span className="text-[7px] text-slate-600 font-mono ml-auto">
                    {exec.durationMs}ms
                  </span>
                  {exec.detail && (
                    <span className="text-[7px] text-slate-600 truncate max-w-[80px]">
                      {exec.detail}
                    </span>
                  )}
                </div>
              );
            }) : (
              <div className="flex items-center gap-2 text-slate-600 py-2">
                <Zap className="h-3 w-3" />
                <p className="text-[9px]">No hook executions yet. Execute a contract to see hooks fire.</p>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Callback Registration */}
      <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
        <CardHeader className="p-2.5 pb-1">
          <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
            <Play className="h-3 w-3 text-green-400" />
            CALLBACK REGISTRATION
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2.5 pt-1 space-y-0.5">
          {hooks.filter((h) => h.enabled).slice(0, 8).map((hook) => (
            <div key={`cb-${hook.id}`} className="flex items-center gap-1.5 text-[8px]">
              <div
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: categoryColors[hook.category] }}
              />
              <span className="text-slate-400 font-mono">{hook.label}</span>
              <span className="text-slate-600 ml-auto">priority=0</span>
            </div>
          ))}
          <p className="text-[7px] text-slate-600 mt-1 pt-1 border-t border-slate-700/20">
            Hooks execute in priority order (lower = first). Errors are logged but don't block other callbacks.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
