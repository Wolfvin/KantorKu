'use client';

import React, { useState, useCallback } from 'react';
import type { ShelfNode } from '@/lib/kantorku/types';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  Folder,
  BookOpen,
} from 'lucide-react';

interface ShelfBrowserProps {
  onShelfSelect?: (path: string[]) => void;
}

function ShelfTreeNode({
  node,
  depth,
  onShelfSelect,
  selectedPath,
}: {
  node: ShelfNode;
  depth: number;
  onShelfSelect: (path: string[]) => void;
  selectedPath: string | null;
}) {
  const [expanded, setExpanded] = useState(depth === 0);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedPath === node.path.join('/');
  const t = useTranslations().t;

  const qualityBadgeColor =
    node.quality_avg >= 0.8
      ? 'border-green-500/40 text-green-300 bg-green-500/10'
      : node.quality_avg >= 0.5
      ? 'border-amber-500/40 text-amber-300 bg-amber-500/10'
      : 'border-slate-600/50 text-slate-400 bg-slate-800/30';

  return (
    <div>
      <button
        className={`w-full flex items-center gap-1.5 py-1.5 px-2 rounded-md text-left transition-colors hover:bg-slate-800/50 ${
          isSelected ? 'bg-cyan-500/10 border-l-2 border-cyan-400' : ''
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          onShelfSelect(node.path);
        }}
        aria-expanded={hasChildren ? expanded : undefined}
        aria-label={`${node.name}, ${node.entry_count} ${t('common.entries')}`}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
          )
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        {hasChildren ? (
          expanded ? (
            <FolderOpen className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
          ) : (
            <Folder className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
          )
        ) : (
          <BookOpen className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
        )}
        <span className="text-xs font-mono text-slate-300 truncate flex-1">
          {node.name}
        </span>
        <Badge
          variant="outline"
          className="text-[9px] px-1 py-0 h-4 font-mono border-slate-700/50 text-slate-500 flex-shrink-0"
        >
          {node.entry_count}
        </Badge>
        {node.quality_avg > 0 && (
          <Badge
            variant="outline"
            className={`text-[9px] px-1 py-0 h-4 font-mono ${qualityBadgeColor} flex-shrink-0`}
          >
            {node.quality_avg.toFixed(1)}
          </Badge>
        )}
      </button>
      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <ShelfTreeNode
              key={child.path.join('/')}
              node={child}
              depth={depth + 1}
              onShelfSelect={onShelfSelect}
              selectedPath={selectedPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ShelfBrowser({ onShelfSelect }: ShelfBrowserProps) {
  const { libraryShelves } = useKantorkuStore();
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const t = useTranslations().t;

  // Build breadcrumb from selected path
  const breadcrumb = selectedPath ? selectedPath.split('/') : [];

  const handleShelfSelect = useCallback(
    (path: string[]) => {
      setSelectedPath(path.join('/'));
      onShelfSelect?.(path);
    },
    [onShelfSelect]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb */}
      {breadcrumb.length > 0 && (
        <div className="flex items-center gap-1 px-3 py-2 border-b border-slate-800/50 bg-slate-900/30">
          <Button
            variant="ghost"
            size="sm"
            className="text-[10px] h-5 px-1 text-slate-500 hover:text-cyan-400"
            onClick={() => {
              setSelectedPath(null);
              onShelfSelect?.([]);
            }}
          >
            {t('library.allShelves')}
          </Button>
          {breadcrumb.map((seg, i) => (
            <React.Fragment key={i}>
              <ChevronRight className="h-2.5 w-2.5 text-slate-600" />
              <Button
                variant="ghost"
                size="sm"
                className="text-[10px] h-5 px-1 text-slate-400 hover:text-cyan-400"
                onClick={() => {
                  const path = breadcrumb.slice(0, i + 1);
                  setSelectedPath(path.join('/'));
                  onShelfSelect?.(path);
                }}
              >
                {seg}
              </Button>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Shelf Tree */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-0.5">
          {libraryShelves.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs font-mono">
              <Folder className="h-8 w-8 mx-auto mb-2 text-slate-700" />
              <p>{t('library.noShelves')}</p>
            </div>
          ) : (
            libraryShelves.map((shelf) => (
              <ShelfTreeNode
                key={shelf.path.join('/')}
                node={shelf}
                depth={0}
                onShelfSelect={handleShelfSelect}
                selectedPath={selectedPath}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
