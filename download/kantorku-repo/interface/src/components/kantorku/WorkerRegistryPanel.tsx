'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { WorkerIdentity } from '@/lib/kantorku/types';
import { SQUADS } from '@/lib/kantorku/workers-data';
import {
  Users, UserPlus, UserMinus, Search, Activity,
  Zap, Shield, TrendingUp, TrendingDown, Minus,
  Plug, Eye, RefreshCw, AlertCircle,
} from 'lucide-react';

const STATUS_COLORS: Record<string, { dot: string; bg: string; text: string }> = {
  idle: { dot: 'bg-slate-500', bg: 'bg-slate-800/60', text: 'text-slate-400' },
  busy: { dot: 'bg-cyan-400 animate-pulse', bg: 'bg-cyan-950/40', text: 'text-cyan-300' },
  error: { dot: 'bg-red-400', bg: 'bg-red-950/40', text: 'text-red-300' },
  offline: { dot: 'bg-slate-700', bg: 'bg-slate-900/60', text: 'text-slate-600' },
};

const WORKER_TEMPLATES: Array<{ id: string; role: string; model: string; emoji: string; squad: string }> = [
  { id: 'researcher', role: 'Research Specialist', model: 'google/gemma-3-27b', emoji: '🔬', squad: 'research' },
  { id: 'architect', role: 'System Architect', model: 'anthropic/claude-opus-4-6', emoji: '🏗️', squad: 'engineering' },
  { id: 'devops', role: 'DevOps Engineer', model: 'openai/gpt-4.1', emoji: '🚀', squad: 'engineering' },
  { id: 'qa_tester', role: 'QA Tester', model: 'google/gemini-2.5-pro', emoji: '🧪', squad: 'verification' },
  { id: 'data_analyst', role: 'Data Analyst', model: 'meta/llama4-maverick', emoji: '📈', squad: 'research' },
  { id: 'ux_designer', role: 'UX Designer', model: 'anthropic/claude-sonnet-4', emoji: '🎯', squad: 'documentation' },
];

export function WorkerRegistryPanel() {
  const { workers, hireWorker, fireWorker, trustScores, workerEmotions, delegations } = useKantorkuStore();
  const [showHireForm, setShowHireForm] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [confirmFireId, setConfirmFireId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Hire form state
  const [hireForm, setHireForm] = useState({
    id: '',
    model: 'openai/gpt-4.1-mini',
    squad: 'engineering',
    role: '',
    emoji: '🤖',
  });

  const filteredWorkers = workers.filter((w) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      w.id.toLowerCase().includes(q) ||
      w.role.toLowerCase().includes(q) ||
      w.squad.toLowerCase().includes(q) ||
      w.model.toLowerCase().includes(q)
    );
  });

  const handleHire = () => {
    if (!hireForm.id.trim() || !hireForm.role.trim()) return;
    const existing = workers.find((w) => w.id === hireForm.id);
    if (existing) return;

    const newWorker: WorkerIdentity = {
      id: hireForm.id.trim(),
      model: hireForm.model,
      squad: hireForm.squad,
      role: hireForm.role.trim(),
      skill_md: `Custom worker: ${hireForm.role.trim()}`,
      personality: 'Custom worker',
      emoji: hireForm.emoji,
      color: '#06b6d4',
      status: 'idle',
      is_custom: true,
      hired_at: new Date().toISOString(),
      trust_score: 50,
      total_tasks: 0,
      success_rate: 0,
    };
    hireWorker(newWorker);
    setHireForm({ id: '', model: 'openai/gpt-4.1-mini', squad: 'engineering', role: '', emoji: '🤖' });
    setShowHireForm(false);
  };

  const handleFire = (id: string) => {
    fireWorker(id);
    setConfirmFireId(null);
  };

  const handleTemplateHire = (template: typeof WORKER_TEMPLATES[0]) => {
    const existing = workers.find((w) => w.id === template.id);
    if (existing) return;

    const newWorker: WorkerIdentity = {
      id: template.id,
      model: template.model,
      squad: template.squad,
      role: template.role,
      skill_md: `Template worker: ${template.role}`,
      personality: 'Template worker',
      emoji: template.emoji,
      color: '#06b6d4',
      status: 'idle',
      is_custom: true,
      hired_at: new Date().toISOString(),
      trust_score: 50,
      total_tasks: 0,
      success_rate: 0,
    };
    hireWorker(newWorker);
  };

  const getWorkerTrust = (id: string) => trustScores.find((t) => t.worker_id === id);
  const getWorkerEmotion = (id: string) => workerEmotions.find((e) => e.worker_id === id);
  const getWorkerDelegations = (id: string) => delegations.filter((d) => d.from_worker === id || d.to_worker === id);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40 space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Worker Registry</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-cyan-500/30 text-cyan-300 font-mono">
              {workers.length} workers
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1.5 text-[9px] text-slate-500 hover:text-teal-400"
              onClick={() => setShowTemplates(!showTemplates)}
            >
              <Eye className="h-3 w-3 mr-0.5" />
              Templates
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1.5 text-[9px] text-slate-500 hover:text-green-400"
              onClick={() => setShowHireForm(!showHireForm)}
            >
              <UserPlus className="h-3 w-3 mr-0.5" />
              Hire
            </Button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2 text-slate-600" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search workers..."
            className="h-6 text-[10px] pl-7 bg-slate-800/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2">
        {/* Hire Form */}
        {showHireForm && (
          <Card className="bg-slate-800/60 border-green-500/30 backdrop-blur-sm">
            <CardHeader className="p-2.5 pb-1">
              <div className="flex items-center gap-1.5">
                <UserPlus className="h-3 w-3 text-green-400" />
                <CardTitle className="text-[10px] text-green-300 font-mono uppercase">Hire New Worker</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-2.5 pt-0 space-y-1.5">
              <div className="grid grid-cols-2 gap-1.5">
                <Input
                  value={hireForm.id}
                  onChange={(e) => setHireForm({ ...hireForm, id: e.target.value })}
                  placeholder="Worker ID"
                  className="h-6 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
                />
                <Input
                  value={hireForm.emoji}
                  onChange={(e) => setHireForm({ ...hireForm, emoji: e.target.value })}
                  placeholder="Emoji"
                  className="h-6 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
                />
              </div>
              <Input
                value={hireForm.role}
                onChange={(e) => setHireForm({ ...hireForm, role: e.target.value })}
                placeholder="Role (e.g. Backend Developer)"
                className="h-6 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
              />
              <Input
                value={hireForm.model}
                onChange={(e) => setHireForm({ ...hireForm, model: e.target.value })}
                placeholder="Model (e.g. openai/gpt-4.1-mini)"
                className="h-6 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
              />
              <select
                value={hireForm.squad}
                onChange={(e) => setHireForm({ ...hireForm, squad: e.target.value })}
                className="h-6 text-[10px] bg-slate-900/60 border border-slate-700/50 text-slate-300 rounded-md px-2 w-full"
              >
                {SQUADS.map((s) => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
              <div className="flex gap-1.5">
                <Button
                  size="sm"
                  className="h-6 text-[9px] bg-green-600 hover:bg-green-500 text-white px-3"
                  onClick={handleHire}
                  disabled={!hireForm.id.trim() || !hireForm.role.trim()}
                >
                  <UserPlus className="h-3 w-3 mr-1" />
                  Hire
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-[9px] text-slate-500"
                  onClick={() => setShowHireForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Templates */}
        {showTemplates && (
          <Card className="bg-slate-800/60 border-teal-500/30 backdrop-blur-sm">
            <CardHeader className="p-2.5 pb-1">
              <div className="flex items-center gap-1.5">
                <RefreshCw className="h-3 w-3 text-teal-400" />
                <CardTitle className="text-[10px] text-teal-300 font-mono uppercase">Worker Templates</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-2.5 pt-0 space-y-1">
              {WORKER_TEMPLATES.map((template) => {
                const alreadyHired = workers.some((w) => w.id === template.id);
                return (
                  <div key={template.id} className="flex items-center gap-2 p-1.5 rounded bg-slate-900/40 border border-slate-700/15">
                    <span className="text-sm">{template.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-white font-medium">{template.role}</p>
                      <p className="text-[8px] text-slate-500 font-mono">{template.id} · {template.model}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 px-1.5 text-[8px]"
                      disabled={alreadyHired}
                      onClick={() => handleTemplateHire(template)}
                    >
                      {alreadyHired ? '✓' : <UserPlus className="h-3 w-3 text-teal-400" />}
                    </Button>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}

        {/* Worker List */}
        {filteredWorkers.map((worker) => {
          const statusStyle = STATUS_COLORS[worker.status || 'idle'] || STATUS_COLORS.idle;
          const trust = getWorkerTrust(worker.id);
          const emotion = getWorkerEmotion(worker.id);
          const workerDelegations = getWorkerDelegations(worker.id);
          const trustScore = trust?.score ?? worker.trust_score ?? 0;
          const trend = trust?.trend;

          return (
            <Card
              key={worker.id}
              className="bg-slate-800/40 border-slate-700/20 backdrop-blur-sm transition-all duration-200"
              style={{
                boxShadow: worker.status === 'busy' ? `0 0 8px ${worker.color}22` : 'none',
              }}
            >
              <CardContent className="p-2.5">
                <div className="flex items-start gap-2">
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-lg text-base flex-shrink-0"
                    style={{ backgroundColor: `${worker.color}20` }}
                  >
                    {worker.emoji}
                  </div>
                  <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex items-center gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${statusStyle.dot}`} />
                      <span className="text-[11px] font-mono text-white font-medium">{worker.id}</span>
                      {worker.is_custom && (
                        <Badge variant="outline" className="text-[7px] px-0.5 py-0 h-3 border-amber-500/30 text-amber-300">
                          custom
                        </Badge>
                      )}
                      <Plug className="h-2.5 w-2.5 text-green-400" title="Hot-plug capable" />
                    </div>

                    {/* Role & Model */}
                    <p className="text-[9px] text-slate-400 mt-0.5">{worker.role}</p>
                    <p className="text-[8px] text-slate-600 font-mono truncate">{worker.model}</p>

                    {/* Badges */}
                    <div className="flex items-center gap-1 mt-1">
                      <Badge
                        variant="outline"
                        className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-500"
                      >
                        {worker.squad}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={`text-[8px] px-1 py-0 h-3.5 ${statusStyle.text}`}
                      >
                        {worker.status || 'idle'}
                      </Badge>
                      {worker.current_task && (
                        <Badge variant="outline" className="text-[7px] px-0.5 py-0 h-3 border-cyan-500/30 text-cyan-300 truncate max-w-[100px]">
                          {worker.current_task}
                        </Badge>
                      )}
                    </div>

                    {/* Stats Row */}
                    <div className="flex items-center gap-3 mt-1.5">
                      {/* Trust Score */}
                      <div className="flex items-center gap-1 flex-1 min-w-0">
                        <Shield className="h-2.5 w-2.5 text-slate-500" />
                        <span className="text-[8px] text-slate-500">Trust</span>
                        <div className="flex-1 max-w-[50px]">
                          <Progress
                            value={trustScore}
                            className="h-1 bg-slate-900/60"
                          />
                        </div>
                        <span className="text-[8px] font-mono text-slate-400">{trustScore}</span>
                        {trend && (
                          trend === 'improving' ? <TrendingUp className="h-2.5 w-2.5 text-green-400" /> :
                          trend === 'declining' ? <TrendingDown className="h-2.5 w-2.5 text-red-400" /> :
                          <Minus className="h-2.5 w-2.5 text-slate-600" />
                        )}
                      </div>
                    </div>

                    {/* Task & Success Stats */}
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="flex items-center gap-0.5">
                        <Activity className="h-2.5 w-2.5 text-slate-600" />
                        <span className="text-[8px] text-slate-500 font-mono">{worker.total_tasks ?? 0} tasks</span>
                      </div>
                      <div className="flex items-center gap-0.5">
                        <Zap className="h-2.5 w-2.5 text-slate-600" />
                        <span className="text-[8px] text-slate-500 font-mono">
                          {worker.success_rate !== undefined ? `${(worker.success_rate * 100).toFixed(0)}%` : '—'}
                        </span>
                      </div>
                      {workerDelegations.length > 0 && (
                        <div className="flex items-center gap-0.5">
                          <span className="text-[8px] text-amber-400 font-mono">↔ {workerDelegations.length}</span>
                        </div>
                      )}
                    </div>

                    {/* Emotion */}
                    {emotion && (
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className="text-[8px]">
                          {emotion.emotion === 'confident' ? '💪' :
                           emotion.emotion === 'uncertain' ? '🤔' :
                           emotion.emotion === 'frustrated' ? '😤' :
                           emotion.emotion === 'excited' ? '🤩' : '😐'}
                        </span>
                        <span className="text-[8px] text-slate-500">{emotion.emotion}</span>
                        <span className="text-[8px] text-slate-600 font-mono">({(emotion.confidence * 100).toFixed(0)}%)</span>
                      </div>
                    )}

                    {/* Fire button */}
                    <div className="flex items-center justify-end mt-1.5">
                      {confirmFireId === worker.id ? (
                        <div className="flex items-center gap-1">
                          <AlertCircle className="h-2.5 w-2.5 text-red-400" />
                          <span className="text-[8px] text-red-300">Confirm?</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-4 px-1 text-[8px] text-red-400 hover:text-red-300"
                            onClick={() => handleFire(worker.id)}
                          >
                            Yes
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-4 px-1 text-[8px] text-slate-500"
                            onClick={() => setConfirmFireId(null)}
                          >
                            No
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-4 px-1 text-[8px] text-slate-600 hover:text-red-400"
                          onClick={() => setConfirmFireId(worker.id)}
                        >
                          <UserMinus className="h-2.5 w-2.5 mr-0.5" />
                          Fire
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
