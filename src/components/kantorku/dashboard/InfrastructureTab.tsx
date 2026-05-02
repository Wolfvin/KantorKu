'use client';

import { useState } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Heart,
  Shield,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Bell,
  FileText,
  Server,
  Info,
  Plus,
} from 'lucide-react';
import { ProviderPipelinePanel } from '../ProviderPipelinePanel';
import { ContextPoolPanel } from '../ContextPoolPanel';
import { CrashRecoveryPanel } from '../CrashRecoveryPanel';

const cbStateColors: Record<string, string> = {
  closed: '#10b981',
  open: '#ef4444',
  half_open: '#f59e0b',
};

export function InfrastructureTab() {
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

      {/* Provider Pipeline Visualization */}
      <ProviderPipelinePanel />

      {/* Context Pool Visualization */}
      <ContextPoolPanel />

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

      {/* Crash Recovery Panel */}
      <CrashRecoveryPanel />

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
            <div key={`sop-${i}`} className="flex items-start gap-1.5 py-0.5">
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
