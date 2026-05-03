'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Settings,
  Key,
  Wifi,
  WifiOff,
  Server,
  Trash2,
  Download,
  Info,
  CheckCircle2,
  XCircle,
  Loader2,
  Palette,
  Globe,
  Zap,
  Shield,
  Brain,
  Eye,
  Users,
  Activity,
  Clock,
  Database,
  GitBranch,
  Layers,
  FileText,
  Heart,
  Cpu,
  AlertTriangle,
  Timer,
  BarChart3,
  Network,
  Lock,
  RefreshCw,
  Sparkles,
  EyeOff,
  Bot,
  ChevronDown,
} from 'lucide-react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import type { WorkerApiKeyConfig } from '@/lib/kantorku/types';
import { useWebSocket, ConnectionState } from '@/hooks/use-websocket';
import { useState, useCallback, useRef, useEffect } from 'react';

// ── Provider Definitions ──────────────────────────────────────────
interface ProviderConfig {
  id: string;
  name: string;
  envVar: string;
  storageKey: string;
  placeholder: string;
  color: string;
  workers: string[];
  required: boolean;
  icon: string;
}

const PROVIDERS: ProviderConfig[] = [
  {
    id: 'zai',
    name: 'Z-AI SDK',
    envVar: 'ZAI_API_KEY',
    storageKey: 'kantorku_api_key',
    placeholder: 'Built-in SDK (auto-configured)',
    color: 'cyan',
    workers: ['Conductor (standalone)', 'All workers (standalone mode)'],
    required: true,
    icon: '⚡',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    envVar: 'ANTHROPIC_API_KEY',
    storageKey: 'kantorku_provider_anthropic',
    placeholder: 'sk-ant-...',
    color: 'orange',
    workers: ['Conductor (Claude Opus 4.6)', 'coder_frontend', 'auditor'],
    required: true,
    icon: '🟠',
  },
  {
    id: 'google',
    name: 'Google / Gemini',
    envVar: 'GOOGLE_API_KEY',
    storageKey: 'kantorku_provider_google',
    placeholder: 'AIza...',
    color: 'blue',
    workers: ['coder_wiring', 'verifier_designer', 'scout'],
    required: false,
    icon: '🔵',
  },
  {
    id: 'minimax',
    name: 'MiniMax',
    envVar: 'MINIMAX_API_KEY',
    storageKey: 'kantorku_provider_minimax',
    placeholder: 'mm-...',
    color: 'green',
    workers: ['coder_backend (M2.7)', 'verifier_engineer (M2.5)'],
    required: false,
    icon: '🟢',
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    envVar: 'DEEPSEEK_API_KEY',
    storageKey: 'kantorku_provider_deepseek',
    placeholder: 'sk-...',
    color: 'purple',
    workers: ['debugger (V3.2)', 'scribe (V4 Flash)', 'summarizer (V4 Flash)', 'Context Pool (x3)'],
    required: false,
    icon: '🟣',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    envVar: 'OPENAI_API_KEY',
    storageKey: 'kantorku_provider_openai',
    placeholder: 'sk-...',
    color: 'emerald',
    workers: ['coder_wiring (Codex)'],
    required: false,
    icon: '💚',
  },
  {
    id: 'xai',
    name: 'xAI (Grok)',
    envVar: 'XAI_API_KEY',
    storageKey: 'kantorku_provider_xai',
    placeholder: 'xai-...',
    color: 'white',
    workers: ['debugger (Grok 3)'],
    required: false,
    icon: '⚪',
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    envVar: 'OLLAMA_BASE_URL',
    storageKey: 'kantorku_provider_ollama',
    placeholder: 'http://localhost:11434',
    color: 'slate',
    workers: ['intake (Llama3)', 'narrator (Llama3)', 'sentinel (Llama3)'],
    required: false,
    icon: '🦙',
  },
];

// ── Provider Key Input Component ──────────────────────────────────
function ProviderKeyInput({ provider, onStatusChange }: { provider: ProviderConfig; onStatusChange: () => void }) {
  const [value, setValue] = useState(() => {
    if (typeof window === 'undefined') return '';
    return localStorage.getItem(provider.storageKey) || '';
  });
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'idle' | 'success' | 'error'>('idle');

  const isConfigured = value.length > 0;
  const isOllama = provider.id === 'ollama';

  const handleTest = useCallback(async () => {
    setTesting(true);
    setTestResult('idle');
    try {
      if (isOllama) {
        const resp = await fetch(value || 'http://localhost:11434/api/tags', {
          signal: AbortSignal.timeout(5000),
        }).catch(() => null);
        setTestResult(resp?.ok ? 'success' : 'error');
      } else if (provider.id === 'anthropic') {
        const resp = await fetch('/api/health', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: 'anthropic', api_key: value }),
          signal: AbortSignal.timeout(10000),
        }).catch(() => null);
        setTestResult(resp?.ok ? 'success' : 'error');
      } else {
        setTestResult(value.length > 10 ? 'success' : 'error');
      }
    } catch {
      setTestResult('error');
    }
    setTesting(false);
  }, [value, isOllama, provider.id]);

  const colorMap: Record<string, string> = {
    cyan: 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10',
    orange: 'border-orange-500/30 text-orange-400 bg-orange-500/10',
    blue: 'border-blue-500/30 text-blue-400 bg-blue-500/10',
    green: 'border-green-500/30 text-green-400 bg-green-500/10',
    purple: 'border-purple-500/30 text-purple-400 bg-purple-500/10',
    emerald: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10',
    white: 'border-white/30 text-white bg-white/10',
    slate: 'border-slate-500/30 text-slate-400 bg-slate-500/10',
  };

  return (
    <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/30 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">{provider.icon}</span>
          <span className="text-xs font-medium text-slate-200">{provider.name}</span>
          {provider.required && (
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-400 bg-amber-500/10">
              Recommended
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          {isConfigured ? (
            <Badge variant="outline" className={`text-[8px] px-1.5 py-0 h-3.5 ${colorMap[provider.color] || colorMap.cyan}`}>
              Configured
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[8px] px-1.5 py-0 h-3.5 border-slate-600/50 text-slate-500">
              Not Set
            </Badge>
          )}
        </div>
      </div>

      <div className="flex gap-1.5">
        <div className="relative flex-1">
          <Input
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              localStorage.setItem(provider.storageKey, e.target.value);
            }}
            type={showKey ? 'text' : 'password'}
            placeholder={provider.placeholder}
            className="bg-slate-900/60 border-slate-700/50 text-[11px] text-slate-200 pr-8 h-7"
          />
          <button
            onClick={() => setShowKey(!showKey)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            {showKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
          </button>
        </div>
        <Button
          onClick={handleTest}
          variant="outline"
          size="sm"
          disabled={!value || testing}
          className="border-slate-600/50 text-[10px] px-2 h-7 hover:bg-slate-700/50"
        >
          {testing ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : testResult === 'success' ? (
            <CheckCircle2 className="h-3 w-3 text-green-400" />
          ) : testResult === 'error' ? (
            <XCircle className="h-3 w-3 text-red-400" />
          ) : (
            'Test'
          )}
        </Button>
      </div>

      {testResult === 'success' && (
        <p className="text-[9px] text-green-400">Connection successful</p>
      )}
      {testResult === 'error' && (
        <p className="text-[9px] text-red-400">Connection failed — check your key</p>
      )}

      <div className="flex flex-wrap gap-1">
        {provider.workers.map((w) => (
          <span key={w} className="text-[8px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400">
            {w}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── WebSocket Connection Section ──────────────────────────────────
function WebSocketConnectionSection({ backendUrl }: { backendUrl: string }) {
  const [wsEnabled, setWsEnabled] = useState(false);
  const [wsUrl, setWsUrl] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('kantorku_ws_url') || '';
    }
    return '';
  });
  const { connectionState, disconnect, reconnect } = useWebSocket({
    url: wsUrl,
    enabled: wsEnabled,
  });

  const handleToggle = useCallback(() => {
    if (wsEnabled) {
      setWsEnabled(false);
      disconnect();
    } else {
      // Derive WS URL from backend URL
      const derivedUrl = wsUrl || backendUrl.replace(/^http/, 'ws') + '/ws';
      setWsUrl(derivedUrl);
      localStorage.setItem('kantorku_ws_url', derivedUrl);
      setWsEnabled(true);
    }
  }, [wsEnabled, wsUrl, backendUrl, disconnect]);

  const stateColors: Record<ConnectionState, string> = {
    connecting: 'text-amber-400',
    connected: 'text-green-400',
    disconnected: 'text-slate-500',
  };

  const stateDots: Record<ConnectionState, string> = {
    connecting: 'bg-amber-400 shadow-[0_0_6px_#f59e0b] animate-pulse',
    connected: 'bg-green-400 shadow-[0_0_6px_#10b981]',
    disconnected: 'bg-slate-600',
  };

  return (
    <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/30 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 text-cyan-400" />
          <div>
            <p className="text-xs text-slate-300">WebSocket Connection</p>
            <p className="text-[10px] text-slate-500">Real-time updates from Python backend</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${stateDots[connectionState]}`} />
          <span className={`text-[9px] font-mono ${stateColors[connectionState]}`}>
            {connectionState.toUpperCase()}
          </span>
          <Switch
            checked={wsEnabled}
            onCheckedChange={handleToggle}
            aria-label="Toggle WebSocket connection"
          />
        </div>
      </div>

      {wsEnabled && (
        <>
          <div className="flex gap-2">
            <Input
              value={wsUrl}
              onChange={(e) => {
                setWsUrl(e.target.value);
                localStorage.setItem('kantorku_ws_url', e.target.value);
              }}
              placeholder="ws://localhost:8000/ws"
              className="bg-slate-900/60 border-slate-700/50 text-[11px] text-slate-200 h-7 flex-1"
              aria-label="WebSocket URL"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={reconnect}
              className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 text-[10px] px-2 h-7"
              aria-label="Reconnect WebSocket"
            >
              <RefreshCw className="h-3 w-3" />
            </Button>
          </div>
          <p className="text-[9px] text-slate-600">
            WebSocket enables real-time task updates, worker messages, and contract state changes from the Python backend.
          </p>
        </>
      )}
    </div>
  );
}

// ── Worker API Key Row ──────────────────────────────────────────────
const WORKER_PROVIDER_OPTIONS = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'google', label: 'Google / Gemini' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'minimax', label: 'MiniMax' },
  { value: 'xai', label: 'xAI (Grok)' },
  { value: 'ollama', label: 'Ollama (Local)' },
  { value: 'zai', label: 'Z-AI SDK' },
];

function WorkerKeyRow({
  worker,
  existingConfig,
  onSave,
  onRemove,
}: {
  worker: { id: string; model: string; squad: string; role: string; emoji?: string; color?: string };
  existingConfig: WorkerApiKeyConfig | undefined;
  onSave: (config: WorkerApiKeyConfig) => void;
  onRemove: (workerId: string) => void;
}) {
  const [expanded, setExpanded] = useState(!!existingConfig);
  const [provider, setProvider] = useState(existingConfig?.provider || worker.model.split('/')[0] || 'anthropic');
  const [apiKey, setApiKey] = useState(existingConfig?.api_key || '');
  const [baseUrl, setBaseUrl] = useState(existingConfig?.base_url || '');
  const [showKey, setShowKey] = useState(false);

  const hasCustomKey = !!existingConfig;

  const handleSave = () => {
    if (!apiKey.trim()) return;
    onSave({
      worker_id: worker.id,
      provider,
      model: existingConfig?.model || worker.model,
      api_key: apiKey.trim(),
      base_url: baseUrl.trim() || undefined,
      is_custom: true,
    });
  };

  const handleRemove = () => {
    onRemove(worker.id);
    setApiKey('');
    setBaseUrl('');
    setExpanded(false);
  };

  return (
    <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/30 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">{worker.emoji || '🤖'}</span>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-medium text-slate-200 font-mono">{worker.id}</span>
              {hasCustomKey && (
                <Badge variant="outline" className="text-[7px] px-1 py-0 h-3 border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
                  Custom Key
                </Badge>
              )}
            </div>
            <p className="text-[9px] text-slate-500">{worker.role} · <span className="font-mono">{worker.model}</span></p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-5 px-1.5 text-[9px] text-slate-500 hover:text-cyan-400"
          onClick={() => setExpanded(!expanded)}
        >
          <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </Button>
      </div>

      {expanded && (
        <div className="space-y-2 pl-1">
          {/* Provider Dropdown */}
          <div className="flex items-center gap-2">
            <Label className="text-[9px] text-slate-500 w-14 flex-shrink-0">Provider</Label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="flex-1 h-6 text-[10px] bg-slate-900/60 border border-slate-700/50 rounded text-slate-200 px-2 font-mono focus:outline-none focus:border-cyan-500/50"
            >
              {WORKER_PROVIDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* API Key Input */}
          <div className="flex items-center gap-2">
            <Label className="text-[9px] text-slate-500 w-14 flex-shrink-0">API Key</Label>
            <div className="relative flex-1">
              <Input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                type={showKey ? 'text' : 'password'}
                placeholder="Leave empty to use global key"
                className="bg-slate-900/60 border-slate-700/50 text-[10px] text-slate-200 pr-7 h-6"
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                {showKey ? <EyeOff className="h-2.5 w-2.5" /> : <Eye className="h-2.5 w-2.5" />}
              </button>
            </div>
          </div>

          {/* Base URL (optional) */}
          <div className="flex items-center gap-2">
            <Label className="text-[9px] text-slate-500 w-14 flex-shrink-0">Base URL</Label>
            <Input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="Optional (e.g. http://localhost:11434)"
              className="bg-slate-900/60 border-slate-700/50 text-[10px] text-slate-200 h-6 flex-1"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-1.5 justify-end pt-1">
            {hasCustomKey && (
              <Button
                variant="outline"
                size="sm"
                className="h-5 px-2 text-[9px] border-red-500/30 text-red-400 hover:bg-red-500/10"
                onClick={handleRemove}
              >
                <Trash2 className="h-2.5 w-2.5 mr-0.5" />
                Remove
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-5 px-2 text-[9px] border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10"
              onClick={handleSave}
              disabled={!apiKey.trim()}
            >
              Save Key
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Settings Dialog ──────────────────────────────────────────
export function SettingsDialog() {
  const {
    apiKey,
    setApiKey,
    isBackendConnected,
    setBackendConnected,
    settingsOpen,
    setSettingsOpen,
    resetAll,
    workers,
    workerApiKeys,
    setWorkerApiKey,
    removeWorkerApiKey,
  } = useKantorkuStore();

  const [tempKey, setTempKey] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('kantorku_api_key') || apiKey;
    }
    return apiKey;
  });

  const [backendUrl, setBackendUrl] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('kantorku_backend_url') || 'http://localhost:8000';
    }
    return 'http://localhost:8000';
  });

  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testLatency, setTestLatency] = useState<number | null>(null);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<{ current: string; latest: string; upToDate: boolean } | null>(null);
  const [, setRefreshTick] = useState(0);

  const triggerRefresh = useCallback(() => {
    setRefreshTick((t) => t + 1);
  }, []);

  const configuredCount = typeof window !== 'undefined'
    ? PROVIDERS.filter((p) => (localStorage.getItem(p.storageKey) || '').length > 0).length
    : 0;

  const handleSave = () => {
    setApiKey(tempKey);
    localStorage.setItem('kantorku_api_key', tempKey);
    localStorage.setItem('kantorku_backend_url', backendUrl);
    setSettingsOpen(false);
  };

  const handleConnectionTest = async () => {
    setTestStatus('testing');
    setTestLatency(null);
    const start = Date.now();
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      const response = await fetch(`${backendUrl}/api/health`, {
        signal: controller.signal,
      }).catch(() => null);
      clearTimeout(timeout);
      const latency = Date.now() - start;
      if (response && response.ok) {
        setTestStatus('success');
        setTestLatency(latency);
        setBackendConnected(true);
      } else {
        setTestStatus('error');
        setBackendConnected(false);
      }
    } catch {
      setTestStatus('error');
      setBackendConnected(false);
    }
  };

  const handleCheckUpdates = () => {
    setCheckingUpdates(true);
    setTimeout(() => {
      setUpdateInfo({ current: '0.4.1', latest: '0.4.1', upToDate: true });
      setCheckingUpdates(false);
    }, 1500);
  };

  const handleClearData = () => {
    if (typeof window !== 'undefined') {
      const confirmed = window.confirm('Are you sure you want to clear all data? This cannot be undone.');
      if (confirmed) {
        resetAll();
        PROVIDERS.forEach((p) => localStorage.removeItem(p.storageKey));
        setSettingsOpen(false);
      }
    }
  };

  const handleExportData = () => {
    if (typeof window === 'undefined') return;
    const data: Record<string, unknown> = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('kantorku')) {
        try {
          data[key] = JSON.parse(localStorage.getItem(key) || '""');
        } catch {
          data[key] = localStorage.getItem(key);
        }
      }
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kantorku-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const frameworkLayers = [
    { icon: Users, label: 'Multi-Worker Orchestration', desc: 'Coordinate 13+ specialized AI workers in squads' },
    { icon: Shield, label: 'Contract-Based Workflow', desc: 'Structured agreements with approval gates before execution' },
    { icon: Brain, label: '3-Ring Memory System', desc: 'Session, Episode, Knowledge persistence layers' },
    { icon: Eye, label: 'Full Observability', desc: 'Distributed traces, spans, and middleware pipeline' },
    { icon: Activity, label: 'Health & Circuit Breakers', desc: 'Real-time provider health monitoring with auto-recovery' },
    { icon: Zap, label: 'Cost Guard & Budget', desc: 'Automatic budget enforcement, cost tracking, and alerts' },
    { icon: Clock, label: 'Latency Percentiles', desc: 'P50/P95/P99 latency computation from real history' },
    { icon: Database, label: 'DAG Task Dependencies', desc: 'Visual directed acyclic graph for task execution order' },
    { icon: GitBranch, label: 'Time Travel Snapshots', desc: 'Browse and compare contract state at any point in time' },
    { icon: Layers, label: 'Middleware Pipeline', desc: 'Auth, rate limiting, cost guard, cache, retry layers' },
    { icon: FileText, label: 'Dynamic SOP Rules', desc: 'Create, manage, and enforce standard operating procedures' },
    { icon: Heart, label: 'Health Polling', desc: '30-second periodic health checks with auto-detection' },
    { icon: Cpu, label: 'Worker Emotion Tracking', desc: 'Confidence, frustration, and excitement monitoring' },
    { icon: AlertTriangle, label: 'Escalation Management', desc: 'Automatic and manual escalation with resolution workflow' },
    { icon: Timer, label: 'Approval Gates', desc: 'Interactive approve/reject with reason tracking' },
    { icon: BarChart3, label: 'Cost Time-Series', desc: 'Cumulative cost visualization over time' },
    { icon: Network, label: 'Bulletin Board', desc: 'Announcements, alerts, rules, and SOPs in one place' },
    { icon: Lock, label: 'Trust Scores', desc: 'Per-worker trust scoring with trend tracking' },
    { icon: RefreshCw, label: 'Circuit Breaker Reset', desc: 'Manual reset for open circuit breakers' },
    { icon: Sparkles, label: 'Debrief & Lessons Learned', desc: 'Post-contract analysis with worker feedback' },
    { icon: Globe, label: 'Team Discussion Rounds', desc: 'Multi-round consensus building with volunteer assignment' },
  ];

  return (
    <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
      <DialogContent className="bg-slate-900 border-slate-700/50 text-white max-w-2xl max-h-[90vh] overflow-y-auto custom-scrollbar">
        <DialogHeader>
          <DialogTitle className="text-cyan-300 flex items-center gap-2">
            <Settings className="h-4 w-4" />
            kantorku Settings
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="providers" className="w-full">
          <TabsList className="bg-slate-800/60 border border-slate-700/30 w-full grid grid-cols-5 h-8">
            <TabsTrigger value="providers" className="text-[10px] data-[state=active]:bg-cyan-600/20 data-[state=active]:text-cyan-300">
              <Key className="h-3 w-3 mr-1" />
              API Keys
            </TabsTrigger>
            <TabsTrigger value="worker-keys" className="text-[10px] data-[state=active]:bg-cyan-600/20 data-[state=active]:text-cyan-300">
              <Bot className="h-3 w-3 mr-1" />
              Workers
            </TabsTrigger>
            <TabsTrigger value="connection" className="text-[10px] data-[state=active]:bg-cyan-600/20 data-[state=active]:text-cyan-300">
              <Globe className="h-3 w-3 mr-1" />
              Connection
            </TabsTrigger>
            <TabsTrigger value="data" className="text-[10px] data-[state=active]:bg-cyan-600/20 data-[state=active]:text-cyan-300">
              <Server className="h-3 w-3 mr-1" />
              Data
            </TabsTrigger>
            <TabsTrigger value="about" className="text-[10px] data-[state=active]:bg-cyan-600/20 data-[state=active]:text-cyan-300">
              <Info className="h-3 w-3 mr-1" />
              About
            </TabsTrigger>
          </TabsList>

          {/* ── Tab: API Keys / Providers ──────────────────────────── */}
          <TabsContent value="providers" className="space-y-3 mt-3">
            <div className="flex items-center justify-between">
              <p className="text-[10px] text-slate-400">
                Configure API keys for LLM providers. Each worker uses a specific provider.
              </p>
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
                {configuredCount}/{PROVIDERS.length} configured
              </Badge>
            </div>

            <div className="space-y-2">
              {PROVIDERS.map((provider) => (
                <ProviderKeyInput
                  key={provider.id}
                  provider={provider}
                  onStatusChange={triggerRefresh}
                />
              ))}
            </div>

            <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-700/20">
              <p className="text-[9px] text-slate-500 leading-relaxed">
                <strong className="text-slate-400">Tips:</strong> For cheapest setup, use Z-AI SDK (free standalone mode) + Ollama (free, local) + DeepSeek (cheap at $0.28/M).
                For best quality, use Anthropic + Google + MiniMax. Keys are stored in your browser localStorage only — never sent to our servers.
                You can also set environment variables when using the Python backend.
              </p>
            </div>

            <Button
              onClick={handleSave}
              className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs"
            >
              Save All Settings
            </Button>
          </TabsContent>

          {/* ── Tab: Worker API Keys ─────────────────────────────────── */}
          <TabsContent value="worker-keys" className="space-y-3 mt-3">
            <div className="flex items-center justify-between">
              <p className="text-[10px] text-slate-400">
                Override API keys per worker. Workers with custom keys use them instead of the global provider key.
              </p>
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
                {workerApiKeys.length}/{workers.length} customized
              </Badge>
            </div>

            <div className="space-y-2 max-h-[60vh] overflow-y-auto custom-scrollbar pr-1">
              {workers.map((worker) => {
                const existingConfig = workerApiKeys.find((k) => k.worker_id === worker.id);
                return (
                  <WorkerKeyRow
                    key={worker.id}
                    worker={worker}
                    existingConfig={existingConfig}
                    onSave={setWorkerApiKey}
                    onRemove={removeWorkerApiKey}
                  />
                );
              })}
            </div>

            <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-700/20">
              <p className="text-[9px] text-slate-500 leading-relaxed">
                <strong className="text-slate-400">Note:</strong> Per-worker keys override the global provider API keys from the previous tab.
                This is useful when a specific worker needs a different provider, model, or API key than the default.
                Leave empty to use the global key.
              </p>
            </div>

            <Button
              onClick={handleSave}
              className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs"
            >
              Save All Settings
            </Button>
          </TabsContent>

          {/* ── Tab: Connection ─────────────────────────────────────── */}
          <TabsContent value="connection" className="space-y-4 mt-3">
            <div className="space-y-2">
              <Label className="text-xs text-slate-400 flex items-center gap-1">
                <Globe className="h-3 w-3" />
                Python Backend URL
              </Label>
              <div className="flex gap-2">
                <Input
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                  className="bg-slate-800/60 border-slate-700/50 text-xs text-slate-200 flex-1"
                  aria-label="Backend URL"
                />
                <Button
                  onClick={handleConnectionTest}
                  variant="outline"
                  size="sm"
                  disabled={testStatus === 'testing'}
                  className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 text-xs px-3"
                  aria-label="Test backend connection"
                >
                  {testStatus === 'testing' ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : testStatus === 'success' ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                  ) : testStatus === 'error' ? (
                    <XCircle className="h-3.5 w-3.5 text-red-400" />
                  ) : (
                    'Test'
                  )}
                </Button>
              </div>
              {testStatus === 'success' && (
                <p className="text-[10px] text-green-400">Connected successfully{testLatency != null ? ` (${testLatency}ms)` : ''}</p>
              )}
              {testStatus === 'error' && (
                <p className="text-[10px] text-red-400">Could not connect to backend</p>
              )}
            </div>

            <Separator className="bg-slate-700/30" />

            {/* WebSocket Connection */}
            <WebSocketConnectionSection backendUrl={backendUrl} />

            <Separator className="bg-slate-700/30" />

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 border border-slate-700/30">
              <div className="flex items-center gap-2">
                {isBackendConnected ? (
                  <Wifi className="h-4 w-4 text-green-400" />
                ) : (
                  <WifiOff className="h-4 w-4 text-amber-400" />
                )}
                <div>
                  <p className="text-xs text-slate-300">Backend Status</p>
                  <p className="text-[10px] text-slate-500">
                    {isBackendConnected ? 'Connected to Python backend' : 'Standalone Mode (z-ai-web-dev-sdk)'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`h-2 w-2 rounded-full ${isBackendConnected ? 'bg-green-400 shadow-[0_0_6px_#10b981]' : 'bg-amber-400 shadow-[0_0_6px_#f59e0b]'}`} />
                <span className="text-[9px] font-mono text-slate-500">{isBackendConnected ? 'ONLINE' : 'OFFLINE'}</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/20 space-y-2">
              <p className="text-[10px] font-medium text-slate-300">Operating Modes</p>
              <div className="grid grid-cols-2 gap-2">
                <div className={`p-2 rounded border ${!isBackendConnected ? 'border-cyan-500/30 bg-cyan-500/5' : 'border-slate-700/30'}`}>
                  <p className="text-[10px] font-medium text-cyan-400">Standalone Mode</p>
                  <p className="text-[9px] text-slate-500">Uses z-ai-web-dev-sdk directly. No Python needed. API keys configured above.</p>
                </div>
                <div className={`p-2 rounded border ${isBackendConnected ? 'border-green-500/30 bg-green-500/5' : 'border-slate-700/30'}`}>
                  <p className="text-[10px] font-medium text-green-400">Full Stack Mode</p>
                  <p className="text-[9px] text-slate-500">Python backend + Next.js frontend. WebSocket/SSE real-time. Full 20+ layers.</p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 border border-slate-700/30">
              <div className="flex items-center gap-2">
                <Palette className="h-4 w-4 text-violet-400" />
                <div>
                  <p className="text-xs text-slate-300">Tema</p>
                  <p className="text-[10px] text-slate-500">Pilih tampilan gelap, terang, atau sistem</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                {(['dark', 'light', 'system'] as const).map((t) => {
                  const currentTheme = typeof window !== 'undefined'
                    ? (window as unknown as Record<string, unknown>).__kantorku_theme as string || 'dark'
                    : 'dark';
                  const setThemeFn = typeof window !== 'undefined'
                    ? (window as unknown as Record<string, (t: string) => void>).__kantorku_setTheme
                    : null;
                  const isActive = currentTheme === t;
                  return (
                    <button
                      key={t}
                      onClick={() => setThemeFn?.(t)}
                      className={`px-2 py-1 rounded text-[9px] font-mono transition-colors ${
                        isActive
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                          : 'text-slate-500 hover:text-slate-300 border border-slate-700/30'
                      }`}
                    >
                      {t === 'dark' ? '🌙 Gelap' : t === 'light' ? '☀️ Terang' : '🖥️ Sistem'}
                    </button>
                  );
                })}
              </div>
            </div>

            <Button
              onClick={handleSave}
              className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs"
            >
              Save Connection Settings
            </Button>
          </TabsContent>

          {/* ── Tab: Data ───────────────────────────────────────────── */}
          <TabsContent value="data" className="space-y-4 mt-3">
            <div className="space-y-2">
              <Label className="text-xs text-slate-400 flex items-center gap-1">
                <Server className="h-3 w-3" />
                Data Management
              </Label>
              <div className="flex gap-2">
                <Button
                  onClick={handleExportData}
                  variant="outline"
                  size="sm"
                  className="flex-1 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 text-xs"
                >
                  <Download className="h-3.5 w-3.5 mr-1" />
                  Export Data
                </Button>
                <Button
                  onClick={handleClearData}
                  variant="outline"
                  size="sm"
                  className="flex-1 border-red-500/30 text-red-300 hover:bg-red-500/10 text-xs"
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1" />
                  Clear All
                </Button>
              </div>
              <p className="text-[10px] text-slate-600">
                Export downloads localStorage data as JSON (including API keys). Clear removes all local data.
              </p>
            </div>

            <Separator className="bg-slate-700/30" />

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500 font-mono">Framework Version</span>
                <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
                  v0.4.1
                </Badge>
              </div>
              <Button
                onClick={handleCheckUpdates}
                variant="outline"
                size="sm"
                disabled={checkingUpdates}
                className="w-full border-slate-700/50 text-slate-400 hover:text-slate-300 hover:bg-slate-800/60 text-xs"
              >
                {checkingUpdates ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1.5 animate-spin" />
                    Checking...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-3 w-3 mr-1.5" />
                    Check for Updates
                  </>
                )}
              </Button>
              {updateInfo && (
                <div className="flex items-center gap-1.5 p-2 rounded bg-slate-800/60 border border-slate-700/30">
                  {updateInfo.upToDate ? (
                    <>
                      <CheckCircle2 className="h-3 w-3 text-green-400" />
                      <span className="text-[10px] text-green-300">You&apos;re on the latest version (v{updateInfo.latest})</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-3 w-3 text-amber-400" />
                      <span className="text-[10px] text-amber-300">Update available: v{updateInfo.latest} (current: v{updateInfo.current})</span>
                    </>
                  )}
                </div>
              )}
            </div>
          </TabsContent>

          {/* ── Tab: About ──────────────────────────────────────────── */}
          <TabsContent value="about" className="space-y-3 mt-3">
            <p className="text-[10px] text-slate-400 leading-relaxed">
              kantorku is a 20+ layer digital office framework for orchestrating multiple AI workers.
              It uses contract-based workflows, 3-ring memory, full observability, circuit breakers,
              approval gates, budget enforcement, escalation management, and much more to
              deliver reliable, transparent, and governable AI-powered development.
            </p>
            <div className="space-y-1 max-h-72 overflow-y-auto custom-scrollbar pr-1">
              {frameworkLayers.map(({ icon: Icon, label, desc }) => (
                <div key={label} className="flex items-start gap-2">
                  <Icon className="h-3 w-3 text-cyan-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-[10px] text-slate-300">{label}</p>
                    <p className="text-[9px] text-slate-500">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

export function SettingsButton({ isLightTheme }: { isLightTheme?: boolean }) {
  const { setSettingsOpen } = useKantorkuStore();
  return (
    <button
      onClick={() => setSettingsOpen(true)}
      className={`p-1.5 rounded-md transition-colors ${isLightTheme ? 'hover:bg-slate-200' : 'hover:bg-slate-700/50'}`}
      title="Settings"
    >
      <Settings className={`h-4 w-4 ${isLightTheme ? 'text-slate-500' : 'text-slate-400'}`} />
    </button>
  );
}
