'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { WORKERS, MESSAGE_TYPE_COLORS } from '@/lib/kantorku/workers-data';
import { Presentation, Users, CheckCircle2, XCircle, ArrowRight, Clock, Target, AlertTriangle } from 'lucide-react';

export function BriefingRoomPanel() {
  const { briefingResult, discussionRounds, workersMessages, contract, workers } = useKantorkuStore();

  const getWorkerEmoji = (id: string) => {
    if (id === 'conductor' || id === 'manager') return '👔';
    const w = workers.find((w) => w.id === id);
    return w?.emoji || '🤖';
  };

  const getWorkerColor = (id: string) => {
    if (id === 'conductor' || id === 'manager') return '#06b6d4';
    const w = workers.find((w) => w.id === id);
    return w?.color || '#94a3b8';
  };

  const totalMessages = discussionRounds.reduce((acc, r) => acc + r.messages.length, 0);
  const currentRound = discussionRounds.length > 0 ? discussionRounds[discussionRounds.length - 1].round_number : 0;
  const consensusReached = briefingResult?.consensus_reached ?? false;

  return (
    <div className="flex flex-col h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
      {/* Briefing Status Card */}
      <Card className="bg-slate-800/60 border-slate-700/30 backdrop-blur-sm">
        <CardHeader className="p-3 pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Presentation className="h-4 w-4 text-violet-400" />
              <CardTitle className="text-xs text-violet-300">Briefing Room</CardTitle>
            </div>
            {briefingResult && (
              <div className="flex items-center gap-1">
                {consensusReached ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-red-400" />
                )}
                <Badge
                  variant="outline"
                  className="text-[9px] px-1.5 py-0 h-4 font-mono"
                  style={{
                    borderColor: consensusReached ? '#22c55e40' : '#ef444440',
                    color: consensusReached ? '#4ade80' : '#f87171',
                    backgroundColor: consensusReached ? '#22c55e10' : '#ef444410',
                  }}
                >
                  {consensusReached ? 'CONSENSUS' : 'NO CONSENSUS'}
                </Badge>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-3 pt-0">
          {briefingResult ? (
            <div className="space-y-2.5">
              {/* Stats Grid */}
              <div className="grid grid-cols-4 gap-1.5">
                <div className="text-center p-2 rounded-md bg-slate-900/60 border border-slate-700/20">
                  <p className="text-lg font-bold text-cyan-300 font-mono">{briefingResult.rounds_completed}</p>
                  <p className="text-[9px] text-slate-500 uppercase">Rounds</p>
                </div>
                <div className="text-center p-2 rounded-md bg-slate-900/60 border border-slate-700/20">
                  <p className="text-lg font-bold text-green-300 font-mono">{briefingResult.decisions.length}</p>
                  <p className="text-[9px] text-slate-500 uppercase">Decisions</p>
                </div>
                <div className="text-center p-2 rounded-md bg-slate-900/60 border border-slate-700/20">
                  <p className="text-lg font-bold text-amber-300 font-mono">{briefingResult.concerns.length}</p>
                  <p className="text-[9px] text-slate-500 uppercase">Concerns</p>
                </div>
                <div className="text-center p-2 rounded-md bg-slate-900/60 border border-slate-700/20">
                  <p className="text-lg font-bold text-violet-300 font-mono">{totalMessages}</p>
                  <p className="text-[9px] text-slate-500 uppercase">Messages</p>
                </div>
              </div>

              {/* Round Progress */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-400 font-mono">Round Progress</span>
                  <span className="text-[10px] text-cyan-400 font-mono">{currentRound}/{briefingResult.rounds_completed}</span>
                </div>
                <Progress
                  value={(currentRound / Math.max(briefingResult.rounds_completed, 1)) * 100}
                  className="h-1.5 bg-slate-900/60"
                />
              </div>

              {/* Decisions */}
              {briefingResult.decisions.length > 0 && (
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <Target className="h-3 w-3 text-green-400" />
                    <span className="text-[10px] font-mono text-green-400 uppercase">Decisions</span>
                  </div>
                  {briefingResult.decisions.map((d, i) => (
                    <div key={i} className="flex items-start gap-1.5 pl-1">
                      <ArrowRight className="h-2.5 w-2.5 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-[10px] text-slate-300">{String(d)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Concerns */}
              {briefingResult.concerns.length > 0 && (
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3 text-amber-400" />
                    <span className="text-[10px] font-mono text-amber-400 uppercase">Concerns</span>
                  </div>
                  {briefingResult.concerns.map((c, i) => (
                    <div key={i} className="flex items-start gap-1.5 pl-1">
                      <XCircle className="h-2.5 w-2.5 text-amber-500 mt-0.5 flex-shrink-0" />
                      <span className="text-[10px] text-slate-400">
                        {typeof c === 'string' ? c : JSON.stringify(c)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-6 text-slate-500">
              <Users className="h-8 w-8 text-slate-600/50 mb-2" />
              <p className="text-[10px] text-center">
                Briefing room is empty.<br />
                <span className="text-slate-600">Accept a contract to start a team discussion.</span>
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Discussion Rounds */}
      {discussionRounds.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3 w-3 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Discussion Rounds</span>
          </div>
          {discussionRounds.map((round) => (
            <Card key={round.round_number} className="bg-slate-800/40 border-slate-700/20 backdrop-blur-sm">
              <CardContent className="p-2.5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <div className="h-5 w-5 rounded-full bg-cyan-500/20 flex items-center justify-center">
                      <span className="text-[9px] font-bold text-cyan-400 font-mono">{round.round_number}</span>
                    </div>
                    <span className="text-[10px] font-mono text-cyan-400">Round {round.round_number}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-400">
                      {round.messages.length} msgs
                    </Badge>
                    {round.consensus_reached ? (
                      <CheckCircle2 className="h-3 w-3 text-green-400" />
                    ) : (
                      <XCircle className="h-3 w-3 text-red-400/50" />
                    )}
                  </div>
                </div>

                {/* Messages in round */}
                <div className="space-y-1.5 mb-2 max-h-48 overflow-y-auto custom-scrollbar">
                  {round.messages.map((msg, idx) => {
                    const msgColor = MESSAGE_TYPE_COLORS[msg.message_type] || '#94a3b8';
                    return (
                      <div key={idx} className="flex items-start gap-1.5">
                        <span className="text-[10px] flex-shrink-0">{getWorkerEmoji(msg.from_id)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1">
                            <span className="text-[9px] font-mono font-semibold" style={{ color: getWorkerColor(msg.from_id) }}>
                              {msg.from_id}
                            </span>
                            <Badge
                              variant="outline"
                              className="text-[9px] px-0.5 py-0 h-3"
                              style={{
                                borderColor: `${msgColor}40`,
                                color: msgColor,
                                backgroundColor: `${msgColor}10`,
                              }}
                            >
                              {msg.message_type}
                            </Badge>
                          </div>
                          <p className="text-[9px] text-slate-400 leading-tight break-words line-clamp-2">
                            {msg.content}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Summary */}
                {round.summary && (
                  <p className="text-[10px] text-slate-400 bg-slate-900/40 rounded p-1.5 border border-slate-700/10">
                    {round.summary}
                  </p>
                )}

                {/* Decisions */}
                {round.decisions.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {round.decisions.map((d, i) => (
                      <Badge key={i} variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-green-500/30 text-green-300">
                        {d}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Volunteer Assignments */}
      {briefingResult?.volunteer_assignments && Object.keys(briefingResult.volunteer_assignments).length > 0 && (
        <Card className="bg-slate-800/40 border-slate-700/20 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <div className="flex items-center gap-1.5">
              <Users className="h-3 w-3 text-teal-400" />
              <CardTitle className="text-[10px] text-teal-300 font-mono uppercase">Volunteer Assignments</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-2.5 pt-0">
            <div className="space-y-1">
              {Object.entries(briefingResult.volunteer_assignments).map(([workerId, task]) => (
                <div key={workerId} className="flex items-center gap-2 text-[10px]">
                  <span>{getWorkerEmoji(workerId)}</span>
                  <span className="font-mono text-cyan-300">{workerId}</span>
                  <ArrowRight className="h-2.5 w-2.5 text-slate-600" />
                  <span className="text-slate-400 flex-1 truncate">{String(task)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Contract Context */}
      {contract && (
        <Card className="bg-slate-800/40 border-slate-700/20 backdrop-blur-sm">
          <CardHeader className="p-2.5 pb-1">
            <div className="flex items-center gap-1.5">
              <Target className="h-3 w-3 text-pink-400" />
              <CardTitle className="text-[10px] text-pink-300 font-mono uppercase">Contract Context</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-2.5 pt-0">
            <p className="text-xs text-white font-medium">{contract.title}</p>
            <p className="text-[10px] text-slate-400 mt-1 line-clamp-3">{contract.description}</p>
            <div className="flex items-center gap-1.5 mt-2">
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-cyan-500/30 text-cyan-300">
                {contract.todos.length} todos
              </Badge>
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-violet-500/30 text-violet-300">
                {contract.state}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
