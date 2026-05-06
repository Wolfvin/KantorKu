'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import type { EntryType, LibraryEntry } from '@/lib/kantorku/types';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Search,
  BookOpen,
  Lightbulb,
  MessageSquare,
  Wrench,
  Star,
  Filter,
  ArrowUpDown,
} from 'lucide-react';

const ENTRY_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string }> = {
  knowledge: { icon: <BookOpen className="h-3.5 w-3.5" />, color: 'text-cyan-400' },
  solution: { icon: <Lightbulb className="h-3.5 w-3.5" />, color: 'text-amber-400' },
  qa_pair: { icon: <MessageSquare className="h-3.5 w-3.5" />, color: 'text-teal-400' },
  procedure: { icon: <Wrench className="h-3.5 w-3.5" />, color: 'text-green-400' },
};

type SortBy = 'relevance' | 'quality' | 'date';

export function SearchComponent() {
  const {
    libraryEntries,
    librarySearchQuery,
    librarySearchTypeFilter,
    librarySearchMinQuality,
    setLibrarySearchQuery,
    setLibrarySearchResults,
    setLibrarySearchTypeFilter,
    setLibrarySearchMinQuality,
    setLibrarySelectedEntry,
  } = useKantorkuStore();
  const t = useTranslations().t;
  const [sortBy, setSortBy] = useState<SortBy>('relevance');
  const [localQuery, setLocalQuery] = useState(librarySearchQuery);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setLibrarySearchQuery(localQuery);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [localQuery, setLibrarySearchQuery]);

  // Filter and sort entries
  const results = React.useMemo(() => {
    let filtered = [...libraryEntries];

    if (librarySearchQuery) {
      const q = librarySearchQuery.toLowerCase();
      filtered = filtered.filter(
        (e) =>
          e.title.toLowerCase().includes(q) ||
          e.content.toLowerCase().includes(q) ||
          e.keywords.some((k) => k.toLowerCase().includes(q)) ||
          e.summary.toLowerCase().includes(q)
      );
    }

    if (librarySearchTypeFilter !== 'all') {
      filtered = filtered.filter((e) => e.entry_type === librarySearchTypeFilter);
    }

    filtered = filtered.filter((e) => e.quality_score >= librarySearchMinQuality);

    // Sort
    switch (sortBy) {
      case 'quality':
        filtered.sort((a, b) => b.quality_score - a.quality_score);
        break;
      case 'date':
        filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case 'relevance':
      default:
        if (librarySearchQuery) {
          const q = librarySearchQuery.toLowerCase();
          filtered.sort((a, b) => {
            const aTitle = a.title.toLowerCase().includes(q) ? 2 : 0;
            const bTitle = b.title.toLowerCase().includes(q) ? 2 : 0;
            return (bTitle + b.quality_score) - (aTitle + a.quality_score);
          });
        } else {
          filtered.sort((a, b) => b.quality_score - a.quality_score);
        }
    }

    return filtered;
  }, [libraryEntries, librarySearchQuery, librarySearchTypeFilter, librarySearchMinQuality, sortBy]);

  return (
    <div className="flex flex-col h-full">
      {/* Search bar + filters */}
      <div className="flex-shrink-0 p-3 space-y-2 border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
            <Input
              value={localQuery}
              onChange={(e) => setLocalQuery(e.target.value)}
              placeholder={t('library.searchPlaceholder')}
              className="pl-8 text-xs bg-slate-900/50 border-slate-700/50 h-8"
            />
          </div>
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortBy)}>
            <SelectTrigger className="w-[110px] text-[10px] h-8 bg-slate-900/50 border-slate-700/50">
              <ArrowUpDown className="h-3 w-3 mr-1" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="relevance">{t('library.sortRelevance')}</SelectItem>
              <SelectItem value="quality">{t('library.sortQuality')}</SelectItem>
              <SelectItem value="date">{t('library.sortDate')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-3 w-3 text-slate-500" />
          <Select value={librarySearchTypeFilter} onValueChange={(v) => setLibrarySearchTypeFilter(v as EntryType | 'all')}>
            <SelectTrigger className="w-[120px] text-[10px] h-6 bg-slate-900/50 border-slate-700/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all')}</SelectItem>
              <SelectItem value="knowledge">Knowledge</SelectItem>
              <SelectItem value="solution">Solution</SelectItem>
              <SelectItem value="qa_pair">Q&A</SelectItem>
              <SelectItem value="procedure">Procedure</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center gap-1.5 ml-auto">
            <span className="text-[9px] text-slate-500 font-mono">{t('library.minQuality')}</span>
            <Input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={librarySearchMinQuality}
              onChange={(e) => setLibrarySearchMinQuality(parseFloat(e.target.value) || 0)}
              className="w-14 text-[10px] h-6 bg-slate-900/50 border-slate-700/50 text-center font-mono"
            />
          </div>
        </div>
        <div className="text-[9px] text-slate-600 font-mono">
          {results.length} {t('common.entries')} {librarySearchQuery ? t('library.forQuery') + ' "' + librarySearchQuery + '"' : ''}
        </div>
      </div>

      {/* Results */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1.5">
          {results.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Search className="h-10 w-10 mx-auto mb-3 text-slate-700" />
              <p className="text-sm font-mono">{t('library.noResults')}</p>
              <p className="text-[10px] text-slate-600 mt-1">{t('library.tryDifferent')}</p>
            </div>
          ) : (
            results.map((entry) => {
              const typeConfig = ENTRY_TYPE_CONFIG[entry.entry_type] || ENTRY_TYPE_CONFIG.knowledge;
              return (
                <button
                  key={entry.id}
                  className="w-full text-left p-2.5 rounded-md border border-slate-800/50 bg-slate-900/30 hover:bg-slate-800/40 hover:border-cyan-500/20 transition-colors"
                  onClick={() => setLibrarySelectedEntry(entry)}
                >
                  <div className="flex items-start gap-2">
                    <div className={typeConfig.color}>{typeConfig.icon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-slate-200 font-medium truncate">
                          {entry.title || t('library.untitled')}
                        </span>
                        {entry.verified && (
                          <Badge variant="outline" className="text-[8px] px-0.5 py-0 h-3 border-green-500/30 text-green-400">
                            ✓
                          </Badge>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-500 truncate mt-0.5">
                        {entry.summary || entry.content.substring(0, 100)}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        {entry.shelf_path.length > 0 && (
                          <span className="text-[9px] text-slate-600 font-mono truncate">
                            {entry.shelf_path.join(' / ')}
                          </span>
                        )}
                        <div className="flex items-center gap-0.5 ml-auto">
                          <Star className="h-2.5 w-2.5 text-amber-400" />
                          <span className="text-[9px] text-slate-500 font-mono">
                            {(entry.quality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
