'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LobbyZone } from './LobbyZone';
import { WorkspaceZone } from './WorkspaceZone';
import { DashboardZone } from './DashboardZone';
import { SettingsDialog, SettingsButton } from './SettingsDialog';
import { OnboardingOverlay } from './OnboardingOverlay';
import { ErrorBoundary } from './ErrorBoundary';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import {
  MessageSquare,
  Briefcase,
  BarChart3,
  Wifi,
  WifiOff,
  ChevronDown,
  Plus,
  FolderOpen,
  Sun,
  Moon,
} from 'lucide-react';

type MobileTab = 'lobby' | 'workspace' | 'dashboard';
type ThemeMode = 'dark' | 'light' | 'system';

export function KantorkuApp() {
  const {
    isBackendConnected,
    contractState,
    sessions,
    activeSessionId,
    setActiveSession,
    panelLayout,
    setPanelLayout,
  } = useKantorkuStore();
  const [mobileTab, setMobileTab] = useState<MobileTab>('lobby');

  // ── Theme Management ──────────────────────────────────────────
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'dark';
    return (localStorage.getItem('kantorku_theme') as ThemeMode) || 'dark';
  });

  const resolvedTheme = useMemo(() => {
    if (theme === 'system') {
      if (typeof window !== 'undefined') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return 'dark';
    }
    return theme;
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolvedTheme);
    if (resolvedTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [resolvedTheme]);

  useEffect(() => {
    localStorage.setItem('kantorku_theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      if (prev === 'dark') return 'light';
      if (prev === 'light') return 'system';
      return 'dark';
    });
  }, []);

  const isLightTheme = resolvedTheme === 'light';

  // ── Keyboard Shortcuts ──────────────────────────────────────
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey) {
        if (e.key === '1') {
          e.preventDefault();
          setMobileTab('lobby');
        } else if (e.key === '2') {
          e.preventDefault();
          setMobileTab('workspace');
        } else if (e.key === '3') {
          e.preventDefault();
          setMobileTab('dashboard');
        }
      }
    },
    []
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // ── Panel Layout Persistence ────────────────────────────────
  const handlePanelLayoutChange = useCallback(
    (sizes: number[]) => {
      if (sizes.length === 3) {
        setPanelLayout({
          lobby: sizes[0],
          workspace: sizes[1],
          dashboard: sizes[2],
        });
      }
    },
    [setPanelLayout]
  );

  // ── Session Info ────────────────────────────────────────────
  const activeSession = sessions.find((s) => s.session_id === activeSessionId);
  const sessionLabel = activeSession
    ? activeSession.contract_title || activeSession.session_id.slice(0, 12)
    : 'No Session';

  const handleNewSessionFromSwitcher = useCallback(() => {
    // The LobbyZone's handleNewSession will be called via the store reset
    setActiveSession('');
  }, [setActiveSession]);

  return (
    <div className={`h-screen w-screen flex flex-col overflow-hidden ${isLightTheme ? 'bg-[#f8fafc] text-slate-900' : 'bg-[#0a0e1a] text-white'}`}>
      {/* Top Bar */}
      <header className={`flex-shrink-0 h-10 border-b backdrop-blur-sm flex items-center justify-between px-3 z-50 ${isLightTheme ? 'border-cyan-200/50 bg-white/90' : 'border-cyan-900/30 bg-[#0a0e1a]/90'}`} role="banner">
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
            v0.4.1
          </Badge>

          {/* Session Switcher */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono border border-slate-700/50 bg-slate-800/50 hover:bg-slate-700/50 hover:border-cyan-500/30 transition-colors max-w-[140px]">
                <FolderOpen className="h-2.5 w-2.5 text-cyan-400 flex-shrink-0" />
                <span className="text-slate-300 truncate">{sessionLabel}</span>
                <ChevronDown className="h-2.5 w-2.5 text-slate-500 flex-shrink-0" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-56 bg-slate-900 border-slate-700/50"
            >
              {sessions.length > 0 ? (
                sessions.map((session) => (
                  <DropdownMenuItem
                    key={session.session_id}
                    onClick={() => setActiveSession(session.session_id)}
                    className={`text-xs font-mono cursor-pointer ${
                      session.session_id === activeSessionId
                        ? 'bg-cyan-500/10 text-cyan-300'
                        : 'text-slate-300'
                    }`}
                  >
                    <FolderOpen className="h-3 w-3 mr-2 flex-shrink-0" />
                    <span className="truncate">
                      {session.contract_title || session.session_id.slice(0, 16)}
                    </span>
                    <Badge
                      variant="outline"
                      className={`ml-auto text-[9px] px-1 py-0 h-3 ${
                        session.state === 'done'
                          ? 'border-green-500/30 text-green-300'
                          : session.state === 'failed'
                          ? 'border-red-500/30 text-red-300'
                          : session.state === 'working'
                          ? 'border-cyan-500/30 text-cyan-300'
                          : 'border-slate-600/50 text-slate-400'
                      }`}
                    >
                      {session.state}
                    </Badge>
                  </DropdownMenuItem>
                ))
              ) : (
                <div className="px-2 py-1.5 text-[10px] text-slate-500 font-mono">
                  No sessions yet
                </div>
              )}
              <DropdownMenuSeparator className="bg-slate-700/50" />
              <DropdownMenuItem
                onClick={handleNewSessionFromSwitcher}
                className="text-xs font-mono text-cyan-400 cursor-pointer"
              >
                <Plus className="h-3 w-3 mr-2" />
                New Session
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

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
          {/* Keyboard shortcut hints (desktop only) */}
          <div className={`hidden lg:flex items-center gap-1 text-[8px] font-mono ${isLightTheme ? 'text-slate-400' : 'text-slate-600'}`}>
            <kbd className={`px-0.5 py-0 rounded border ${isLightTheme ? 'bg-slate-100 border-slate-200' : 'bg-slate-800 border-slate-700/50'}`}>⌘1</kbd>
            <kbd className={`px-0.5 py-0 rounded border ${isLightTheme ? 'bg-slate-100 border-slate-200' : 'bg-slate-800 border-slate-700/50'}`}>⌘2</kbd>
            <kbd className={`px-0.5 py-0 rounded border ${isLightTheme ? 'bg-slate-100 border-slate-200' : 'bg-slate-800 border-slate-700/50'}`}>⌘3</kbd>
          </div>
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
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className={`p-1.5 rounded-md transition-colors ${isLightTheme ? 'hover:bg-slate-200' : 'hover:bg-slate-700/50'}`}
            title={`Theme: ${theme} (click to cycle)`}
            aria-label={`Switch theme, current: ${theme}`}
          >
            {theme === 'dark' ? (
              <Moon className="h-4 w-4 text-cyan-400" />
            ) : theme === 'light' ? (
              <Sun className="h-4 w-4 text-amber-500" />
            ) : (
              <div className="h-4 w-4 relative">
                <Sun className="h-3 w-3 text-amber-400 absolute top-0 left-0" />
                <Moon className="h-3 w-3 text-cyan-400 absolute bottom-0 right-0" />
              </div>
            )}
          </button>
          <SettingsButton isLightTheme={isLightTheme} />
        </div>
      </header>

      {/* Mobile Tab Bar */}
      <nav className={`flex-shrink-0 sm:hidden border-b backdrop-blur-sm ${isLightTheme ? 'border-cyan-200/50 bg-white/90' : 'border-cyan-900/30 bg-[#0a0e1a]/90'}`} aria-label="Main navigation">
        <div className="flex">
          {[
            { id: 'lobby' as const, icon: MessageSquare, label: 'Lobby' },
            { id: 'workspace' as const, icon: Briefcase, label: 'Workspace' },
            { id: 'dashboard' as const, icon: BarChart3, label: 'Dashboard' },
          ].map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              onClick={() => setMobileTab(id)}
              className={`flex-1 py-2 flex flex-col items-center gap-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400 ${isLightTheme ? 'focus:ring-offset-white' : 'focus:ring-offset-2 focus:ring-offset-[#0a0e1a]'} ${
                mobileTab === id
                  ? `text-cyan-400 border-b-2 border-cyan-400 ${isLightTheme ? 'bg-cyan-50' : ''}`
                  : isLightTheme ? 'text-slate-400' : 'text-slate-500'
              }`}
              aria-label={`Switch to ${label}`}
              aria-current={mobileTab === id ? 'page' : undefined}
            >
              <Icon className="h-4 w-4" />
              <span className={`text-[9px] font-mono ${isLightTheme && mobileTab !== id ? 'text-slate-500' : ''}`}>{label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden" id="main-content" role="main">
        {/* Desktop 3-Panel Layout */}
        <div className="hidden sm:block h-full">
          <ResizablePanelGroup
            direction="horizontal"
            className="h-full"
            onLayout={handlePanelLayoutChange}
          >
            {/* Lobby Zone */}
            <ResizablePanel
              defaultSize={panelLayout.lobby}
              minSize={20}
              maxSize={45}
            >
              <div className={`h-full border-r ${isLightTheme ? 'border-cyan-200/30' : 'border-cyan-900/20'}`}>
                <ErrorBoundary fallbackTitle="Lobby Error">
                  <LobbyZone />
                </ErrorBoundary>
              </div>
            </ResizablePanel>

            <ResizableHandle className={`${isLightTheme ? 'bg-cyan-200/20 hover:bg-cyan-300/30' : 'bg-cyan-900/20 hover:bg-cyan-700/30'} transition-colors w-0.5`} />

            {/* Workspace Zone */}
            <ResizablePanel
              defaultSize={panelLayout.workspace}
              minSize={30}
            >
              <div className={`h-full border-r ${isLightTheme ? 'border-cyan-200/30' : 'border-cyan-900/20'}`}>
                <ErrorBoundary fallbackTitle="Workspace Error">
                  <WorkspaceZone />
                </ErrorBoundary>
              </div>
            </ResizablePanel>

            <ResizableHandle className={`${isLightTheme ? 'bg-cyan-200/20 hover:bg-cyan-300/30' : 'bg-cyan-900/20 hover:bg-cyan-700/30'} transition-colors w-0.5`} />

            {/* Dashboard Zone */}
            <ResizablePanel
              defaultSize={panelLayout.dashboard}
              minSize={18}
              maxSize={40}
            >
              <div className="h-full">
                <ErrorBoundary fallbackTitle="Dashboard Error">
                  <DashboardZone />
                </ErrorBoundary>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>

        {/* Mobile Single-Panel Layout */}
        <div className="sm:hidden h-full">
          {mobileTab === 'lobby' && <ErrorBoundary fallbackTitle="Lobby Error"><LobbyZone /></ErrorBoundary>}
          {mobileTab === 'workspace' && <ErrorBoundary fallbackTitle="Workspace Error"><WorkspaceZone /></ErrorBoundary>}
          {mobileTab === 'dashboard' && <ErrorBoundary fallbackTitle="Dashboard Error"><DashboardZone /></ErrorBoundary>}
        </div>
      </div>

      {/* Settings Dialog */}
      <SettingsDialog />

      {/* Onboarding Overlay */}
      <OnboardingOverlay />

      {/* Skip to content link for accessibility */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[60] focus:px-3 focus:py-1 focus:bg-cyan-600 focus:text-white focus:rounded focus:text-sm">
        Skip to content
      </a>
    </div>
  );
}
