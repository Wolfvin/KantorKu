'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import { ShelfBrowser } from '@/components/kantorku/library/shelf-browser';
import { Reader } from '@/components/kantorku/library/reader';
import { AskChat } from '@/components/kantorku/library/ask-chat';
import { Ingest } from '@/components/kantorku/library/ingest';
import { SearchComponent } from '@/components/kantorku/library/search';
import { ExportDashboard } from '@/components/kantorku/library/export-dashboard';
import { StatsDashboard } from '@/components/kantorku/library/stats-dashboard';
import { SettingsPanel } from '@/components/kantorku/library/settings';
import {
  Search,
  MessageCircle,
  Upload,
  Download,
  BarChart3,
  Settings,
  BookOpen,
  ArrowLeft,
} from 'lucide-react';

interface LibraryZoneProps {
  onBack?: () => void;
  isLightTheme?: boolean;
}

export function LibraryZone({ onBack, isLightTheme = false }: LibraryZoneProps) {
  const {
    libraryEntries,
    librarySelectedEntry,
    setLibrarySelectedEntry,
    libraryShelves,
    setLibraryShelves,
    setLibraryEntries,
    setLibraryLoading,
    setLibraryStats,
  } = useKantorkuStore();
  const t = useTranslations().t;
  const [activeTab, setActiveTab] = useState('browse');

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      setLibraryLoading(true);
      try {
        const [shelvesResp, entriesResp, statsResp] = await Promise.allSettled([
          fetch('/api/library/shelves'),
          fetch('/api/library'),
          fetch('/api/library/stats'),
        ]);

        if (shelvesResp.status === 'fulfilled' && shelvesResp.value.ok) {
          const data = await shelvesResp.value.json();
          setLibraryShelves(data.shelves || []);
        }

        if (entriesResp.status === 'fulfilled' && entriesResp.value.ok) {
          const data = await entriesResp.value.json();
          setLibraryEntries(data.entries || []);
        }

        if (statsResp.status === 'fulfilled' && statsResp.value.ok) {
          const data = await statsResp.value.json();
          setLibraryStats(data);
        }
      } catch {
        // Handle error silently
      } finally {
        setLibraryLoading(false);
      }
    };
    loadData();
  }, [setLibraryShelves, setLibraryEntries, setLibraryStats, setLibraryLoading]);

  const handleShelfSelect = useCallback(
    (path: string[]) => {
      setActiveTab('search');
    },
    []
  );

  const bgClass = isLightTheme ? 'bg-[#f8fafc] text-slate-900' : 'bg-[#0a0e1a] text-white';
  const borderClass = isLightTheme ? 'border-cyan-200/30' : 'border-slate-800/50';
  const headerBg = isLightTheme ? 'bg-white/90 border-cyan-200/50' : 'bg-[#0a0e1a]/90 border-slate-800/50';
  const tabBg = isLightTheme ? 'bg-slate-100/50' : 'bg-slate-900/50';

  return (
    <div className={`h-full flex flex-col ${bgClass}`}>
      {/* Library Header */}
      <div className={`flex-shrink-0 h-10 border-b ${headerBg} backdrop-blur-sm flex items-center px-3 gap-2`}>
        {onBack && (
          <Button
            variant="ghost"
            size="sm"
            className={`text-[10px] h-6 px-1 ${isLightTheme ? 'text-slate-500 hover:text-cyan-600' : 'text-slate-400 hover:text-cyan-400'}`}
            onClick={onBack}
          >
            <ArrowLeft className="h-3 w-3 mr-1" />
            {t('common.back')}
          </Button>
        )}
        <div className="flex items-center gap-1.5">
          <BookOpen className={`h-4 w-4 ${isLightTheme ? 'text-cyan-600' : 'text-cyan-400'}`} />
          <h2 className="text-xs font-bold bg-gradient-to-r from-cyan-400 to-teal-300 bg-clip-text text-transparent">
            Library
          </h2>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Badge
            variant="outline"
            className={`text-[8px] px-1 py-0 h-4 font-mono ${isLightTheme ? 'border-cyan-300/50 text-cyan-600 bg-cyan-50' : 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10'}`}
          >
            {libraryEntries.length} {t('common.entries')}
          </Badge>
          <Badge
            variant="outline"
            className={`text-[8px] px-1 py-0 h-4 font-mono ${isLightTheme ? 'border-slate-300/50 text-slate-500' : 'border-slate-700/50 text-slate-500'}`}
          >
            {libraryShelves.length} {t('library.shelves')}
          </Badge>
        </div>
      </div>

      {/* Tab Bar */}
      <div className={`flex-shrink-0 border-b ${borderClass} px-2 pt-1`}>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className={`${tabBg} h-7 w-full justify-start gap-0 overflow-x-auto`}>
            <TabsTrigger value="browse" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <BookOpen className="h-3 w-3 mr-1" />
              {t('library.browse')}
            </TabsTrigger>
            <TabsTrigger value="search" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <Search className="h-3 w-3 mr-1" />
              {t('common.search')}
            </TabsTrigger>
            <TabsTrigger value="ask" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <MessageCircle className="h-3 w-3 mr-1" />
              {t('library.ask')}
            </TabsTrigger>
            <TabsTrigger value="ingest" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <Upload className="h-3 w-3 mr-1" />
              {t('library.ingest')}
            </TabsTrigger>
            <TabsTrigger value="export" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <Download className="h-3 w-3 mr-1" />
              {t('common.export')}
            </TabsTrigger>
            <TabsTrigger value="stats" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <BarChart3 className="h-3 w-3 mr-1" />
              {t('library.stats')}
            </TabsTrigger>
            <TabsTrigger value="settings" className={`text-[10px] px-2 h-6 ${isLightTheme ? 'data-[state=active]:bg-cyan-100 data-[state=active]:text-cyan-700' : 'data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400'}`}>
              <Settings className="h-3 w-3 mr-1" />
              {t('library.settings')}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'browse' && (
          <div className="flex h-full">
            <div className={`w-56 border-r ${borderClass} h-full overflow-hidden`}>
              <ShelfBrowser onShelfSelect={handleShelfSelect} />
            </div>
            <div className="flex-1 h-full overflow-hidden">
              <Reader
                entry={librarySelectedEntry}
                onBack={() => setLibrarySelectedEntry(null)}
              />
            </div>
          </div>
        )}

        {activeTab === 'search' && (
          <div className="h-full">
            <SearchComponent />
          </div>
        )}

        {activeTab === 'ask' && (
          <div className="h-full">
            <AskChat />
          </div>
        )}

        {activeTab === 'ingest' && (
          <div className="h-full overflow-auto">
            <Ingest />
          </div>
        )}

        {activeTab === 'export' && (
          <div className="h-full overflow-auto">
            <ExportDashboard />
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="h-full">
            <StatsDashboard />
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="h-full overflow-auto">
            <SettingsPanel />
          </div>
        )}
      </div>
    </div>
  );
}
