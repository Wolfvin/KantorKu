'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { WorkerCard } from './WorkerCard';
import { BriefingRoomPanel } from './BriefingRoomPanel';
import { GroupChannelPanel } from './GroupChannelPanel';
import { OfficeEventLog } from './OfficeEventLog';
import { MemoryExplorerPanel } from './MemoryExplorerPanel';
import { DAGVisualizationPanel } from './DAGVisualizationPanel';
import { WorkerRegistryPanel } from './WorkerRegistryPanel';
import { DebriefPanel } from './DebriefPanel';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SQUADS } from '@/lib/kantorku/workers-data';
import {
  Presentation, Users, Activity, MessageCircle,
  Brain, GitBranch, BookOpen, ClipboardCheck,
} from 'lucide-react';

export function WorkspaceZone() {
  const { workers, officeEvents } = useKantorkuStore();

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
          <TabsList className="flex-shrink-0 mx-3 mt-2 bg-slate-800/60 border border-slate-700/30 h-7 p-0.5 flex-wrap gap-0">
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
            <TabsTrigger value="memory" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Brain className="h-3 w-3 mr-1" />
              Memory
            </TabsTrigger>
            <TabsTrigger value="dag" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <GitBranch className="h-3 w-3 mr-1" />
              DAG
            </TabsTrigger>
            <TabsTrigger value="registry" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <BookOpen className="h-3 w-3 mr-1" />
              Registry
            </TabsTrigger>
            <TabsTrigger value="debrief" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <ClipboardCheck className="h-3 w-3 mr-1" />
              Debrief
            </TabsTrigger>
          </TabsList>

          {/* Workers Grid */}
          <TabsContent value="workers" className="flex-1 overflow-hidden mt-0">
            <div className="h-full overflow-y-auto custom-scrollbar px-3 py-2">
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
            <BriefingRoomPanel />
          </TabsContent>

          {/* Group Channel */}
          <TabsContent value="channel" className="flex-1 overflow-hidden mt-0">
            <GroupChannelPanel />
          </TabsContent>

          {/* Event Log */}
          <TabsContent value="events" className="flex-1 overflow-hidden mt-0">
            <OfficeEventLog events={officeEvents} />
          </TabsContent>

          {/* Memory Explorer */}
          <TabsContent value="memory" className="flex-1 overflow-hidden mt-0">
            <MemoryExplorerPanel />
          </TabsContent>

          {/* DAG Visualization */}
          <TabsContent value="dag" className="flex-1 overflow-hidden mt-0">
            <DAGVisualizationPanel />
          </TabsContent>

          {/* Worker Registry */}
          <TabsContent value="registry" className="flex-1 overflow-hidden mt-0">
            <WorkerRegistryPanel />
          </TabsContent>

          {/* Debrief */}
          <TabsContent value="debrief" className="flex-1 overflow-hidden mt-0">
            <DebriefPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
