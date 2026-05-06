'use client';

import React, { useState, useCallback } from 'react';
import type { EntryType } from '@/lib/kantorku/types';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  BookOpen,
  Lightbulb,
  MessageSquare,
  Wrench,
  Upload,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Loader2,
} from 'lucide-react';

const ENTRY_TYPE_OPTIONS: Array<{ value: EntryType; label: string; icon: React.ReactNode; color: string }> = [
  { value: 'knowledge', label: 'Knowledge', icon: <BookOpen className="h-3.5 w-3.5" />, color: 'text-cyan-400' },
  { value: 'solution', label: 'Solution', icon: <Lightbulb className="h-3.5 w-3.5" />, color: 'text-amber-400' },
  { value: 'qa_pair', label: 'Q&A Pair', icon: <MessageSquare className="h-3.5 w-3.5" />, color: 'text-teal-400' },
  { value: 'procedure', label: 'Procedure', icon: <Wrench className="h-3.5 w-3.5" />, color: 'text-green-400' },
];

export function Ingest() {
  const { libraryIngesting, setLibraryIngesting, addLibraryEntry } = useKantorkuStore();
  const t = useTranslations().t;

  const [phase, setPhase] = useState<1 | 2>(1);
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const [userHint, setUserHint] = useState('');

  // Phase 2 classification
  const [classification, setClassification] = useState<{
    entry_type: EntryType;
    keywords: string[];
    shelf_path: string[];
    quality_initial: number;
    domain: string;
    shelf_confidence: number;
    summary: string;
  } | null>(null);

  const [progress, setProgress] = useState(0);

  const handleAnalyze = useCallback(async () => {
    if (!content.trim()) return;
    setLibraryIngesting(true);
    setProgress(10);

    try {
      setProgress(30);
      // Call ingest API which will classify
      const resp = await fetch('/api/library', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, title, source: 'manual', user_hint: userHint }),
      });

      setProgress(70);

      if (resp.ok) {
        const data = await resp.json();
        if (data.classification) {
          setClassification(data.classification);
        } else {
          // Fallback classification
          setClassification({
            entry_type: 'knowledge',
            keywords: [],
            shelf_path: [],
            quality_initial: 0.5,
            domain: 'web_text',
            shelf_confidence: 0.3,
            summary: content.substring(0, 200),
          });
        }
        setProgress(100);
        setPhase(2);
      }
    } catch {
      // Handle error silently
    } finally {
      setLibraryIngesting(false);
      setProgress(0);
    }
  }, [content, title, userHint, setLibraryIngesting]);

  const handleSave = useCallback(async () => {
    if (!classification) return;
    setLibraryIngesting(true);

    try {
      const resp = await fetch('/api/library', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content,
          title,
          source: 'manual',
          user_hint: userHint,
          classification,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.entry) {
          addLibraryEntry(data.entry);
        }
        // Reset form
        setContent('');
        setTitle('');
        setUserHint('');
        setClassification(null);
        setPhase(1);
      }
    } catch {
      // Handle error
    } finally {
      setLibraryIngesting(false);
    }
  }, [content, title, userHint, classification, addLibraryEntry, setLibraryIngesting]);

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Phase indicator */}
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-1 ${phase === 1 ? 'text-cyan-400' : 'text-slate-500'}`}>
              <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[9px] font-mono ${phase === 1 ? 'bg-cyan-500/20 border border-cyan-500/40' : 'bg-slate-800 border border-slate-700'}`}>
                1
              </div>
              <span className="text-[10px] font-mono">{t('library.phaseInput')}</span>
            </div>
            <ArrowRight className="h-3 w-3 text-slate-700" />
            <div className={`flex items-center gap-1 ${phase === 2 ? 'text-cyan-400' : 'text-slate-500'}`}>
              <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[9px] font-mono ${phase === 2 ? 'bg-cyan-500/20 border border-cyan-500/40' : 'bg-slate-800 border border-slate-700'}`}>
                2
              </div>
              <span className="text-[10px] font-mono">{t('library.phaseReview')}</span>
            </div>
          </div>

          {phase === 1 ? (
            /* Phase 1: Input */
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] text-slate-400 font-mono uppercase">
                  {t('library.title')}
                </Label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={t('library.titlePlaceholder')}
                  className="text-xs bg-slate-900/50 border-slate-700/50"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-[10px] text-slate-400 font-mono uppercase">
                  {t('library.content')}
                </Label>
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={t('library.contentPlaceholder')}
                  className="min-h-[200px] text-xs bg-slate-900/50 border-slate-700/50 font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-[10px] text-slate-400 font-mono uppercase">
                  {t('library.hint')}
                </Label>
                <Input
                  value={userHint}
                  onChange={(e) => setUserHint(e.target.value)}
                  placeholder={t('library.hintPlaceholder')}
                  className="text-xs bg-slate-900/50 border-slate-700/50"
                />
              </div>

              {progress > 0 && (
                <Progress value={progress} className="h-1" />
              )}

              <Button
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-white"
                onClick={handleAnalyze}
                disabled={!content.trim() || libraryIngesting}
              >
                {libraryIngesting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                    {t('library.analyzing')}
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5 mr-2" />
                    {t('library.analyze')}
                  </>
                )}
              </Button>
            </div>
          ) : (
            /* Phase 2: Review */
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] text-slate-400 font-mono uppercase">
                  {t('library.entryType')}
                </Label>
                <Select
                  value={classification?.entry_type || 'knowledge'}
                  onValueChange={(val) =>
                    classification &&
                    setClassification({ ...classification, entry_type: val as EntryType })
                  }
                >
                  <SelectTrigger className="text-xs bg-slate-900/50 border-slate-700/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ENTRY_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        <div className="flex items-center gap-1.5">
                          <span className={opt.color}>{opt.icon}</span>
                          {opt.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-[10px] text-slate-400 font-mono uppercase">
                  {t('library.keywords')}
                </Label>
                <div className="flex flex-wrap gap-1">
                  {classification?.keywords.map((kw, i) => (
                    <Badge key={i} variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-[10px] text-slate-400 font-mono uppercase">
                  {t('library.shelfPath')}
                </Label>
                <div className="text-xs text-slate-300 font-mono">
                  {classification?.shelf_path.join(' / ') || t('library.uncategorized')}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-[9px] text-slate-500 font-mono uppercase">Domain</Label>
                  <div className="text-[10px] text-slate-300 font-mono">{classification?.domain || '—'}</div>
                </div>
                <div className="space-y-1">
                  <Label className="text-[9px] text-slate-500 font-mono uppercase">Quality</Label>
                  <div className="text-[10px] text-slate-300 font-mono">{(classification?.quality_initial || 0).toFixed(2)}</div>
                </div>
                <div className="space-y-1">
                  <Label className="text-[9px] text-slate-500 font-mono uppercase">Confidence</Label>
                  <div className="text-[10px] text-slate-300 font-mono">{(classification?.shelf_confidence || 0).toFixed(2)}</div>
                </div>
              </div>

              {classification?.summary && (
                <div className="space-y-1.5">
                  <Label className="text-[10px] text-slate-400 font-mono uppercase">
                    {t('library.summary')}
                  </Label>
                  <p className="text-xs text-slate-400 bg-slate-900/40 rounded p-2">
                    {classification.summary}
                  </p>
                </div>
              )}

              <div className="flex items-center gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1 text-xs border-slate-700/50 text-slate-400"
                  onClick={() => setPhase(1)}
                >
                  <ArrowLeft className="h-3 w-3 mr-1" />
                  {t('common.back')}
                </Button>
                <Button
                  className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white text-xs"
                  onClick={handleSave}
                  disabled={libraryIngesting}
                >
                  {libraryIngesting ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle className="h-3.5 w-3.5 mr-1" />
                  )}
                  {t('library.save')}
                </Button>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
