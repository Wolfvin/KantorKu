'use client';

import { useState, useMemo } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { WORKERS } from '@/lib/kantorku/workers-data';
import {
  ScrollText, Search, Filter, Clock, MessageSquare,
  CheckCircle2, AlertTriangle, Lightbulb, FileText, ChevronDown, ChevronRight,
} from 'lucide-react';

type Phase = 'client_discussion' | 'team_briefing' | 'todo_review' | 'execution';
type EntryType = 'message' | 'decision' | 'concern' | 'result';

interface TranscriptEntry {
  id: string;
  phase: Phase;
  type: EntryType;
  worker_id: string;
  content: string;
  timestamp: string;
}

const PHASE_CONFIG: Record<Phase, { label: string; color: string; icon: typeof MessageSquare }> = {
  client_discussion: { label: 'Diskusi Klien', color: '#06b6d4', icon: MessageSquare },
  team_briefing: { label: 'Briefing Tim', color: '#8b5cf6', icon: FileText },
  todo_review: { label: 'Review TODO', color: '#f59e0b', icon: CheckCircle2 },
  execution: { label: 'Eksekusi', color: '#10b981', icon: Lightbulb },
};

const ENTRY_TYPE_CONFIG: Record<EntryType, { color: string; icon: typeof MessageSquare }> = {
  message: { color: '#94a3b8', icon: MessageSquare },
  decision: { color: '#10b981', icon: CheckCircle2 },
  concern: { color: '#f59e0b', icon: AlertTriangle },
  result: { color: '#06b6d4', icon: FileText },
};

const PHASE_ORDER: Phase[] = ['client_discussion', 'team_briefing', 'todo_review', 'execution'];

export function SessionTranscriptPanel() {
  const { clientMessages, workersMessages, contract, activeSessionId, sessions } = useKantorkuStore();
  const [workerFilter, setWorkerFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<Phase | 'all'>('all');
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);
  const [showSummary, setShowSummary] = useState(false);

  // Build transcript entries from store data
  const transcriptEntries: TranscriptEntry[] = useMemo(() => {
    const entries: TranscriptEntry[] = [];

    // Phase: client_discussion
    clientMessages.forEach((msg, i) => {
      entries.push({
        id: `tc_${i}`,
        phase: 'client_discussion',
        type: 'message',
        worker_id: msg.role === 'user' ? 'client' : 'conductor',
        content: msg.content,
        timestamp: msg.timestamp,
      });
    });

    // Phase: team_briefing
    workersMessages.forEach((msg, i) => {
      if (msg.message_type === 'agreement' || msg.message_type === 'disagreement') {
        entries.push({
          id: `tb_${i}`,
          phase: 'team_briefing',
          type: 'decision',
          worker_id: msg.from_id,
          content: msg.content,
          timestamp: msg.timestamp,
        });
      } else if (msg.message_type === 'concern') {
        entries.push({
          id: `tb_${i}`,
          phase: 'team_briefing',
          type: 'concern',
          worker_id: msg.from_id,
          content: msg.content,
          timestamp: msg.timestamp,
        });
      } else {
        entries.push({
          id: `tb_${i}`,
          phase: 'team_briefing',
          type: 'message',
          worker_id: msg.from_id,
          content: msg.content,
          timestamp: msg.timestamp,
        });
      }
    });

    // Phase: todo_review
    if (contract) {
      contract.todos.forEach((todo, i) => {
        entries.push({
          id: `tr_${i}`,
          phase: 'todo_review',
          type: 'result',
          worker_id: todo.assigned_to || 'unassigned',
          content: `[${todo.status.toUpperCase()}] ${todo.description}`,
          timestamp: todo.completed_at || todo.started_at || contract.created_at,
        });
      });
    }

    // Phase: execution (results from done/failed todos)
    if (contract) {
      contract.todos
        .filter((t) => t.status === 'done' || t.status === 'failed')
        .forEach((todo, i) => {
          entries.push({
            id: `te_${i}`,
            phase: 'execution',
            type: todo.status === 'done' ? 'result' : 'concern',
            worker_id: todo.assigned_to || 'unassigned',
            content: `${todo.status === 'done' ? '✅' : '❌'} ${todo.description}${todo.result ? ` — ${todo.result}` : ''}${todo.error ? ` (Error: ${todo.error})` : ''}`,
            timestamp: todo.completed_at || new Date().toISOString(),
          });
        });
    }

    return entries.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [clientMessages, workersMessages, contract]);

  // Filter entries
  const filteredEntries = useMemo(() => {
    return transcriptEntries.filter((e) => {
      if (phaseFilter !== 'all' && e.phase !== phaseFilter) return false;
      if (workerFilter !== 'all' && e.worker_id !== workerFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!e.content.toLowerCase().includes(q) && !e.worker_id.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [transcriptEntries, phaseFilter, workerFilter, searchQuery]);

  // Group entries by phase
  const groupedEntries = useMemo(() => {
    const groups: Record<Phase, TranscriptEntry[]> = {
      client_discussion: [],
      team_briefing: [],
      todo_review: [],
      execution: [],
    };
    filteredEntries.forEach((e) => groups[e.phase].push(e));
    return groups;
  }, [filteredEntries]);

  // Summary
  const summary = useMemo(() => {
    const byPhase = Object.fromEntries(
      PHASE_ORDER.map((p) => [p, transcriptEntries.filter((e) => e.phase === p).length])
    );
    const byType = Object.fromEntries(
      (['message', 'decision', 'concern', 'result'] as EntryType[]).map((t) => [
        t,
        transcriptEntries.filter((e) => e.type === t).length,
      ])
    );
    const uniqueWorkers = new Set(transcriptEntries.map((e) => e.worker_id)).size;
    return { byPhase, byType, totalEntries: transcriptEntries.length, uniqueWorkers };
  }, [transcriptEntries]);

  // Unique workers for filter
  const uniqueWorkerIds = useMemo(() => {
    const ids = new Set(transcriptEntries.map((e) => e.worker_id));
    return Array.from(ids).sort();
  }, [transcriptEntries]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <ScrollText className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Transkrip Sesi</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-500 font-mono">
              {transcriptEntries.length}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSummary(!showSummary)}
            className="h-5 px-2 text-[9px] text-cyan-400 hover:text-cyan-300"
          >
            {showSummary ? 'Tutup' : 'Ringkasan'}
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="h-2.5 w-2.5 absolute left-1.5 top-1/2 -translate-y-1/2 text-slate-600" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cari dalam transkrip..."
            className="h-5 text-[10px] pl-5 bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
          />
        </div>

        {/* Phase filter */}
        <div className="flex items-center gap-1 flex-wrap">
          <Filter className="h-2.5 w-2.5 text-slate-600" />
          <Badge
            variant="outline"
            className={`text-[8px] px-1 py-0 h-3 cursor-pointer font-mono ${
              phaseFilter === 'all' ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10' : 'border-slate-700/30 text-slate-500'
            }`}
            onClick={() => setPhaseFilter('all')}
          >
            ALL
          </Badge>
          {PHASE_ORDER.map((p) => (
            <Badge
              key={p}
              variant="outline"
              className={`text-[8px] px-1 py-0 h-3 cursor-pointer font-mono ${
                phaseFilter === p ? '' : 'border-slate-700/30 text-slate-500'
              }`}
              style={phaseFilter === p ? {
                borderColor: `${PHASE_CONFIG[p].color}40`,
                color: PHASE_CONFIG[p].color,
                backgroundColor: `${PHASE_CONFIG[p].color}10`,
              } : undefined}
              onClick={() => setPhaseFilter(p)}
            >
              {PHASE_CONFIG[p].label}
            </Badge>
          ))}
        </div>

        {/* Worker filter */}
        {uniqueWorkerIds.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-[8px] text-slate-600 font-mono">Worker:</span>
            <Badge
              variant="outline"
              className={`text-[9px] px-1 py-0 h-3 cursor-pointer font-mono ${
                workerFilter === 'all' ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10' : 'border-slate-700/30 text-slate-500'
              }`}
              onClick={() => setWorkerFilter('all')}
            >
              ALL
            </Badge>
            {uniqueWorkerIds.map((id) => {
              const worker = WORKERS.find((w) => w.id === id);
              return (
                <Badge
                  key={id}
                  variant="outline"
                  className={`text-[9px] px-1 py-0 h-3 cursor-pointer font-mono ${
                    workerFilter === id ? '' : 'border-slate-700/30 text-slate-500'
                  }`}
                  style={workerFilter === id ? {
                    borderColor: `${worker?.color || '#94a3b8'}40`,
                    color: worker?.color || '#94a3b8',
                  } : undefined}
                  onClick={() => setWorkerFilter(id)}
                >
                  {id}
                </Badge>
              );
            })}
          </div>
        )}
      </div>

      {/* Summary card */}
      {showSummary && (
        <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-800/60">
          <div className="grid grid-cols-2 gap-1.5">
            <div className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
              <p className="text-[8px] text-slate-500 uppercase">Total Entri</p>
              <p className="text-[11px] font-bold text-cyan-300 font-mono">{summary.totalEntries}</p>
            </div>
            <div className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
              <p className="text-[8px] text-slate-500 uppercase">Worker Aktif</p>
              <p className="text-[11px] font-bold text-green-300 font-mono">{summary.uniqueWorkers}</p>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-1 mt-1.5">
            {PHASE_ORDER.map((p) => (
              <div key={p} className="p-1 rounded text-center" style={{ backgroundColor: `${PHASE_CONFIG[p].color}10`, border: `1px solid ${PHASE_CONFIG[p].color}20` }}>
                <p className="text-[8px] font-mono" style={{ color: PHASE_CONFIG[p].color }}>{summary.byPhase[p]}</p>
                <p className="text-[9px] text-slate-500">{PHASE_CONFIG[p].label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transcript entries by phase */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
        {filteredEntries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <ScrollText className="h-8 w-8 text-slate-600/50 mb-2" />
            <p className="text-[10px] text-center text-slate-600">
              Belum ada transkrip.<br />
              Mulai percakapan untuk mengisi transkrip sesi.
            </p>
          </div>
        ) : (
          PHASE_ORDER.map((phase) => {
            const phaseEntries = groupedEntries[phase];
            if (phaseEntries.length === 0) return null;
            const config = PHASE_CONFIG[phase];

            return (
              <div key={phase}>
                {/* Phase header */}
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className="h-0.5 flex-1 rounded-full" style={{ backgroundColor: `${config.color}30` }} />
                  <span className="text-[9px] font-mono font-semibold" style={{ color: config.color }}>
                    {config.label}
                  </span>
                  <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-2.5 font-mono" style={{ borderColor: `${config.color}30`, color: config.color }}>
                    {phaseEntries.length}
                  </Badge>
                  <div className="h-0.5 flex-1 rounded-full" style={{ backgroundColor: `${config.color}30` }} />
                </div>

                {/* Phase entries */}
                <div className="space-y-1 ml-2 border-l-2 pl-2" style={{ borderColor: `${config.color}20` }}>
                  {phaseEntries.map((entry) => {
                    const entryConfig = ENTRY_TYPE_CONFIG[entry.type];
                    const EntryIcon = entryConfig.icon;
                    const isExpanded = expandedEntry === entry.id;
                    const worker = WORKERS.find((w) => w.id === entry.worker_id);

                    return (
                      <div
                        key={entry.id}
                        className="p-1.5 rounded bg-slate-800/40 border border-slate-700/15 cursor-pointer hover:bg-slate-800/60 transition-colors"
                        onClick={() => setExpandedEntry(isExpanded ? null : entry.id)}
                      >
                        <div className="flex items-center gap-1.5">
                          <EntryIcon className="h-2.5 w-2.5 flex-shrink-0" style={{ color: entryConfig.color }} />
                          <span className="text-[10px] font-mono" style={{ color: worker?.color || '#94a3b8' }}>
                            {worker?.emoji || '👤'} {entry.worker_id}
                          </span>
                          <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-2.5 border-slate-700/50 text-slate-500">
                            {entry.type}
                          </Badge>
                          <span className="text-[8px] text-slate-600 font-mono ml-auto flex-shrink-0">
                            {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 mt-0.5 leading-tight line-clamp-2">
                          {entry.content}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
