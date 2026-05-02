'use client';

import { useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import { LobbyZone } from './LobbyZone';
import { WorkspaceZone } from './WorkspaceZone';
import { DashboardZone } from './DashboardZone';
import { SettingsDialog, SettingsButton } from './SettingsDialog';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import {
  MessageSquare,
  Briefcase,
  BarChart3,
  Wifi,
  WifiOff,
} from 'lucide-react';

export function KantorkuApp() {
  const { isBackendConnected, contractState } = useKantorkuStore();
  const [mobileTab, setMobileTab] = useState<'lobby' | 'workspace' | 'dashboard'>('lobby');

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0a0e1a] text-white overflow-hidden">
      {/* Top Bar */}
      <header className="flex-shrink-0 h-10 border-b border-cyan-900/30 bg-[#0a0e1a]/90 backdrop-blur-sm flex items-center justify-between px-3 z-50">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div className="h-5 w-5 rounded bg-gradient-to-br from-cyan-500 to-teal-500 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">K</span>
            </div>
            <h1 className="text-sm font-bold bg-gradient-to-r from-cyan-400 to-teal-300 bg-clip-text text-transparent">
              kantorku
            </h1>
          </div>
          <Badge
            variant="outline"
            className="text-[8px] px-1 py-0 h-4 font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/10 hidden sm:inline-flex"
          >
            v0.4.0
          </Badge>
          <Badge
            variant="outline"
            className={`text-[8px] px-1 py-0 h-4 font-mono ${
              contractState === 'working'
                ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                : contractState === 'done'
                ? 'border-green-500/40 text-green-300 bg-green-500/10'
                : 'border-slate-600/50 text-slate-400 bg-slate-800/30'
            }`}
          >
            {contractState === 'idle' ? 'READY' : contractState.toUpperCase().replace('_', ' ')}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-[9px]">
            {isBackendConnected ? (
              <>
                <Wifi className="h-3 w-3 text-green-400" />
                <span className="text-green-400 font-mono hidden sm:inline">CONNECTED</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-amber-400" />
                <span className="text-amber-400 font-mono hidden sm:inline">STANDALONE</span>
              </>
            )}
          </div>
          <SettingsButton />
        </div>
      </header>

      {/* Mobile Tab Bar */}
      <div className="flex-shrink-0 sm:hidden border-b border-cyan-900/30 bg-[#0a0e1a]/90">
        <div className="flex">
          {[
            { id: 'lobby' as const, icon: MessageSquare, label: 'Lobby' },
            { id: 'workspace' as const, icon: Briefcase, label: 'Workspace' },
            { id: 'dashboard' as const, icon: BarChart3, label: 'Dashboard' },
          ].map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              onClick={() => setMobileTab(id)}
              className={`flex-1 py-2 flex flex-col items-center gap-0.5 transition-colors ${
                mobileTab === id
                  ? 'text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-slate-500'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span className="text-[9px] font-mono">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {/* Desktop 3-Panel Layout */}
        <div className="hidden sm:block h-full">
          <ResizablePanelGroup direction="horizontal" className="h-full">
            {/* Lobby Zone */}
            <ResizablePanel defaultSize={30} minSize={20} maxSize={45}>
              <div className="h-full border-r border-cyan-900/20">
                <LobbyZone />
              </div>
            </ResizablePanel>

            <ResizableHandle className="bg-cyan-900/20 hover:bg-cyan-700/30 transition-colors w-0.5" />

            {/* Workspace Zone */}
            <ResizablePanel defaultSize={45} minSize={30}>
              <div className="h-full border-r border-cyan-900/20">
                <WorkspaceZone />
              </div>
            </ResizablePanel>

            <ResizableHandle className="bg-cyan-900/20 hover:bg-cyan-700/30 transition-colors w-0.5" />

            {/* Dashboard Zone */}
            <ResizablePanel defaultSize={25} minSize={18} maxSize={40}>
              <div className="h-full">
                <DashboardZone />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>

        {/* Mobile Single-Panel Layout */}
        <div className="sm:hidden h-full">
          {mobileTab === 'lobby' && <LobbyZone />}
          {mobileTab === 'workspace' && <WorkspaceZone />}
          {mobileTab === 'dashboard' && <DashboardZone />}
        </div>
      </div>

      {/* Settings Dialog */}
      <SettingsDialog />
    </div>
  );
}
