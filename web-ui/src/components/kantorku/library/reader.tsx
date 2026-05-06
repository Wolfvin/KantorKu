'use client';

import React, { useCallback } from 'react';
import type { LibraryEntry, EvidenceTier } from '@/lib/kantorku/types';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  BookOpen,
  Lightbulb,
  MessageSquare,
  Wrench,
  ThumbsUp,
  ThumbsDown,
  ChevronLeft,
  CheckCircle,
  Eye,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const ENTRY_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  knowledge: { icon: <BookOpen className="h-4 w-4" />, color: 'text-cyan-400', label: 'Knowledge' },
  solution: { icon: <Lightbulb className="h-4 w-4" />, color: 'text-amber-400', label: 'Solution' },
  qa_pair: { icon: <MessageSquare className="h-4 w-4" />, color: 'text-teal-400', label: 'Q&A' },
  procedure: { icon: <Wrench className="h-4 w-4" />, color: 'text-green-400', label: 'Procedure' },
};

const EVIDENCE_TIER_CONFIG: Record<EvidenceTier, { color: string; label: string }> = {
  official: { color: 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10', label: 'Official' },
  vendor: { color: 'border-blue-500/40 text-blue-400 bg-blue-500/10', label: 'Vendor' },
  secondary: { color: 'border-amber-500/40 text-amber-400 bg-amber-500/10', label: 'Secondary' },
  community: { color: 'border-slate-500/40 text-slate-400 bg-slate-500/10', label: 'Community' },
};

function QualityGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8 ? 'bg-green-500' : score >= 0.5 ? 'bg-amber-500' : 'bg-red-500';
  const textColor =
    score >= 0.8 ? 'text-green-400' : score >= 0.5 ? 'text-amber-400' : 'text-red-400';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 max-w-[100px] h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[10px] font-mono ${textColor}`}>{pct}%</span>
    </div>
  );
}

interface ReaderProps {
  entry?: LibraryEntry | null;
  onBack?: () => void;
}

export function Reader({ entry, onBack }: ReaderProps) {
  const { addLibraryAskHistory } = useKantorkuStore();
  const t = useTranslations().t;

  const handleFeedback = useCallback(
    async (type: 'helpful' | 'unhelpful') => {
      if (!entry) return;
      try {
        await fetch('/api/library/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_id: entry.id, feedback_type: type }),
        });
      } catch {
        // Silently handle
      }
    },
    [entry]
  );

  if (!entry) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500">
        <div className="text-center">
          <BookOpen className="h-12 w-12 mx-auto mb-3 text-slate-700" />
          <p className="text-sm font-mono">{t('library.selectEntry')}</p>
        </div>
      </div>
    );
  }

  const typeConfig = ENTRY_TYPE_CONFIG[entry.entry_type] || ENTRY_TYPE_CONFIG.knowledge;

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Back button */}
        {onBack && (
          <Button
            variant="ghost"
            size="sm"
            className="text-[10px] h-6 text-slate-400 hover:text-cyan-400 -ml-2"
            onClick={onBack}
          >
            <ChevronLeft className="h-3 w-3 mr-1" />
            {t('common.back')}
          </Button>
        )}

        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <div className={typeConfig.color}>{typeConfig.icon}</div>
            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-semibold text-slate-200 leading-tight">
                {entry.title || t('library.untitled')}
              </h2>
              <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                <Badge variant="outline" className={`text-[9px] px-1.5 py-0 h-4 ${typeConfig.color}`}>
                  {typeConfig.label}
                </Badge>
                {entry.shelf_path.length > 0 && (
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-slate-700/50 text-slate-500">
                    {entry.shelf_path.join(' / ')}
                  </Badge>
                )}
                {entry.verified && (
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-green-500/40 text-green-400 bg-green-500/10">
                    <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                    Verified
                  </Badge>
                )}
                {entry.evidence_tier && EVIDENCE_TIER_CONFIG[entry.evidence_tier] && (
                  <Badge variant="outline" className={`text-[9px] px-1.5 py-0 h-4 ${EVIDENCE_TIER_CONFIG[entry.evidence_tier].color}`}>
                    {EVIDENCE_TIER_CONFIG[entry.evidence_tier].label}
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {/* Quality gauge */}
          <div className="flex items-center gap-3">
            <span className="text-[9px] text-slate-500 uppercase font-mono">Quality</span>
            <QualityGauge score={entry.quality_score} />
          </div>

          {/* Keywords */}
          {entry.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {entry.keywords.map((kw, i) => (
                <Badge key={i} variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-slate-700/50 text-slate-500">
                  {kw}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <Separator className="bg-slate-800/50" />

        {/* Type-specific sections */}
        {entry.entry_type === 'solution' && entry.problem_description && (
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
              {t('library.problem')}
            </h3>
            <div className="p-3 rounded-md bg-red-500/5 border border-red-500/10 text-xs text-slate-300">
              {entry.problem_description}
            </div>
          </div>
        )}

        {entry.entry_type === 'qa_pair' && entry.question && (
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
              {t('library.question')}
            </h3>
            <div className="p-3 rounded-md bg-teal-500/5 border border-teal-500/10 text-xs text-slate-300">
              {entry.question}
            </div>
          </div>
        )}

        {entry.entry_type === 'procedure' && entry.steps.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
              {t('library.steps')}
            </h3>
            <ol className="space-y-2">
              {entry.steps.map((step, i) => (
                <li key={i} className="flex gap-2">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center text-[9px] text-green-400 font-mono">
                    {step.step || i + 1}
                  </span>
                  <div className="text-xs text-slate-300">
                    <p>{step.action}</p>
                    {step.expected && (
                      <p className="text-[10px] text-slate-500 mt-0.5">→ {step.expected}</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Main content */}
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
            {t('library.content')}
          </h3>
          <div className="prose prose-invert prose-xs max-w-none text-xs text-slate-300">
            <ReactMarkdown>{entry.content}</ReactMarkdown>
          </div>
        </div>

        {/* Solution code */}
        {entry.entry_type === 'solution' && entry.solution_code && (
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
              {t('library.solutionCode')}
            </h3>
            <pre className="p-3 rounded-md bg-slate-900 border border-slate-800 text-[10px] text-slate-300 overflow-x-auto">
              <code>{entry.solution_code}</code>
            </pre>
          </div>
        )}

        {/* QA answer */}
        {entry.entry_type === 'qa_pair' && entry.answer && (
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
              {t('library.answer')}
            </h3>
            <div className="p-3 rounded-md bg-cyan-500/5 border border-cyan-500/10 text-xs text-slate-300">
              <ReactMarkdown>{entry.answer}</ReactMarkdown>
            </div>
          </div>
        )}

        <Separator className="bg-slate-800/50" />

        {/* Feedback */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            className="text-[10px] h-7 border-green-500/30 text-green-400 hover:bg-green-500/10"
            onClick={() => handleFeedback('helpful')}
          >
            <ThumbsUp className="h-3 w-3 mr-1" />
            {entry.was_helpful}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-[10px] h-7 border-red-500/30 text-red-400 hover:bg-red-500/10"
            onClick={() => handleFeedback('unhelpful')}
          >
            <ThumbsDown className="h-3 w-3 mr-1" />
            {entry.was_unhelpful}
          </Button>
          <span className="text-[9px] text-slate-600 font-mono ml-auto">
            <Eye className="h-2.5 w-2.5 inline mr-0.5" />
            {entry.usage_count} {t('library.views')}
          </span>
        </div>

        {/* Related entries */}
        {entry.related_ids.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-mono font-semibold">
              {t('library.related')}
            </h3>
            <div className="space-y-1">
              {entry.related_ids.slice(0, 5).map((id) => (
                <div key={id} className="text-[10px] text-slate-500 font-mono truncate">
                  → {id}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
