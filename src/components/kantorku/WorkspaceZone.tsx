'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { WorkerCard } from './WorkerCard';
import { WorkersChatPanel } from './ChatPanel';
import { OfficeEventLog } from './OfficeEventLog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SQUADS, MEMORY_RINGS } from '@/lib/kantorku/workers-data';
import { Presentation, Users, Activity, MessageCircle, Brain, Database } from 'lucide-react';

export function WorkspaceZone() {
  const { workers, workersMessages, officeEvents, briefingResult, discussionRounds, contract, contractState } =
    useKantorkuStore();

  const busyWorkers = workers.filter((w) => w.status === 'busy').length;
  const idleWorkers = workers.filter((w) => w.status === 'idle').length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-slate-700/50 bg-slate-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Presentation className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white">RUANG KERJA</h2>
          </div>
          <div className="flex items-center gap-2 text-[10px]">
            <span className="text-cyan-400 font-mono">{busyWorkers} busy</span>
            <span className="text-slate-600">|</span>
            <span className="text-green-400 font-mono">{idleWorkers} idle</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="workers" className="h-full flex flex-col">
          <TabsList className="flex-shrink-0 mx-3 mt-2 bg-slate-800/60 border border-slate-700/30 h-7 p-0.5">
            <TabsTrigger value="workers" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Users className="h-3 w-3 mr-1" />
              Workers
            </TabsTrigger>
            <TabsTrigger value="briefing" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Presentation className="h-3 w-3 mr-1" />
              Briefing
            </TabsTrigger>
            <TabsTrigger value="channel" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <MessageCircle className="h-3 w-3 mr-1" />
              Channel
            </TabsTrigger>
            <TabsTrigger value="events" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Activity className="h-3 w-3 mr-1" />
              Events
            </TabsTrigger>
          </TabsList>

          {/* Workers Grid */}
          <TabsContent value="workers" className="flex-1 overflow-hidden mt-0">
            <div className="h-full overflow-y-auto custom-scrollbar px-3 py-2">
              {/* Worker Grid by Squad */}
              {SQUADS.map((squad) => {
                const squadWorkers = workers.filter(
                  (w) => w.squad === squad.id
                );
                if (squadWorkers.length === 0) return null;
                return (
                  <div key={squad.id} className="mb-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <div
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: squad.color }}
                      />
                      <span
                        className="text-[10px] font-mono font-semibold uppercase"
                        style={{ color: squad.color }}
                      >
                        {squad.label}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5">
                      {squadWorkers.map((worker) => (
                        <WorkerCard key={worker.id} worker={worker} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </TabsContent>

          {/* Briefing Room */}
          <TabsContent value="briefing" className="flex-1 overflow-hidden mt-0">
            <div className="h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
              {/* Briefing Status */}
              <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/30">
                <div className="flex items-center gap-2 mb-2">
                  <Presentation className="h-4 w-4 text-violet-400" />
                  <span className="text-xs font-semibold text-violet-300">
                    Briefing Room
                  </span>
                  {briefingResult && (
                    <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-green-500/30 text-green-300">
                      {briefingResult.consensus_reached ? 'Consensus' : 'No Consensus'}
                    </Badge>
                  )}
                </div>
                {briefingResult ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      <div className="text-center p-2 rounded bg-slate-900/60">
                        <p className="text-lg font-bold text-cyan-300">{briefingResult.rounds_completed}</p>
                        <p className="text-[9px] text-slate-500">Rounds</p>
                      </div>
                      <div className="text-center p-2 rounded bg-slate-900/60">
                        <p className="text-lg font-bold text-green-300">{briefingResult.decisions.length}</p>
                        <p className="text-[9px] text-slate-500">Decisions</p>
                      </div>
                      <div className="text-center p-2 rounded bg-slate-900/60">
                        <p className="text-lg font-bold text-amber-300">{briefingResult.concerns.length}</p>
                        <p className="text-[9px] text-slate-500">Concerns</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-[10px] text-slate-500">
                    Briefing room is empty. Accept a contract to start a team discussion.
                  </p>
                )}
              </div>

              {/* Discussion Rounds */}
              {discussionRounds.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] font-mono text-slate-400 uppercase">
                    Discussion Rounds
                  </span>
                  {discussionRounds.map((round) => (
                    <div
                      key={round.round_number}
                      className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/20"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono text-cyan-400">
                          Round {round.round_number}
                        </span>
                        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-400">
                          {round.messages.length} msgs
                        </Badge>
                      </div>
                      <p className="text-[10px] text-slate-400">{round.summary}</p>
                      {round.decisions.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {round.decisions.map((d, i) => (
                            <Badge key={i} variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-green-500/30 text-green-300">
                              {d}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 3-Ring Memory Visualization */}
              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <Brain className="h-3.5 w-3.5 text-pink-400" />
                  <span className="text-[10px] font-mono text-slate-400 uppercase">
                    Memory Rings
                  </span>
                </div>
                {MEMORY_RINGS.map((ring) => (
                  <div
                    key={ring.ring}
                    className="p-2 rounded-lg bg-slate-800/40 border border-slate-700/20"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold border-2"
                        style={{
                          borderColor: ring.color,
                          color: ring.color,
                          backgroundColor: `${ring.color}15`,
                        }}
                      >
                        R{ring.ring}
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold" style={{ color: ring.color }}>
                          {ring.label}
                        </p>
                        <p className="text-[9px] text-slate-500">{ring.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Context Pool */}
              <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/20">
                <div className="flex items-center gap-1.5 mb-1">
                  <Database className="h-3.5 w-3.5 text-teal-400" />
                  <span className="text-[10px] font-mono text-slate-400 uppercase">
                    Context Pool
                  </span>
                </div>
                <p className="text-[9px] text-slate-500">
                  Prefetched context is stored in Ring 1 during briefing and made available to workers during execution.
                </p>
              </div>
            </div>
          </TabsContent>

          {/* Group Channel */}
          <TabsContent value="channel" className="flex-1 overflow-hidden mt-0">
            <WorkersChatPanel messages={workersMessages} />
          </TabsContent>

          {/* Event Log */}
          <TabsContent value="events" className="flex-1 overflow-hidden mt-0">
            <OfficeEventLog events={officeEvents} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
