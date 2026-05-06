'use client';

import React, { useState, useCallback } from 'react';
import type { LibrarySettings } from '@/lib/kantorku/types';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Settings,
  Database,
  RotateCcw,
  Save,
  Tag,
} from 'lucide-react';

export function SettingsPanel() {
  const { librarySettings, setLibrarySettings } = useKantorkuStore();
  const t = useTranslations().t;
  const [localSettings, setLocalSettings] = useState<LibrarySettings>({ ...librarySettings });
  const [newTaxonomyItem, setNewTaxonomyItem] = useState('');

  const handleSave = useCallback(() => {
    setLibrarySettings(localSettings);
  }, [localSettings, setLibrarySettings]);

  const handleReset = useCallback(() => {
    const defaults: LibrarySettings = {
      embedding_backend: 'memory',
      similarity_threshold: 0.5,
      auto_index: true,
      default_shelf_taxonomy: ['Engineering', 'Mathematics', 'Science', 'Philosophy', 'Business'],
    };
    setLocalSettings(defaults);
    setLibrarySettings(defaults);
  }, [setLibrarySettings]);

  const addTaxonomyItem = useCallback(() => {
    if (newTaxonomyItem.trim() && !localSettings.default_shelf_taxonomy.includes(newTaxonomyItem.trim())) {
      setLocalSettings({
        ...localSettings,
        default_shelf_taxonomy: [...localSettings.default_shelf_taxonomy, newTaxonomyItem.trim()],
      });
      setNewTaxonomyItem('');
    }
  }, [newTaxonomyItem, localSettings]);

  const removeTaxonomyItem = useCallback((item: string) => {
    setLocalSettings({
      ...localSettings,
      default_shelf_taxonomy: localSettings.default_shelf_taxonomy.filter((t) => t !== item),
    });
  }, [localSettings]);

  return (
    <div className="p-4 space-y-5">
      <div className="text-center mb-2">
        <h3 className="text-sm font-mono text-slate-300 flex items-center justify-center gap-1.5">
          <Settings className="h-4 w-4 text-cyan-400" />
          {t('library.settingsTitle')}
        </h3>
      </div>

      {/* Embedding backend */}
      <div className="space-y-2">
        <Label className="text-[10px] text-slate-400 font-mono uppercase">
          <Database className="h-3 w-3 inline mr-1" />
          {t('library.embeddingBackend')}
        </Label>
        <Select
          value={localSettings.embedding_backend}
          onValueChange={(v) =>
            setLocalSettings({ ...localSettings, embedding_backend: v as LibrarySettings['embedding_backend'] })
          }
        >
          <SelectTrigger className="text-xs bg-slate-900/50 border-slate-700/50">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="memory">Memory (In-Memory)</SelectItem>
            <SelectItem value="chromadb">ChromaDB</SelectItem>
            <SelectItem value="faiss">FAISS</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-[9px] text-slate-600">
          {t('library.embeddingDesc')}
        </p>
      </div>

      {/* Similarity threshold */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-[10px] text-slate-400 font-mono uppercase">
            {t('library.similarityThreshold')}
          </Label>
          <span className="text-[10px] text-cyan-400 font-mono">{localSettings.similarity_threshold.toFixed(2)}</span>
        </div>
        <Slider
          value={[localSettings.similarity_threshold]}
          onValueChange={(v) =>
            setLocalSettings({ ...localSettings, similarity_threshold: v[0] })
          }
          min={0}
          max={1}
          step={0.05}
          className="w-full"
        />
        <p className="text-[9px] text-slate-600">
          {t('library.similarityDesc')}
        </p>
      </div>

      {/* Auto-index */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="text-[10px] text-slate-400 font-mono uppercase">
            {t('library.autoIndex')}
          </Label>
          <p className="text-[9px] text-slate-600">
            {t('library.autoIndexDesc')}
          </p>
        </div>
        <Switch
          checked={localSettings.auto_index}
          onCheckedChange={(v) => setLocalSettings({ ...localSettings, auto_index: v })}
        />
      </div>

      {/* Default shelf taxonomy */}
      <div className="space-y-2">
        <Label className="text-[10px] text-slate-400 font-mono uppercase">
          <Tag className="h-3 w-3 inline mr-1" />
          {t('library.shelfTaxonomy')}
        </Label>
        <div className="flex flex-wrap gap-1.5">
          {localSettings.default_shelf_taxonomy.map((item) => (
            <Badge
              key={item}
              variant="outline"
              className="text-[9px] px-2 py-0.5 border-cyan-500/30 text-cyan-300 bg-cyan-500/5 cursor-pointer hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-300 transition-colors"
              onClick={() => removeTaxonomyItem(item)}
            >
              {item} ×
            </Badge>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Input
            value={newTaxonomyItem}
            onChange={(e) => setNewTaxonomyItem(e.target.value)}
            placeholder={t('library.addShelf')}
            className="text-xs bg-slate-900/50 border-slate-700/50 h-7"
            onKeyDown={(e) => {
              if (e.key === 'Enter') addTaxonomyItem();
            }}
          />
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10"
            onClick={addTaxonomyItem}
          >
            +
          </Button>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-2">
        <Button
          variant="outline"
          className="flex-1 text-xs border-slate-700/50 text-slate-400"
          onClick={handleReset}
        >
          <RotateCcw className="h-3 w-3 mr-1" />
          {t('common.reset')}
        </Button>
        <Button
          className="flex-1 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
          onClick={handleSave}
        >
          <Save className="h-3 w-3 mr-1" />
          {t('common.save')}
        </Button>
      </div>
    </div>
  );
}
