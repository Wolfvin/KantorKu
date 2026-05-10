'use client';

import React, { useState, useRef, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Send,
  BookOpen,
  Loader2,
  ExternalLink,
  Sparkles,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'archivist';
  content: string;
  sources?: Array<{
    entry_id: string;
    title: string;
    similarity: number;
    entry_type: string;
  }>;
  confidence?: number;
  timestamp: string;
}

function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const color =
    confidence >= 0.7
      ? 'bg-green-500 text-green-400'
      : confidence >= 0.4
      ? 'bg-amber-500 text-amber-400'
      : 'bg-red-500 text-red-400';
  const label =
    confidence >= 0.7 ? 'High' : confidence >= 0.4 ? 'Medium' : 'Low';

  return (
    <Badge
      variant="outline"
      className={`text-[9px] px-1.5 py-0 h-4 font-mono ${color} border-current/20`}
    >
      {label} ({(confidence * 100).toFixed(0)}%)
    </Badge>
  );
}

export function AskChat() {
  const { libraryAsking, setLibraryAsking, addLibraryAskHistory } = useKantorkuStore();
  const t = useTranslations().t;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [saveToLibrary, setSaveToLibrary] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSend = useCallback(async () => {
    if (!input.trim() || libraryAsking) return;

    const question = input.trim();
    setInput('');
    setLibraryAsking(true);

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const resp = await fetch('/api/library/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          top_k: 5,
          save_to_library: saveToLibrary,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        const archivistMsg: ChatMessage = {
          id: `msg_${Date.now()}_a`,
          role: 'archivist',
          content: data.answer || t('library.noAnswer'),
          sources: data.sources || [],
          confidence: data.confidence || 0,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, archivistMsg]);
        addLibraryAskHistory(question, data);
      } else {
        const errorMsg: ChatMessage = {
          id: `msg_${Date.now()}_e`,
          role: 'archivist',
          content: t('library.askError'),
          confidence: 0,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch {
      const errorMsg: ChatMessage = {
        id: `msg_${Date.now()}_e`,
        role: 'archivist',
        content: t('library.askError'),
        confidence: 0,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLibraryAsking(false);
      // Scroll to bottom
      setTimeout(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
      }, 100);
    }
  }, [input, libraryAsking, saveToLibrary, setLibraryAsking, addLibraryAskHistory, t]);

  return (
    <div className="flex flex-col h-full">
      {/* Chat Messages */}
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="p-3 space-y-3">
          {messages.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              <Sparkles className="h-10 w-10 mx-auto mb-3 text-slate-700" />
              <p className="text-sm font-mono">{t('library.askPlaceholder')}</p>
              <p className="text-[10px] text-slate-600 mt-1">{t('library.askHint')}</p>
            </div>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-xs ${
                  msg.role === 'user'
                    ? 'bg-cyan-500/10 border border-cyan-500/20 text-slate-200'
                    : 'bg-slate-800/60 border border-slate-700/30 text-slate-300'
                }`}
              >
                {msg.role === 'archivist' && (
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <BookOpen className="h-3 w-3 text-cyan-400" />
                    <span className="text-[9px] font-mono text-cyan-400">Archivist</span>
                    {msg.confidence !== undefined && msg.confidence > 0 && (
                      <ConfidenceIndicator confidence={msg.confidence} />
                    )}
                  </div>
                )}
                <div className="whitespace-pre-wrap">{msg.content}</div>
                {/* Source citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-slate-700/30">
                    <p className="text-[9px] text-slate-500 uppercase font-mono mb-1">
                      {t('library.sources')}
                    </p>
                    <div className="space-y-1">
                      {msg.sources.map((src, i) => (
                        <button
                          key={src.entry_id}
                          className="flex items-center gap-1.5 w-full text-left hover:bg-slate-700/30 rounded px-1 py-0.5 transition-colors"
                          onClick={() => {
                            // Could navigate to entry in reader
                          }}
                        >
                          <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-3 border-cyan-500/30 text-cyan-400 bg-cyan-500/5">
                            [{i + 1}]
                          </Badge>
                          <span className="text-[10px] text-slate-400 truncate">
                            {src.title}
                          </span>
                          <span className="text-[9px] text-slate-600 font-mono ml-auto flex-shrink-0">
                            {(src.similarity * 100).toFixed(0)}%
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {libraryAsking && (
            <div className="flex justify-start">
              <div className="bg-slate-800/60 border border-slate-700/30 rounded-lg px-3 py-2 flex items-center gap-2">
                <Loader2 className="h-3 w-3 text-cyan-400 animate-spin" />
                <span className="text-[10px] text-slate-400 font-mono">{t('library.thinking')}</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input bar */}
      <div className="flex-shrink-0 border-t border-slate-800/50 p-3 space-y-2">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <Switch
              id="save-to-library"
              checked={saveToLibrary}
              onCheckedChange={setSaveToLibrary}
              className="scale-75"
            />
            <Label htmlFor="save-to-library" className="text-[9px] text-slate-500 font-mono cursor-pointer">
              {t('library.saveToLibrary')}
            </Label>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={t('library.askInputPlaceholder')}
            className="flex-1 bg-slate-900/50 border border-slate-700/50 rounded-md px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
            disabled={libraryAsking}
          />
          <Button
            size="sm"
            className="h-7 px-3 bg-cyan-600 hover:bg-cyan-500 text-white"
            onClick={handleSend}
            disabled={!input.trim() || libraryAsking}
          >
            <Send className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
