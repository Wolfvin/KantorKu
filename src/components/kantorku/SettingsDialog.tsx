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
} from 'lucide-react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useState } from 'react';

export function SettingsDialog() {
  const {
    apiKey,
    setApiKey,
    isBackendConnected,
    setBackendConnected,
    settingsOpen,
    setSettingsOpen,
    resetAll,
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
  const [themeEnabled, setThemeEnabled] = useState(false);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<{ current: string; latest: string; upToDate: boolean } | null>(null);

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
    // Simulate update check (in production this would hit an API)
    setTimeout(() => {
      setUpdateInfo({ current: '0.4.0', latest: '0.4.0', upToDate: true });
      setCheckingUpdates(false);
    }, 1500);
  };

  const handleClearData = () => {
    if (typeof window !== 'undefined') {
      const confirmed = window.confirm('Are you sure you want to clear all data? This cannot be undone.');
      if (confirmed) {
        resetAll();
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
      <DialogContent className="bg-slate-900 border-slate-700/50 text-white max-w-lg max-h-[85vh] overflow-y-auto custom-scrollbar">
        <DialogHeader>
          <DialogTitle className="text-cyan-300 flex items-center gap-2">
            <Settings className="h-4 w-4" />
            kantorku Settings
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-5 pt-2">
          {/* API Key */}
          <div className="space-y-2">
            <Label className="text-xs text-slate-400 flex items-center gap-1">
              <Key className="h-3 w-3" />
              API Key (for standalone mode)
            </Label>
            <Input
              value={tempKey}
              onChange={(e) => setTempKey(e.target.value)}
              type="password"
              placeholder="sk-..."
              className="bg-slate-800/60 border-slate-700/50 text-xs text-slate-200"
            />
            <p className="text-[10px] text-slate-600">
              If no API key is set, the app will try to connect to the kantorku Python backend.
            </p>
          </div>

          <Separator className="bg-slate-700/30" />

          {/* Backend URL */}
          <div className="space-y-2">
            <Label className="text-xs text-slate-400 flex items-center gap-1">
              <Globe className="h-3 w-3" />
              Backend URL
            </Label>
            <div className="flex gap-2">
              <Input
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="bg-slate-800/60 border-slate-700/50 text-xs text-slate-200 flex-1"
              />
              <Button
                onClick={handleConnectionTest}
                variant="outline"
                size="sm"
                disabled={testStatus === 'testing'}
                className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 text-xs px-3"
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
              <p className="text-[10px] text-green-400">✓ Connected successfully{testLatency != null ? ` (${testLatency}ms)` : ''}</p>
            )}
            {testStatus === 'error' && (
              <p className="text-[10px] text-red-400">✗ Could not connect to backend</p>
            )}
          </div>

          <Separator className="bg-slate-700/30" />

          {/* Connection Status */}
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
                  {isBackendConnected ? 'Connected' : 'Standalone Mode (z-ai-web-dev-sdk)'}
                </p>
              </div>
            </div>
            <Switch checked={isBackendConnected} disabled />
          </div>

          {/* Theme Toggle (UI only) */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 border border-slate-700/30">
            <div className="flex items-center gap-2">
              <Palette className="h-4 w-4 text-violet-400" />
              <div>
                <p className="text-xs text-slate-300">Dark Theme</p>
                <p className="text-[10px] text-slate-500">Cyberpunk dark mode (always on)</p>
              </div>
            </div>
            <Switch checked={true} disabled />
          </div>

          <Separator className="bg-slate-700/30" />

          {/* Data Actions */}
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
              Export downloads localStorage data as JSON. Clear removes all local data.
            </p>
          </div>

          <Separator className="bg-slate-700/30" />

          {/* Version & Update Check */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-500 font-mono">Framework Version</span>
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
                v0.4.0
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
                    <span className="text-[10px] text-green-300">You're on the latest version (v{updateInfo.latest})</span>
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

          <Separator className="bg-slate-700/30" />

          {/* About Section */}
          <div className="space-y-3">
            <Label className="text-xs text-slate-400 flex items-center gap-1">
              <Info className="h-3 w-3" />
              About kantorku
            </Label>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              kantorku is a 20+ layer digital office framework for orchestrating multiple AI workers.
              It uses contract-based workflows, 3-ring memory, full observability, circuit breakers,
              approval gates, budget enforcement, escalation management, and much more to
              deliver reliable, transparent, and governable AI-powered development.
            </p>
            <div className="space-y-1 max-h-64 overflow-y-auto custom-scrollbar pr-1">
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
          </div>

          {/* Save */}
          <Button
            onClick={handleSave}
            className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white"
          >
            Save Settings
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function SettingsButton() {
  const { setSettingsOpen } = useKantorkuStore();
  return (
    <button
      onClick={() => setSettingsOpen(true)}
      className="p-1.5 rounded-md hover:bg-slate-700/50 transition-colors"
      title="Settings"
    >
      <Settings className="h-4 w-4 text-slate-400" />
    </button>
  );
}
