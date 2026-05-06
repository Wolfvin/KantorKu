'use client';

import React, { useState, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Download,
  FileJson,
  FileText,
  Brain,
  MessageSquare,
  Lightbulb,
  GitCompare,
} from 'lucide-react';

const FORMAT_OPTIONS = [
  { value: 'json', label: 'JSON', icon: <FileJson className="h-3.5 w-3.5" />, desc: 'Raw JSON export' },
  { value: 'markdown', label: 'Markdown', icon: <FileText className="h-3.5 w-3.5" />, desc: 'Markdown documents' },
  { value: 'losion_pretraining', label: 'Lösiön Pretraining', icon: <Brain className="h-3.5 w-3.5" />, desc: 'Training data format' },
  { value: 'rlhf_qa', label: 'RLHF-QA', icon: <MessageSquare className="h-3.5 w-3.5" />, desc: 'RLHF question-answer pairs' },
  { value: 'rlhf_solutions', label: 'RLHF-Solutions', icon: <Lightbulb className="h-3.5 w-3.5" />, desc: 'RLHF solution pairs' },
  { value: 'preference_pairs', label: 'Preference Pairs', icon: <GitCompare className="h-3.5 w-3.5" />, desc: 'Chosen/rejected pairs' },
] as const;

export function ExportDashboard() {
  const { libraryEntries } = useKantorkuStore();
  const t = useTranslations().t;
  const [format, setFormat] = useState<string>('json');
  const [qualityThreshold, setQualityThreshold] = useState(0);

  const exportCount = libraryEntries.filter(
    (e) => e.quality_score >= qualityThreshold
  ).length;

  const handleExport = useCallback(async () => {
    try {
      const resp = await fetch(
        `/api/library/export?format=${format}&quality_threshold=${qualityThreshold}`
      );
      if (resp.ok) {
        const data = await resp.json();
        // Create downloadable file
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: format === 'json' ? 'application/json' : 'text/plain',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `library-export-${format}-${Date.now()}.${format === 'json' ? 'json' : 'md'}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      // Handle error
    }
  }, [format, qualityThreshold]);

  const selectedFormat = FORMAT_OPTIONS.find((f) => f.value === format);

  return (
    <div className="p-4 space-y-4">
      <div className="text-center mb-4">
        <h3 className="text-sm font-mono text-slate-300">{t('library.exportTitle')}</h3>
        <p className="text-[10px] text-slate-500 mt-1">{t('library.exportDesc')}</p>
      </div>

      {/* Format picker */}
      <div className="space-y-2">
        <Label className="text-[10px] text-slate-400 font-mono uppercase">
          {t('library.format')}
        </Label>
        <div className="grid grid-cols-2 gap-2">
          {FORMAT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`p-2.5 rounded-md border text-left transition-colors ${
                format === opt.value
                  ? 'border-cyan-500/40 bg-cyan-500/10'
                  : 'border-slate-800/50 bg-slate-900/30 hover:border-slate-700/50'
              }`}
              onClick={() => setFormat(opt.value)}
            >
              <div className="flex items-center gap-1.5">
                <span className={format === opt.value ? 'text-cyan-400' : 'text-slate-500'}>
                  {opt.icon}
                </span>
                <span className={`text-[10px] font-mono ${format === opt.value ? 'text-cyan-300' : 'text-slate-400'}`}>
                  {opt.label}
                </span>
              </div>
              <p className="text-[9px] text-slate-600 mt-1 ml-5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Quality threshold */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-[10px] text-slate-400 font-mono uppercase">
            {t('library.qualityThreshold')}
          </Label>
          <span className="text-[10px] text-cyan-400 font-mono">{qualityThreshold.toFixed(1)}</span>
        </div>
        <Slider
          value={[qualityThreshold]}
          onValueChange={(v) => setQualityThreshold(v[0])}
          min={0}
          max={1}
          step={0.1}
          className="w-full"
        />
      </div>

      {/* Export preview */}
      <div className="p-3 rounded-md bg-slate-900/40 border border-slate-800/50">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-slate-500 font-mono">{t('library.entriesToExport')}</span>
          <Badge variant="outline" className="text-[10px] px-2 py-0 h-5 border-cyan-500/30 text-cyan-400 bg-cyan-500/10 font-mono">
            {exportCount}
          </Badge>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-slate-600 font-mono">{t('library.format')}</span>
          <span className="text-[10px] text-slate-400 font-mono">{selectedFormat?.label}</span>
        </div>
      </div>

      {/* Download button */}
      <Button
        className="w-full bg-cyan-600 hover:bg-cyan-500 text-white"
        onClick={handleExport}
        disabled={exportCount === 0}
      >
        <Download className="h-3.5 w-3.5 mr-2" />
        {t('library.download')} ({exportCount})
      </Button>
    </div>
  );
}
