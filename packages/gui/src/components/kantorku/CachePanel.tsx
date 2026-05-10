'use client';

import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useKantorkuStore } from '@/lib/kantorku/store';
import {
  Database,
  Trash2,
  Clock,
  Zap,
  TrendingUp,
  Key,
  Server,
  X,
} from 'lucide-react';

function formatTTL(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(0)}s`;
  if (ms < 3_600_000) return `${(ms / 60_000).toFixed(0)}m`;
  return `${(ms / 3_600_000).toFixed(1)}h`;
}

function formatAge(isoDate: string): string {
  const now = Date.now();
  const created = new Date(isoDate).getTime();
  const diffMs = now - created;
  if (diffMs < 1000) return 'just now';
  if (diffMs < 60_000) return `${(diffMs / 1000).toFixed(0)}s ago`;
  if (diffMs < 3_600_000) return `${(diffMs / 60_000).toFixed(0)}m ago`;
  return `${(diffMs / 3_600_000).toFixed(1)}h ago`;
}

function truncateKey(key: string, maxLen = 28): string {
  if (key.length <= maxLen) return key;
  return `${key.slice(0, maxLen - 3)}...`;
}

export function CachePanel() {
  const cacheEntries = useKantorkuStore((s) => s.cacheEntries);
  const removeCacheEntry = useKantorkuStore((s) => s.removeCacheEntry);
  const clearCache = useKantorkuStore((s) => s.clearCache);

  const stats = useMemo(() => {
    const totalEntries = cacheEntries.length;
    const totalHits = cacheEntries.reduce((sum, e) => sum + e.hit_count, 0);
    const avgTTL =
      totalEntries > 0
        ? cacheEntries.reduce((sum, e) => sum + e.ttl_ms, 0) / totalEntries
        : 0;
    return { totalEntries, totalHits, avgTTL };
  }, [cacheEntries]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              LLM Cache
            </span>
            <Badge
              variant="outline"
              className="text-[8px] px-1 py-0 h-3.5 border-cyan-500/30 text-cyan-300 font-mono"
            >
              {stats.totalEntries} entries
            </Badge>
          </div>
          {cacheEntries.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1.5 text-[9px] text-red-400/70 hover:text-red-300"
              onClick={clearCache}
            >
              <Trash2 className="h-3 w-3 mr-0.5" />
              Clear All
            </Button>
          )}
        </div>
      </div>

      {/* Stats Row */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/20 bg-slate-900/20">
        <div className="grid grid-cols-3 gap-2">
          <Card className="bg-slate-800/40 border-slate-700/20">
            <CardContent className="p-2 text-center">
              <div className="flex items-center justify-center gap-1 mb-0.5">
                <Key className="h-2.5 w-2.5 text-cyan-400/70" />
                <span className="text-[8px] text-slate-500 uppercase font-mono">
                  Entries
                </span>
              </div>
              <p className="text-xs font-bold text-cyan-300 font-mono">
                {stats.totalEntries}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/40 border-slate-700/20">
            <CardContent className="p-2 text-center">
              <div className="flex items-center justify-center gap-1 mb-0.5">
                <Zap className="h-2.5 w-2.5 text-amber-400/70" />
                <span className="text-[8px] text-slate-500 uppercase font-mono">
                  Hits
                </span>
              </div>
              <p className="text-xs font-bold text-amber-300 font-mono">
                {stats.totalHits}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/40 border-slate-700/20">
            <CardContent className="p-2 text-center">
              <div className="flex items-center justify-center gap-1 mb-0.5">
                <Clock className="h-2.5 w-2.5 text-teal-400/70" />
                <span className="text-[8px] text-slate-500 uppercase font-mono">
                  Avg TTL
                </span>
              </div>
              <p className="text-xs font-bold text-teal-300 font-mono">
                {formatTTL(stats.avgTTL)}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Cache Entries Table */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2">
        {cacheEntries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-slate-500">
            <Database className="h-8 w-8 text-slate-600/50 mb-2" />
            <p className="text-[10px] text-center text-slate-600">
              Cache is empty.
              <br />
              Entries will appear when LLM responses are cached.
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {/* Table Header */}
            <div className="grid grid-cols-[1fr_48px_60px_52px_28px] gap-1 px-2 py-1 text-[8px] text-slate-500 uppercase font-mono border-b border-slate-700/20">
              <span>Key</span>
              <span className="text-center">Hits</span>
              <span>Provider</span>
              <span className="text-center">Age</span>
              <span />
            </div>

            {cacheEntries.map((entry) => (
              <Card
                key={entry.key}
                className="bg-slate-800/30 border-slate-700/15 hover:border-slate-600/40 transition-all duration-200"
              >
                <CardContent className="p-1.5">
                  <div className="grid grid-cols-[1fr_48px_60px_52px_28px] gap-1 items-center">
                    {/* Key (truncated) */}
                    <div className="flex items-center gap-1 min-w-0">
                      <TrendingUp className="h-2.5 w-2.5 text-cyan-400/50 flex-shrink-0" />
                      <span
                        className="text-[9px] font-mono text-slate-300 truncate"
                        title={entry.key}
                      >
                        {truncateKey(entry.key)}
                      </span>
                    </div>

                    {/* Hit Count */}
                    <div className="text-center">
                      <Badge
                        variant="outline"
                        className={`text-[8px] px-1 py-0 h-3.5 font-mono ${
                          entry.hit_count > 5
                            ? 'border-amber-500/30 text-amber-300 bg-amber-500/10'
                            : entry.hit_count > 0
                              ? 'border-cyan-500/30 text-cyan-300 bg-cyan-500/10'
                              : 'border-slate-700/30 text-slate-500'
                        }`}
                      >
                        {entry.hit_count}
                      </Badge>
                    </div>

                    {/* Provider */}
                    <div className="flex items-center gap-0.5 min-w-0">
                      <Server className="h-2.5 w-2.5 text-slate-500 flex-shrink-0" />
                      <span className="text-[8px] text-slate-400 font-mono truncate">
                        {entry.provider || entry.model?.split('/')[0] || '—'}
                      </span>
                    </div>

                    {/* Age */}
                    <div className="text-center">
                      <span className="text-[8px] text-slate-500 font-mono">
                        {formatAge(entry.created_at)}
                      </span>
                    </div>

                    {/* Remove Button */}
                    <button
                      onClick={() => removeCacheEntry(entry.key)}
                      className="p-0.5 rounded text-slate-600 hover:text-red-400 transition-colors"
                      title="Remove entry"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Model info (if available) */}
                  {entry.model && (
                    <div className="mt-0.5 ml-4">
                      <Badge
                        variant="outline"
                        className="text-[7px] px-1 py-0 h-3 border-slate-700/30 text-slate-500 font-mono"
                      >
                        {entry.model}
                      </Badge>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
