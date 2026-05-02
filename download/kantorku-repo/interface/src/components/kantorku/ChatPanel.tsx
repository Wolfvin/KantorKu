'use client';

import { useRef, useEffect, useState, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Send, Loader2, User, Bot, Search, RotateCcw, X } from 'lucide-react';
import { MESSAGE_TYPE_COLORS, MESSAGE_TYPE_ICONS } from '@/lib/kantorku/workers-data';
import { WORKERS } from '@/lib/kantorku/workers-data';
import { ClientChatMessage, WorkersChatMessage, MessageType, InteractiveQuestion } from '@/lib/kantorku/types';

// ── Simple Markdown-like Renderer ───────────────────────────────────
function SimpleMarkdown({ content }: { content: string }) {
  // Split by code blocks
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const code = part.slice(3, -3);
          const firstNewline = code.indexOf('\n');
          const lang = firstNewline > 0 ? code.slice(0, firstNewline).trim() : '';
          const codeBody = firstNewline > 0 ? code.slice(firstNewline + 1) : code;
          return (
            <pre key={i} className="mt-1 mb-1 p-1.5 rounded bg-slate-900/80 border border-slate-700/30 overflow-x-auto">
              {lang && (
                <span className="text-[8px] text-cyan-400 font-mono block mb-0.5">{lang}</span>
              )}
              <code className="text-[10px] text-slate-300 font-mono whitespace-pre-wrap">{codeBody}</code>
            </pre>
          );
        }

        // Process inline formatting
        const lines = part.split('\n');
        return (
          <span key={i}>
            {lines.map((line, j) => {
              // Bold
              let processed = line.replace(
                /\*\*(.*?)\*\*/g,
                '<strong class="text-white font-semibold">$1</strong>'
              );
              // Inline code
              processed = processed.replace(
                /`([^`]+)`/g,
                '<code class="text-[10px] bg-slate-900/60 px-0.5 py-0 rounded text-cyan-300 font-mono">$1</code>'
              );
              // Bullet points
              if (processed.startsWith('- ') || processed.startsWith('• ')) {
                processed = '<span class="text-cyan-400 mr-1">•</span>' + processed.slice(2);
              }

              return (
                <span key={j}>
                  <span dangerouslySetInnerHTML={{ __html: processed }} />
                  {j < lines.length - 1 && <br />}
                </span>
              );
            })}
          </span>
        );
      })}
    </>
  );
}

// ── Typing Indicator ────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-cyan-400"
          style={{
            animation: `typingBounce 1.4s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

// ── Interactive Question Options ─────────────────────────────────────
function InteractiveQuestionCard({
  question,
  messageId,
  onAnswer,
}: {
  question: InteractiveQuestion;
  messageId: string;
  onAnswer: (messageId: string, selectedOption: string, customAnswer?: string) => void;
}) {
  const [showOther, setShowOther] = useState(false);
  const [otherText, setOtherText] = useState('');
  const isAnswered = question.answered;
  const selectedOption = question.selected_option;

  const handleSelect = (label: string, text: string) => {
    if (isAnswered) return;
    onAnswer(messageId, label, text);
    setShowOther(false);
  };

  const handleOtherSubmit = () => {
    if (!otherText.trim() || isAnswered) return;
    onAnswer(messageId, 'OTHER', otherText.trim());
    setOtherText('');
  };

  return (
    <div className="mt-2 p-2 rounded-lg bg-cyan-500/5 border border-cyan-500/20 space-y-1.5">
      <div className="flex items-start gap-1.5">
        <span className="text-xs mt-0.5">❓</span>
        <p className="text-[11px] text-cyan-200 font-medium leading-relaxed">{question.question}</p>
      </div>
      <div className="space-y-1">
        {question.options.map((opt) => {
          const isSelected = selectedOption === opt.label;
          return (
            <button
              key={opt.label}
              onClick={() => handleSelect(opt.label, opt.text)}
              disabled={isAnswered}
              className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left text-[11px] transition-all duration-150
                ${isAnswered
                  ? isSelected
                    ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-200'
                    : 'bg-slate-800/30 border border-slate-700/20 text-slate-500'
                  : 'bg-slate-800/60 border border-slate-700/40 text-slate-200 hover:bg-cyan-500/15 hover:border-cyan-500/30 hover:text-cyan-100 cursor-pointer active:scale-[0.98]'}`}
            >
              <span className={`flex-shrink-0 h-5 w-5 rounded flex items-center justify-center text-[9px] font-bold font-mono
                ${isAnswered
                  ? isSelected
                    ? 'bg-cyan-500/30 text-cyan-300'
                    : 'bg-slate-700/40 text-slate-600'
                  : 'bg-slate-700/60 text-slate-400'}`}>
                {opt.label}
              </span>
              <span className="truncate">{opt.text}</span>
              {isSelected && <span className="ml-auto text-cyan-400 text-[9px]">✓</span>}
            </button>
          );
        })}
      </div>
      {/* Other option */}
      {!isAnswered && question.allow_other && (
        <>
          {!showOther ? (
            <button
              onClick={() => setShowOther(true)}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left text-[11px] bg-slate-800/40 border border-slate-700/30 border-dashed text-slate-400 hover:bg-slate-800/60 hover:border-cyan-500/30 hover:text-cyan-300 cursor-pointer transition-all duration-150"
            >
              <span className="flex-shrink-0 h-5 w-5 rounded flex items-center justify-center text-[9px] font-bold font-mono bg-slate-700/40 text-slate-500">
                ✎
              </span>
              <span>Other (type your answer)</span>
            </button>
          ) : (
            <div className="flex items-center gap-1.5">
              <Input
                value={otherText}
                onChange={(e) => setOtherText(e.target.value)}
                placeholder="Type your answer..."
                className="bg-slate-800/60 border-cyan-500/30 text-[11px] text-slate-200 placeholder:text-slate-600 h-7 px-2 focus:border-cyan-400"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleOtherSubmit();
                }}
              />
              <Button
                onClick={handleOtherSubmit}
                disabled={!otherText.trim()}
                size="sm"
                className="bg-cyan-600 hover:bg-cyan-500 text-white px-2 h-7"
              >
                <Send className="h-3 w-3" />
              </Button>
            </div>
          )}
        </>
      )}
      {/* Show selected answer after answering */}
      {isAnswered && selectedOption && (
        <div className="text-[9px] text-cyan-400/60 font-mono pt-0.5 border-t border-cyan-500/10">
          You selected: {selectedOption === 'OTHER' ? question.custom_answer : `${selectedOption} — ${question.options.find(o => o.label === selectedOption)?.text}`}
        </div>
      )}
    </div>
  );
}

// ── Client Chat Panel ───────────────────────────────────────────────
interface ClientChatPanelProps {
  messages: ClientChatMessage[];
  onSend: (message: string) => void;
  isThinking: boolean;
  disabled?: boolean;
  onNewSession?: () => void;
  onAnswerQuestion?: (messageId: string, selectedOption: string, customAnswer?: string) => void;
}

export function ClientChatPanel({
  messages,
  onSend,
  isThinking,
  disabled,
  onNewSession,
  onAnswerQuestion,
}: ClientChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [input, setInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || isThinking || disabled) return;
    onSend(msg);
    setInput('');
    inputRef.current?.focus();
  };

  // Filter messages by search query
  const filteredMessages = useMemo(() => {
    if (!searchQuery.trim()) return messages;
    const q = searchQuery.toLowerCase();
    return messages.filter((m) => m.content.toLowerCase().includes(q));
  }, [messages, searchQuery]);

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Search Bar */}
      {showSearch && (
        <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40">
          <div className="flex items-center gap-1.5">
            <Search className="h-3 w-3 text-slate-500 flex-shrink-0" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search messages..."
              className="bg-slate-800/60 border-slate-700/50 text-[10px] text-slate-200 placeholder:text-slate-600 h-6 px-2 focus:border-cyan-500/50"
              autoFocus
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setShowSearch(false);
              }}
              className="h-6 w-6 p-0 text-slate-500 hover:text-slate-300"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
          {searchQuery && (
            <p className="text-[8px] text-slate-600 mt-0.5">
              {filteredMessages.length} of {messages.length} messages
            </p>
          )}
        </div>
      )}

      {/* Messages Area */}
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
        {filteredMessages.map((msg) => (
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
              <SimpleMarkdown content={msg.content} />
              {/* Interactive Question Options */}
              {msg.question && onAnswerQuestion && (
                <InteractiveQuestionCard
                  question={msg.question}
                  messageId={msg.id}
                  onAnswer={onAnswerQuestion}
                />
              )}
              <div className="mt-1 text-right">
                <span className="text-[8px] text-slate-600 font-mono">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
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
            <div className="bg-slate-800/80 border border-cyan-500/20 rounded-lg px-3 py-2.5 flex items-center gap-2">
              <TypingIndicator />
              <span className="text-[10px] text-cyan-400 ml-1">thinking</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-2 border-t border-slate-700/50">
        <div className="flex items-center gap-1 mb-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSearch(!showSearch)}
            className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400"
            title="Search messages"
          >
            <Search className="h-3 w-3" />
          </Button>
          {onNewSession && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onNewSession}
              className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400"
              title="New session"
            >
              <RotateCcw className="h-3 w-3" />
            </Button>
          )}
        </div>
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

// ── Workers Chat Panel ──────────────────────────────────────────────
interface WorkersChatPanelProps {
  messages: WorkersChatMessage[];
}

export function WorkersChatPanel({ messages }: WorkersChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [replyTo, setReplyTo] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getWorkerInfo = (id: string) => {
    if (id === 'conductor') return { emoji: '👔', color: '#06b6d4', squad: 'management' };
    const w = WORKERS.find((wk) => wk.id === id);
    return {
      emoji: w?.emoji || '🤖',
      color: w?.color || '#94a3b8',
      squad: w?.squad || 'unknown',
    };
  };

  const filteredMessages = useMemo(() => {
    if (filterType === 'all') return messages;
    return messages.filter((m) => m.message_type === filterType);
  }, [messages, filterType]);

  const messageTypes = useMemo(() => {
    const types = new Set(messages.map((m) => m.message_type));
    return ['all', ...Array.from(types)];
  }, [messages]);

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Filter Dropdown */}
      <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-slate-500 font-mono">FILTER:</span>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="h-5 w-[120px] bg-slate-800/60 border-slate-700/50 text-[9px] text-slate-300 font-mono px-1.5 py-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700/50">
              {messageTypes.map((type) => (
                <SelectItem key={type} value={type} className="text-[9px] font-mono text-slate-300 focus:bg-cyan-500/20 focus:text-cyan-300">
                  {type === 'all' ? 'ALL' : type.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-[8px] text-slate-600 font-mono ml-auto">
            {filteredMessages.length}/{messages.length}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
            <span className="text-2xl">💬</span>
            <p className="text-center text-slate-600">
              Worker discussions will appear here during execution.
            </p>
          </div>
        )}
        {filteredMessages.map((msg) => {
          const worker = getWorkerInfo(msg.from_id);
          const msgColor = MESSAGE_TYPE_COLORS[msg.message_type] || '#94a3b8';
          const msgIcon = MESSAGE_TYPE_ICONS[msg.message_type] || '💬';
          const replyMsg = msg.reply_to ? messages.find((m) => m.id === msg.reply_to) : null;

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
                    <span
                      className="text-[8px] font-mono px-1 py-0 rounded"
                      style={{
                        backgroundColor: `${worker.color}15`,
                        color: worker.color,
                      }}
                    >
                      {worker.squad}
                    </span>
                  </div>

                  {/* Reply-to reference */}
                  {replyMsg && (
                    <div className="mb-0.5 px-1.5 py-0.5 rounded bg-slate-900/60 border-l-2 border-cyan-500/30">
                      <span className="text-[8px] text-slate-500 font-mono">
                        ↩ {replyMsg.from_id}: {replyMsg.content.slice(0, 60)}
                        {replyMsg.content.length > 60 ? '...' : ''}
                      </span>
                    </div>
                  )}

                  <p className="text-[11px] text-slate-300 leading-relaxed break-words">
                    {msg.content}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[8px] text-slate-600 font-mono">
                      {formatTime(msg.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
