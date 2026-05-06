'use client';

import React, { useEffect, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  BarChart3,
  BookOpen,
  Lightbulb,
  MessageSquare,
  Wrench,
  TrendingUp,
  Eye,
  Database,
  Activity,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const TYPE_COLORS: Record<string, string> = {
  knowledge: '#06b6d4',
  solution: '#f59e0b',
  qa_pair: '#14b8a6',
  procedure: '#22c55e',
};

const TYPE_LABELS: Record<string, string> = {
  knowledge: 'Knowledge',
  solution: 'Solution',
  qa_pair: 'Q&A',
  procedure: 'Procedure',
};

export function StatsDashboard() {
  const { libraryEntries, libraryStats, setLibraryStats, setLibraryLoading } = useKantorkuStore();
  const t = useTranslations().t;

  // Compute stats from entries
  const computedStats = React.useMemo(() => {
    const entriesByType: Record<string, number> = { knowledge: 0, solution: 0, qa_pair: 0, procedure: 0 };
    let totalQuality = 0;
    let totalUsage = 0;
    const shelfMap: Record<string, { count: number; quality: number }> = {};

    libraryEntries.forEach((e) => {
      entriesByType[e.entry_type] = (entriesByType[e.entry_type] || 0) + 1;
      totalQuality += e.quality_score;
      totalUsage += e.usage_count;
      const shelfKey = e.shelf_path.join(' / ') || 'Uncategorized';
      if (!shelfMap[shelfKey]) shelfMap[shelfKey] = { count: 0, quality: 0 };
      shelfMap[shelfKey].count++;
      shelfMap[shelfKey].quality += e.quality_score;
    });

    const topShelves = Object.entries(shelfMap)
      .map(([path, data]) => ({
        path,
        count: data.count,
        avg_quality: data.count > 0 ? data.quality / data.count : 0,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Quality distribution
    const qualityBuckets = [
      { range: '0.0-0.2', count: 0 },
      { range: '0.2-0.4', count: 0 },
      { range: '0.4-0.6', count: 0 },
      { range: '0.6-0.8', count: 0 },
      { range: '0.8-1.0', count: 0 },
    ];
    libraryEntries.forEach((e) => {
      const idx = Math.min(Math.floor(e.quality_score * 5), 4);
      qualityBuckets[idx].count++;
    });

    return {
      total: libraryEntries.length,
      entriesByType,
      avgQuality: libraryEntries.length > 0 ? totalQuality / libraryEntries.length : 0,
      totalUsage,
      topShelves,
      qualityDistribution: qualityBuckets,
      trendingEntries: [...libraryEntries]
        .sort((a, b) => b.usage_count - a.usage_count)
        .slice(0, 5),
    };
  }, [libraryEntries]);

  const chartData = Object.entries(computedStats.entriesByType).map(([type, count]) => ({
    name: TYPE_LABELS[type] || type,
    count,
    color: TYPE_COLORS[type] || '#94a3b8',
  }));

  const qualityChartData = computedStats.qualityDistribution.map((d) => ({
    ...d,
    qualityColor: d.range === '0.8-1.0' ? '#22c55e' : d.range === '0.6-0.8' ? '#84cc16' : d.range === '0.4-0.6' ? '#f59e0b' : d.range === '0.2-0.4' ? '#f97316' : '#ef4444',
  }));

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Overview cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
            <div className="flex items-center gap-1.5 mb-1">
              <Database className="h-3 w-3 text-cyan-400" />
              <span className="text-[9px] text-slate-500 uppercase font-mono">{t('library.totalEntries')}</span>
            </div>
            <span className="text-lg font-mono font-bold text-slate-200">{computedStats.total}</span>
          </div>
          <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
            <div className="flex items-center gap-1.5 mb-1">
              <Activity className="h-3 w-3 text-amber-400" />
              <span className="text-[9px] text-slate-500 uppercase font-mono">{t('library.avgQuality')}</span>
            </div>
            <span className="text-lg font-mono font-bold text-slate-200">
              {(computedStats.avgQuality * 100).toFixed(0)}%
            </span>
          </div>
          <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
            <div className="flex items-center gap-1.5 mb-1">
              <Eye className="h-3 w-3 text-teal-400" />
              <span className="text-[9px] text-slate-500 uppercase font-mono">{t('library.totalUsage')}</span>
            </div>
            <span className="text-lg font-mono font-bold text-slate-200">{computedStats.totalUsage}</span>
          </div>
          <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
            <div className="flex items-center gap-1.5 mb-1">
              <BarChart3 className="h-3 w-3 text-green-400" />
              <span className="text-[9px] text-slate-500 uppercase font-mono">{t('library.shelves')}</span>
            </div>
            <span className="text-lg font-mono font-bold text-slate-200">
              {computedStats.topShelves.length}
            </span>
          </div>
        </div>

        {/* Entry count by type */}
        <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
          <h4 className="text-[10px] text-slate-500 uppercase font-mono font-semibold mb-3">
            {t('library.entriesByType')}
          </h4>
          <div className="h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9, fill: '#64748b' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    fontSize: '10px',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Quality distribution */}
        <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
          <h4 className="text-[10px] text-slate-500 uppercase font-mono font-semibold mb-3">
            {t('library.qualityDistribution')}
          </h4>
          <div className="h-[140px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={qualityChartData}>
                <XAxis dataKey="range" tick={{ fontSize: 8, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9, fill: '#64748b' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    fontSize: '10px',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {qualityChartData.map((entry, index) => (
                    <Cell key={index} fill={entry.qualityColor} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top shelves */}
        <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
          <h4 className="text-[10px] text-slate-500 uppercase font-mono font-semibold mb-2">
            {t('library.topShelves')}
          </h4>
          {computedStats.topShelves.length === 0 ? (
            <p className="text-[10px] text-slate-600 font-mono">{t('library.noData')}</p>
          ) : (
            <div className="space-y-1.5">
              {computedStats.topShelves.map((shelf) => (
                <div key={shelf.path} className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 font-mono truncate flex-1">
                    {shelf.path}
                  </span>
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-slate-700/50 text-slate-500">
                    {shelf.count}
                  </Badge>
                  <div className="w-16">
                    <Progress
                      value={shelf.avg_quality * 100}
                      className="h-1 bg-slate-800"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Trending entries */}
        {computedStats.trendingEntries.length > 0 && (
          <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
            <h4 className="text-[10px] text-slate-500 uppercase font-mono font-semibold mb-2">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              {t('library.trending')}
            </h4>
            <div className="space-y-1">
              {computedStats.trendingEntries.map((entry) => (
                <div key={entry.id} className="flex items-center gap-2 text-[10px]">
                  <Eye className="h-2.5 w-2.5 text-slate-600 flex-shrink-0" />
                  <span className="text-slate-400 truncate">{entry.title || t('library.untitled')}</span>
                  <span className="text-slate-600 font-mono ml-auto flex-shrink-0">{entry.usage_count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Vector coverage */}
        <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-slate-500 uppercase font-mono">{t('library.vectorCoverage')}</span>
            <span className="text-[10px] text-cyan-400 font-mono">
              {computedStats.total > 0 ? '100%' : '0%'}
            </span>
          </div>
          <Progress value={computedStats.total > 0 ? 100 : 0} className="h-1.5 bg-slate-800" />
        </div>
      </div>
    </ScrollArea>
  );
}
