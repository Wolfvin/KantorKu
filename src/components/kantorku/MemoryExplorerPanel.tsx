'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { MEMORY_RINGS } from '@/lib/kantorku/workers-data';
import { MemoryEntry } from '@/lib/kantorku/types';
import { Brain, Search, Eye, Clock, Hash, Database, ChevronRight, ArrowLeft, Plus, Trash2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

const RING_STYLES: Record<number, { accent: string; border: string; bg: string; glow: string }> = {
  1: { accent: '#06b6d4', border: '#06b6d440', bg: '#06b6d410', glow: '#06b6d420' },
  2: { accent: '#f59e0b', border: '#f59e0b40', bg: '#f59e0b10', glow: '#f59e0b20' },
  3: { accent: '#ec4899', border: '#ec489940', bg: '#ec489910', glow: '#ec489920' },
};

// Semantic search simulation: keyword-based matching with relevance score
function semanticSearch(entries: MemoryEntry[], query: string): Array<MemoryEntry & { relevance: number }> {
  if (!query.trim()) return entries.map((e) => ({ ...e, relevance: 1 }));
  const keywords = query.toLowerCase().split(/\s+/).filter(Boolean);
  return entries
    .map((entry) => {
      const text = `${entry.key} ${entry.value} ${(entry.tags || []).join(' ')}`.toLowerCase();
      let matchCount = 0;
      let exactMatch = 0;
      keywords.forEach((kw) => {
        if (text.includes(kw)) {
          matchCount++;
          // Boost for exact key match
          if (entry.key.toLowerCase().includes(kw)) exactMatch++;
          // Boost for tag match
          if (entry.tags?.some((t) => t.toLowerCase().includes(kw))) exactMatch += 0.5;
        }
      });
      const relevance = keywords.length > 0 ? (matchCount / keywords.length) * 0.6 + (exactMatch / keywords.length) * 0.4 : 0;
      return { ...entry, relevance: Math.min(relevance, 1) };
    })
    .filter((e) => e.relevance > 0)
    .sort((a, b) => b.relevance - a.relevance);
}

export function MemoryExplorerPanel() {
  const { memoryEntries, queryMemory, addMemoryEntry, clearMemoryRing } = useKantorkuStore();
  const [selectedRing, setSelectedRing] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEntry, setNewEntry] = useState({ key: '', value: '', tags: '' });

  const ringCounts = useMemo(() => {
    const counts: Record<number, number> = { 1: 0, 2: 0, 3: 0 };
    memoryEntries.forEach((e) => {
      counts[e.ring] = (counts[e.ring] || 0) + 1;
    });
    return counts;
  }, [memoryEntries]);

  // Ring size: estimate based on entry count and value sizes
  const ringSizes = useMemo(() => {
    const sizes: Record<number, string> = { 1: '0 B', 2: '0 B', 3: '0 B' };
    [1, 2, 3].forEach((ring) => {
      const entries = memoryEntries.filter((e) => e.ring === ring);
      const totalBytes = entries.reduce((sum, e) => sum + (e.key.length + e.value.length) * 2, 0);
      if (totalBytes < 1024) sizes[ring] = `${totalBytes} B`;
      else if (totalBytes < 1024 * 1024) sizes[ring] = `${(totalBytes / 1024).toFixed(1)} KB`;
      else sizes[ring] = `${(totalBytes / (1024 * 1024)).toFixed(1)} MB`;
    });
    return sizes;
  }, [memoryEntries]);

  const displayedEntries = useMemo(() => {
    if (selectedRing === null) return [];
    // Ring 3 uses semantic search simulation
    if (selectedRing === 3 && searchQuery.trim()) {
      const baseEntries = memoryEntries.filter((e) => e.ring === 3);
      return semanticSearch(baseEntries, searchQuery);
    }
    return queryMemory(selectedRing, searchQuery || undefined);
  }, [selectedRing, searchQuery, queryMemory, memoryEntries]);

  const handleRingClick = (ring: number) => {
    setSelectedRing(ring);
    setSearchQuery('');
    setShowAddForm(false);
  };

  const handleBack = () => {
    setSelectedRing(null);
    setSearchQuery('');
    setShowAddForm(false);
  };

  const handleAddEntry = () => {
    if (!selectedRing || !newEntry.key.trim() || !newEntry.value.trim()) return;
    addMemoryEntry({
      id: `mem_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      ring: selectedRing,
      key: newEntry.key.trim(),
      value: newEntry.value.trim(),
      timestamp: new Date().toISOString(),
      tags: newEntry.tags ? newEntry.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
    });
    setNewEntry({ key: '', value: '', tags: '' });
    setShowAddForm(false);
  };

  const handleClearRing = () => {
    if (selectedRing) {
      clearMemoryRing(selectedRing);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Brain className="h-3.5 w-3.5 text-pink-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Memory Explorer</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-pink-500/30 text-pink-300 font-mono">
              {memoryEntries.length} entries
            </Badge>
          </div>
          {selectedRing !== null && (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1.5 text-[9px] text-pink-400/70 hover:text-pink-300"
                onClick={() => setShowAddForm(!showAddForm)}
              >
                <Plus className="h-3 w-3 mr-0.5" />
                Add
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1.5 text-[9px] text-red-400/70 hover:text-red-300"
                onClick={handleClearRing}
              >
                <Trash2 className="h-3 w-3 mr-0.5" />
                Clear
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1.5 text-[9px] text-slate-500 hover:text-cyan-400"
                onClick={handleBack}
              >
                <ArrowLeft className="h-3 w-3 mr-1" />
                Rings
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2">
        {selectedRing === null ? (
          /* Ring Selection View */
          <>
            {MEMORY_RINGS.map((ring) => {
              const styles = RING_STYLES[ring.ring];
              const count = ringCounts[ring.ring] || 0;
              const size = ringSizes[ring.ring] || '0 B';
              return (
                <Card
                  key={ring.ring}
                  className="bg-slate-800/40 border-slate-700/20 backdrop-blur-sm cursor-pointer hover:border-slate-600/50 transition-all duration-200"
                  onClick={() => handleRingClick(ring.ring)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="h-10 w-10 rounded-xl flex items-center justify-center text-sm font-bold border-2 flex-shrink-0"
                        style={{
                          borderColor: styles.accent,
                          color: styles.accent,
                          backgroundColor: styles.bg,
                          boxShadow: `0 0 12px ${styles.glow}`,
                        }}
                      >
                        R{ring.ring}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-semibold" style={{ color: styles.accent }}>
                            {ring.label}
                          </p>
                          <div className="flex items-center gap-1.5">
                            <Badge
                              variant="outline"
                              className="text-[9px] px-1.5 py-0 h-4 font-mono"
                              style={{
                                borderColor: styles.border,
                                color: styles.accent,
                                backgroundColor: styles.bg,
                              }}
                            >
                              {count} entries
                            </Badge>
                            <Badge
                              variant="outline"
                              className="text-[8px] px-1 py-0 h-3.5 font-mono border-slate-700/30 text-slate-500"
                            >
                              {size}
                            </Badge>
                          </div>
                        </div>
                        <p className="text-[9px] text-slate-500 mt-0.5">{ring.description}</p>
                        {ring.ring === 3 && (
                          <div className="flex items-center gap-0.5 mt-0.5">
                            <Sparkles className="h-2.5 w-2.5 text-pink-400/60" />
                            <span className="text-[8px] text-pink-400/60 font-mono">Semantic search enabled</span>
                          </div>
                        )}
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-600 flex-shrink-0" />
                    </div>
                  </CardContent>
                </Card>
              );
            })}

            {memoryEntries.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8 text-slate-500">
                <Database className="h-8 w-8 text-slate-600/50 mb-2" />
                <p className="text-[10px] text-center text-slate-600">
                  Memory rings are empty.<br />
                  Entries will populate during contract execution.
                </p>
              </div>
            )}
          </>
        ) : (
          /* Ring Detail View */
          <>
            {/* Ring Header */}
            <Card className="bg-slate-800/40 border-slate-700/20 backdrop-blur-sm">
              <CardContent className="p-2.5">
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="h-7 w-7 rounded-lg flex items-center justify-center text-xs font-bold border-2"
                    style={{
                      borderColor: RING_STYLES[selectedRing].accent,
                      color: RING_STYLES[selectedRing].accent,
                      backgroundColor: RING_STYLES[selectedRing].bg,
                    }}
                  >
                    R{selectedRing}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-semibold" style={{ color: RING_STYLES[selectedRing].accent }}>
                      {MEMORY_RINGS.find((r) => r.ring === selectedRing)?.label}
                    </p>
                    <div className="flex items-center gap-2">
                      <p className="text-[9px] text-slate-500">
                        {displayedEntries.length} entries found
                      </p>
                      <p className="text-[8px] text-slate-600 font-mono">
                        {ringSizes[selectedRing]}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="relative">
                  {selectedRing === 3 ? (
                    <Sparkles className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2 text-pink-400/60" />
                  ) : (
                    <Search className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2 text-slate-600" />
                  )}
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={selectedRing === 3 ? 'Semantic search (keyword relevance)...' : 'Search entries...'}
                    className="h-6 text-[10px] pl-7 bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Add Entry Form */}
            {showAddForm && (
              <Card className="bg-slate-800/60 border-slate-600/30 backdrop-blur-sm">
                <CardContent className="p-2.5 space-y-1.5">
                  <p className="text-[9px] font-mono text-pink-300 uppercase">New Entry</p>
                  <Input
                    value={newEntry.key}
                    onChange={(e) => setNewEntry({ ...newEntry, key: e.target.value })}
                    placeholder="Key..."
                    className="h-5 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
                  />
                  <Input
                    value={newEntry.value}
                    onChange={(e) => setNewEntry({ ...newEntry, value: e.target.value })}
                    placeholder="Value..."
                    className="h-5 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
                  />
                  <Input
                    value={newEntry.tags}
                    onChange={(e) => setNewEntry({ ...newEntry, tags: e.target.value })}
                    placeholder="Tags (comma-separated)..."
                    className="h-5 text-[10px] bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
                  />
                  <div className="flex gap-1.5">
                    <Button
                      size="sm"
                      className="h-5 px-2 text-[9px] bg-pink-600/30 hover:bg-pink-600/50 text-pink-200 border-pink-500/30"
                      onClick={handleAddEntry}
                    >
                      <Plus className="h-2.5 w-2.5 mr-0.5" />
                      Add Entry
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 px-2 text-[9px] text-slate-500"
                      onClick={() => { setShowAddForm(false); setNewEntry({ key: '', value: '', tags: '' }); }}
                    >
                      Cancel
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Entries */}
            {displayedEntries.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-[10px] text-slate-500">No entries found</p>
                {searchQuery && (
                  <p className="text-[9px] text-slate-600 mt-1">Try a different search query</p>
                )}
              </div>
            ) : (
              <div className="space-y-1.5">
                {displayedEntries.map((entry: MemoryEntry & { relevance?: number }) => (
                  <EntryCard key={entry.id} entry={entry} ringStyle={RING_STYLES[selectedRing]} showRelevance={selectedRing === 3 && !!searchQuery.trim()} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function EntryCard({ entry, ringStyle, showRelevance }: { entry: MemoryEntry & { relevance?: number }; ringStyle: { accent: string; border: string; bg: string; glow: string }; showRelevance?: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className="bg-slate-800/30 border-slate-700/15 backdrop-blur-sm cursor-pointer hover:border-slate-600/40 transition-all duration-200"
      onClick={() => setExpanded(!expanded)}
    >
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <div
            className="h-1.5 w-1.5 rounded-full mt-1.5 flex-shrink-0"
            style={{ backgroundColor: ringStyle.accent, boxShadow: `0 0 4px ${ringStyle.glow}` }}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-[10px] font-mono font-semibold text-slate-300 truncate">
                {entry.key}
              </span>
              {showRelevance && entry.relevance !== undefined && (
                <Badge
                  variant="outline"
                  className="text-[9px] px-0.5 py-0 h-3 border-pink-500/30 text-pink-300 font-mono"
                >
                  {(entry.relevance * 100).toFixed(0)}% match
                </Badge>
              )}
              {entry.tags && entry.tags.length > 0 && (
                <div className="flex gap-0.5">
                  {entry.tags.slice(0, 2).map((tag, i) => (
                    <Badge key={i} variant="outline" className="text-[9px] px-0.5 py-0 h-3 border-slate-700/50 text-slate-500">
                      {tag}
                    </Badge>
                  ))}
                  {entry.tags.length > 2 && (
                    <span className="text-[9px] text-slate-600">+{entry.tags.length - 2}</span>
                  )}
                </div>
              )}
            </div>
            <p className="text-[9px] text-slate-400 break-words">
              {expanded ? entry.value : entry.value.length > 80 ? `${entry.value.substring(0, 80)}...` : entry.value}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex items-center gap-0.5">
                <Clock className="h-2.5 w-2.5 text-slate-600" />
                <span className="text-[8px] text-slate-600 font-mono">
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                </span>
              </div>
              {entry.access_count !== undefined && (
                <div className="flex items-center gap-0.5">
                  <Eye className="h-2.5 w-2.5 text-slate-600" />
                  <span className="text-[8px] text-slate-600 font-mono">{entry.access_count}</span>
                </div>
              )}
              {entry.session_id && (
                <div className="flex items-center gap-0.5">
                  <Hash className="h-2.5 w-2.5 text-slate-600" />
                  <span className="text-[8px] text-slate-600 font-mono truncate max-w-[60px]">{entry.session_id}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
