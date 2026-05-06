'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ShelfBrowser } from '@/components/kantorku/library/shelf-browser';
import { Reader } from '@/components/kantorku/library/reader';
import { AskChat } from '@/components/kantorku/library/ask-chat';
import { Ingest } from '@/components/kantorku/library/ingest';
import { SearchComponent } from '@/components/kantorku/library/search';
import { ExportDashboard } from '@/components/kantorku/library/export-dashboard';
import { StatsDashboard } from '@/components/kantorku/library/stats-dashboard';
import { SettingsPanel } from '@/components/kantorku/library/settings';
import {
  Library,
  Search,
  MessageCircle,
  Upload,
  Download,
  BarChart3,
  Settings,
  BookOpen,
} from 'lucide-react';

export default function LibraryPage() {
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
        // Load shelves
        const shelvesResp = await fetch('/api/library/shelves');
        if (shelvesResp.ok) {
          const data = await shelvesResp.json();
          setLibraryShelves(data.shelves || []);
        }

        // Load entries
        const entriesResp = await fetch('/api/library');
        if (entriesResp.ok) {
          const data = await entriesResp.json();
          setLibraryEntries(data.entries || []);
        }

        // Load stats
        const statsResp = await fetch('/api/library/stats');
        if (statsResp.ok) {
          const data = await statsResp.json();
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

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e1a] text-white">
      {/* Header */}
      <header className="flex-shrink-0 h-12 border-b border-cyan-900/30 bg-[#0a0e1a]/90 backdrop-blur-sm flex items-center px-4 gap-3">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-500 flex items-center justify-center">
            <Library className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold bg-gradient-to-r from-cyan-400 to-teal-300 bg-clip-text text-transparent">
              KantorKu Library
            </h1>
            <p className="text-[9px] text-slate-500 font-mono">
              {libraryEntries.length} {t('common.entries')} · {libraryShelves.length} {t('library.shelves')}
            </p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
            v0.4.1
          </Badge>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="h-full flex flex-col"
        >
          <div className="flex-shrink-0 border-b border-slate-800/50 px-2 pt-1">
            <TabsList className="bg-slate-900/50 h-8 w-full justify-start gap-0.5 overflow-x-auto">
              <TabsTrigger value="browse" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <BookOpen className="h-3 w-3 mr-1" />
                {t('library.browse')}
              </TabsTrigger>
              <TabsTrigger value="search" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <Search className="h-3 w-3 mr-1" />
                {t('common.search')}
              </TabsTrigger>
              <TabsTrigger value="ask" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <MessageCircle className="h-3 w-3 mr-1" />
                {t('library.ask')}
              </TabsTrigger>
              <TabsTrigger value="ingest" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <Upload className="h-3 w-3 mr-1" />
                {t('library.ingest')}
              </TabsTrigger>
              <TabsTrigger value="export" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <Download className="h-3 w-3 mr-1" />
                {t('common.export')}
              </TabsTrigger>
              <TabsTrigger value="stats" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <BarChart3 className="h-3 w-3 mr-1" />
                {t('library.stats')}
              </TabsTrigger>
              <TabsTrigger value="settings" className="text-[10px] px-2 h-7 data-[state=active]:bg-cyan-500/10 data-[state=active]:text-cyan-400">
                <Settings className="h-3 w-3 mr-1" />
                {t('library.settings')}
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-hidden">
            {/* Browse: Split view with shelves and reader */}
            <TabsContent value="browse" className="h-full m-0">
              <div className="flex h-full">
                <div className="w-64 border-r border-slate-800/50 h-full overflow-hidden">
                  <ShelfBrowser onShelfSelect={handleShelfSelect} />
                </div>
                <div className="flex-1 h-full overflow-hidden">
                  <Reader
                    entry={librarySelectedEntry}
                    onBack={() => setLibrarySelectedEntry(null)}
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="search" className="h-full m-0">
              <SearchComponent />
            </TabsContent>

            <TabsContent value="ask" className="h-full m-0">
              <AskChat />
            </TabsContent>

            <TabsContent value="ingest" className="h-full m-0 overflow-auto">
              <Ingest />
            </TabsContent>

            <TabsContent value="export" className="h-full m-0 overflow-auto">
              <ExportDashboard />
            </TabsContent>

            <TabsContent value="stats" className="h-full m-0">
              <StatsDashboard />
            </TabsContent>

            <TabsContent value="settings" className="h-full m-0 overflow-auto">
              <SettingsPanel />
            </TabsContent>
          </div>
        </Tabs>
      </main>
    </div>
  );
}
