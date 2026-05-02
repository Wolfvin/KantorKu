'use client';

import { useRef, useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Send, Loader2, User, Bot } from 'lucide-react';
import { MESSAGE_TYPE_COLORS, MESSAGE_TYPE_ICONS } from '@/lib/kantorku/workers-data';
import { WORKERS } from '@/lib/kantorku/workers-data';
import { ClientChatMessage, WorkersChatMessage } from '@/lib/kantorku/types';

// ── Client Chat Panel ────────────────────────────────────────────
interface ClientChatPanelProps {
  messages: ClientChatMessage[];
  onSend: (message: string) => void;
  isThinking: boolean;
  disabled?: boolean;
}

export function ClientChatPanel({
  messages,
  onSend,
  isThinking,
  disabled,
}: ClientChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [input, setInput] = useState('');

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || isThinking || disabled) return;
    onSend(msg);
    setInput('');
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
            <Bot className="h-8 w-8 text-cyan-500/30" />
            <p className="text-center">
              Start a conversation with the Manager.
              <br />
              <span className="text-slate-600">Describe what you need built.</span>
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'manager' && (
              <div className="flex-shrink-0 h-6 w-6 rounded-full bg-cyan-500/20 flex items-center justify-center mt-0.5">
                <Bot className="h-3.5 w-3.5 text-cyan-400" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600/30 text-slate-200 border border-indigo-500/20'
                  : msg.source === 'team_feedback'
                  ? 'bg-amber-500/10 text-amber-200 border border-amber-500/20'
                  : 'bg-slate-800/80 text-slate-300 border border-slate-700/30'
              }`}
            >
              {msg.source === 'team_feedback' && (
                <span className="text-[9px] text-amber-400 font-mono block mb-1">
                  🏷️ TEAM FEEDBACK
                </span>
              )}
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="flex-shrink-0 h-6 w-6 rounded-full bg-indigo-500/20 flex items-center justify-center mt-0.5">
                <User className="h-3.5 w-3.5 text-indigo-400" />
              </div>
            )}
          </div>
        ))}
        {isThinking && (
          <div className="flex gap-2 justify-start">
            <div className="flex-shrink-0 h-6 w-6 rounded-full bg-cyan-500/20 flex items-center justify-center">
              <Bot className="h-3.5 w-3.5 text-cyan-400" />
            </div>
            <div className="bg-slate-800/80 border border-cyan-500/20 rounded-lg px-3 py-2 flex items-center gap-2">
              <Loader2 className="h-3 w-3 text-cyan-400 animate-spin" />
              <span className="text-xs text-cyan-400">Manager is thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex-shrink-0 p-2 border-t border-slate-700/50">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-1.5"
        >
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your project..."
            disabled={isThinking || disabled}
            className="bg-slate-800/60 border-slate-700/50 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/50"
          />
          <Button
            type="submit"
            size="sm"
            disabled={isThinking || !input.trim() || disabled}
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-3"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>
    </div>
  );
}

// ── Workers Chat Panel ───────────────────────────────────────────
interface WorkersChatPanelProps {
  messages: WorkersChatMessage[];
}

export function WorkersChatPanel({ messages }: WorkersChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getWorkerInfo = (id: string) => {
    if (id === 'conductor') return { emoji: '👔', color: '#06b6d4' };
    const w = WORKERS.find((w) => w.id === id);
    return { emoji: w?.emoji || '🤖', color: w?.color || '#94a3b8' };
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-2">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
          <span className="text-2xl">💬</span>
          <p className="text-center text-slate-600">
            Worker discussions will appear here during execution.
          </p>
        </div>
      )}
      {messages.map((msg) => {
        const worker = getWorkerInfo(msg.from_id);
        const msgColor = MESSAGE_TYPE_COLORS[msg.message_type] || '#94a3b8';
        const msgIcon = MESSAGE_TYPE_ICONS[msg.message_type] || '💬';

        return (
          <div key={msg.id} className="group">
            <div className="flex items-start gap-2">
              <span className="text-sm flex-shrink-0 mt-0.5">{worker.emoji}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span
                    className="text-[10px] font-mono font-semibold"
                    style={{ color: worker.color }}
                  >
                    {msg.from_id}
                  </span>
                  <Badge
                    variant="outline"
                    className="text-[8px] px-1 py-0 h-3.5"
                    style={{
                      borderColor: `${msgColor}40`,
                      color: msgColor,
                      backgroundColor: `${msgColor}10`,
                    }}
                  >
                    {msgIcon} {msg.message_type}
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed break-words">
                  {msg.content}
                </p>
                {msg.reply_to && (
                  <span className="text-[9px] text-slate-600 font-mono">
                    ↩ replying to {msg.reply_to}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
