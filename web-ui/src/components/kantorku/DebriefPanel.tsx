'use client';

import React from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DebriefResult } from '@/lib/kantorku/types';
import {
  ClipboardCheck, ThumbsUp, AlertTriangle, Lightbulb,
  Clock, DollarSign, User, FileText, Calendar,
} from 'lucide-react';

export const DebriefPanel = React.memo(function DebriefPanel() {
  const { debriefResult, contract, workers } = useKantorkuStore();

  const getWorkerEmoji = (id: string) => {
    const w = workers.find((w) => w.id === id);
    return w?.emoji || '🤖';
  };

  const getWorkerColor = (id: string) => {
    const w = workers.find((w) => w.id === id);
    return w?.color || '#94a3b8';
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  if (!debriefResult) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
          <div className="flex items-center gap-1.5">
            <ClipboardCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Debrief</span>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
          <FileText className="h-8 w-8 text-slate-600/50 mb-2" />
          <p className="text-[10px] text-center text-slate-600">
            No debrief available yet.<br />
            Complete a contract to see the debrief report.
          </p>
        </div>
      </div>
    );
  }

  const debrief = debriefResult as DebriefResult;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <ClipboardCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Post-Task Debrief</span>
          </div>
          {debrief.timestamp && (
            <div className="flex items-center gap-1">
              <Calendar className="h-2.5 w-2.5 text-slate-600" />
              <span className="text-[8px] text-slate-600 font-mono">
                {new Date(debrief.timestamp).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2.5">
        {/* Overview Stats */}
        <Card className="bg-slate-800/60 border-slate-700/30 backdrop-blur-sm">
          <CardContent className="p-2.5">
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center gap-2 p-2 rounded-md bg-slate-900/60 border border-slate-700/20">
                <Clock className="h-4 w-4 text-cyan-400" />
                <div>
                  <p className="text-sm font-bold text-cyan-300 font-mono">
                    {formatDuration(debrief.total_duration_ms)}
                  </p>
                  <p className="text-[8px] text-slate-500 uppercase">Duration</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-md bg-slate-900/60 border border-slate-700/20">
                <DollarSign className="h-4 w-4 text-green-400" />
                <div>
                  <p className="text-sm font-bold text-green-300 font-mono">
                    ${debrief.total_cost.toFixed(4)}
                  </p>
                  <p className="text-[8px] text-slate-500 uppercase">Cost</p>
                </div>
              </div>
            </div>
            {debrief.contract_id && (
              <div className="mt-1.5 flex items-center gap-1">
                <FileText className="h-2.5 w-2.5 text-slate-600" />
                <span className="text-[8px] text-slate-500 font-mono">{debrief.contract_id}</span>
                {debrief.session_id && (
                  <span className="text-[8px] text-slate-600 font-mono">· {debrief.session_id.substring(0, 12)}...</span>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* What Went Well */}
        <Card className="bg-slate-800/40 border-green-500/20 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <div className="flex items-center gap-1.5">
              <ThumbsUp className="h-3 w-3 text-green-400" />
              <CardTitle className="text-[10px] text-green-300 font-mono uppercase">What Went Well</CardTitle>
              <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-3 border-green-500/30 text-green-300">
                {debrief.what_went_well.length}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-2.5 pt-0">
            {debrief.what_went_well.length === 0 ? (
              <p className="text-[9px] text-slate-600">No items recorded</p>
            ) : (
              <div className="space-y-1">
                {debrief.what_went_well.map((item, i) => (
                  <div key={i} className="flex items-start gap-1.5">
                    <div className="h-1.5 w-1.5 rounded-full bg-green-400 mt-1 flex-shrink-0" />
                    <span className="text-[10px] text-slate-300">{item}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* What Could Improve */}
        <Card className="bg-slate-800/40 border-amber-500/20 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="h-3 w-3 text-amber-400" />
              <CardTitle className="text-[10px] text-amber-300 font-mono uppercase">What Could Improve</CardTitle>
              <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-3 border-amber-500/30 text-amber-300">
                {debrief.what_could_improve.length}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-2.5 pt-0">
            {debrief.what_could_improve.length === 0 ? (
              <p className="text-[9px] text-slate-600">No items recorded</p>
            ) : (
              <div className="space-y-1">
                {debrief.what_could_improve.map((item, i) => (
                  <div key={i} className="flex items-start gap-1.5">
                    <div className="h-1.5 w-1.5 rounded-full bg-amber-400 mt-1 flex-shrink-0" />
                    <span className="text-[10px] text-slate-300">{item}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Lessons Learned */}
        <Card className="bg-slate-800/40 border-cyan-500/20 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <div className="flex items-center gap-1.5">
              <Lightbulb className="h-3 w-3 text-cyan-400" />
              <CardTitle className="text-[10px] text-cyan-300 font-mono uppercase">Lessons Learned</CardTitle>
              <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-3 border-cyan-500/30 text-cyan-300">
                {debrief.lessons_learned.length}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-2.5 pt-0">
            {debrief.lessons_learned.length === 0 ? (
              <p className="text-[9px] text-slate-600">No lessons recorded</p>
            ) : (
              <div className="space-y-1">
                {debrief.lessons_learned.map((item, i) => (
                  <div key={i} className="flex items-start gap-1.5">
                    <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 mt-1 flex-shrink-0" />
                    <span className="text-[10px] text-slate-300">{item}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Worker Feedback */}
        {Object.keys(debrief.worker_feedback).length > 0 && (
          <Card className="bg-slate-800/40 border-violet-500/20 backdrop-blur-sm">
            <CardHeader className="p-2.5 pb-1">
              <div className="flex items-center gap-1.5">
                <User className="h-3 w-3 text-violet-400" />
                <CardTitle className="text-[10px] text-violet-300 font-mono uppercase">Worker Feedback</CardTitle>
                <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-3 border-violet-500/30 text-violet-300">
                  {Object.keys(debrief.worker_feedback).length}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-2.5 pt-0 space-y-1.5">
              {Object.entries(debrief.worker_feedback).map(([workerId, feedback]) => (
                <div key={workerId} className="p-2 rounded-md bg-slate-900/40 border border-slate-700/15">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-sm">{getWorkerEmoji(workerId)}</span>
                    <span className="text-[10px] font-mono font-semibold" style={{ color: getWorkerColor(workerId) }}>
                      {workerId}
                    </span>
                  </div>
                  <p className="text-[9px] text-slate-400 leading-relaxed">{feedback}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Contract Reference */}
        {contract && (
          <Card className="bg-slate-800/30 border-slate-700/15 backdrop-blur-sm">
            <CardContent className="p-2.5">
              <div className="flex items-center gap-1.5 mb-1">
                <FileText className="h-3 w-3 text-slate-500" />
                <span className="text-[9px] font-mono text-slate-500 uppercase">Contract Reference</span>
              </div>
              <p className="text-[10px] text-white font-medium">{contract.title}</p>
              <p className="text-[9px] text-slate-500 mt-0.5 line-clamp-2">{contract.description}</p>
              <div className="flex items-center gap-1.5 mt-1.5">
                <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-400">
                  {contract.state}
                </Badge>
                <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-400">
                  {contract.todos.filter((t) => t.status === 'done').length}/{contract.todos.length} done
                </Badge>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
});
