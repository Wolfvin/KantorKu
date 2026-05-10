'use client';

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { MESSAGE_TYPE_COLORS, MESSAGE_TYPE_ICONS } from '@/lib/kantorku/workers-data';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { MessageType, WorkersChatMessage } from '@/lib/kantorku/types';
import { Filter, Search, MessageCircle, ArrowUp, Quote, ListTree, LayoutList } from 'lucide-react';
import { Button } from '@/components/ui/button';

const MESSAGE_TYPE_BADGE_STYLES: Record<string, { border: string; text: string; bg: string }> = {
  speak: { border: '#94a3b840', text: '#94a3b8', bg: '#94a3b810' },
  concern: { border: '#ef444440', text: '#f87171', bg: '#ef444410' },
  suggestion: { border: '#22c55e40', text: '#4ade80', bg: '#22c55e10' },
  question: { border: '#f59e0b40', text: '#fbbf24', bg: '#f59e0b10' },
  info: { border: '#06b6d440', text: '#22d3ee', bg: '#06b6d410' },
  agreement: { border: '#10b98140', text: '#34d399', bg: '#10b98110' },
  disagreement: { border: '#dc262640', text: '#f87171', bg: '#dc262610' },
  manager_summary: { border: '#8b5cf640', text: '#a78bfa', bg: '#8b5cf610' },
  manager_decision: { border: '#ec489940', text: '#f472b6', bg: '#ec489910' },
  response: { border: '#3b82f640', text: '#60a5fa', bg: '#3b82f610' },
  volunteer: { border: '#14b8a640', text: '#2dd4bf', bg: '#14b8a610' },
  escalation: { border: '#ef444440', text: '#f87171', bg: '#ef444410' },
  overhearing: { border: '#94a3b840', text: '#94a3b8', bg: '#94a3b808' },
  delegation_request: { border: '#f59e0b40', text: '#fbbf24', bg: '#f59e0b10' },
  delegation_response: { border: '#22c55e40', text: '#4ade80', bg: '#22c55e10' },
  brainstorm: { border: '#a855f740', text: '#c084fc', bg: '#a855f710' },
  context_switch: { border: '#ec489940', text: '#f472b6', bg: '#ec489910' },
};

const ALL_MESSAGE_TYPES: MessageType[] = [
  'speak', 'concern', 'suggestion', 'question', 'response',
  'agreement', 'disagreement', 'info', 'manager_summary', 'manager_decision',
  'volunteer', 'escalation', 'overhearing', 'delegation_request',
  'delegation_response', 'brainstorm', 'context_switch',
];

export function GroupChannelPanel() {
  const { workersMessages, workers, addWorkersMessage } = useKantorkuStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [filterType, setFilterType] = useState<MessageType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [viewMode, setViewMode] = useState<'flat' | 'threaded'>('flat');
  const [replyingTo, setReplyingTo] = useState<{ id: string; from_id: string; content: string } | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const getWorkerInfo = (id: string) => {
    if (id === 'conductor' || id === 'manager') return { emoji: '👔', color: '#06b6d4', role: 'Manager' };
    const w = workers.find((w) => w.id === id);
    return { emoji: w?.emoji || '🤖', color: w?.color || '#94a3b8', role: w?.role || '' };
  };

  const filteredMessages = useMemo(() => {
    let msgs = workersMessages;
    if (filterType !== 'all') {
      msgs = msgs.filter((m) => m.message_type === filterType);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      msgs = msgs.filter(
        (m) => m.content.toLowerCase().includes(q) || m.from_id.toLowerCase().includes(q)
      );
    }
    return msgs;
  }, [workersMessages, filterType, searchQuery]);

  // Build threaded view: group messages by reply chains
  const threadGroups = useMemo(() => {
    if (viewMode !== 'threaded') return [];
    // Find root messages (no reply_to) and their reply chains
    const msgMap = new Map(workersMessages.map((m) => [m.id, m]));
    const roots: WorkersChatMessage[] = [];
    const replies: Map<string, WorkersChatMessage[]> = new Map();

    workersMessages.forEach((msg) => {
      if (msg.reply_to && msgMap.has(msg.reply_to)) {
        if (!replies.has(msg.reply_to)) replies.set(msg.reply_to, []);
        replies.get(msg.reply_to)!.push(msg);
      } else {
        roots.push(msg);
      }
    });

    return roots.map((root) => ({
      root,
      replies: replies.get(root.id) || [],
    }));
  }, [workersMessages, viewMode]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [filteredMessages.length]);

  // Show scroll-to-bottom button when scrolled up
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 100);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Count messages by type for the filter
  const typeCounts = useMemo(() => {
    const counts: Partial<Record<MessageType, number>> = {};
    workersMessages.forEach((m) => {
      counts[m.message_type] = (counts[m.message_type] || 0) + 1;
    });
    return counts;
  }, [workersMessages]);

  const usedTypes = ALL_MESSAGE_TYPES.filter((t) => (typeCounts[t] || 0) > 0);

  // Handle quote and reply
  const handleQuoteReply = useCallback((msg: WorkersChatMessage) => {
    setReplyingTo({ id: msg.id, from_id: msg.from_id, content: msg.content });
  }, []);

  const handleSendReply = useCallback(() => {
    if (!replyingTo || !replyContent.trim()) return;
    addWorkersMessage({
      id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      from_id: 'client',
      message_type: 'response',
      content: replyContent.trim(),
      timestamp: new Date().toISOString(),
      reply_to: replyingTo.id,
      session_id: '',
    });
    setReplyContent('');
    setReplyingTo(null);
  }, [replyingTo, replyContent, addWorkersMessage]);

  const handleCancelReply = useCallback(() => {
    setReplyingTo(null);
    setReplyContent('');
  }, []);

  // Render a single message
  const renderMessage = (msg: WorkersChatMessage, isReply = false) => {
    const worker = getWorkerInfo(msg.from_id);
    const badgeStyle = MESSAGE_TYPE_BADGE_STYLES[msg.message_type] || MESSAGE_TYPE_BADGE_STYLES.speak;
    const msgIcon = MESSAGE_TYPE_ICONS[msg.message_type] || '💬';

    return (
      <div key={msg.id} className={`group ${isReply ? 'ml-6 border-l border-slate-700/30 pl-2' : ''}`}>
        <div className="flex items-start gap-2">
          <span className={`text-sm flex-shrink-0 ${isReply ? 'mt-0 text-xs' : 'mt-0.5'}`}>{worker.emoji}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span
                className={`${isReply ? 'text-[9px]' : 'text-[10px]'} font-mono font-semibold`}
                style={{ color: worker.color }}
              >
                {msg.from_id}
              </span>
              <Badge
                variant="outline"
                className="text-[8px] px-1 py-0 h-3.5"
                style={{
                  borderColor: badgeStyle.border,
                  color: badgeStyle.text,
                  backgroundColor: badgeStyle.bg,
                }}
              >
                {msgIcon} {msg.message_type}
              </Badge>
              <span className="text-[8px] text-slate-600 font-mono">
                {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
              </span>
            </div>
            <p className={`${isReply ? 'text-[10px]' : 'text-[11px]'} text-slate-300 leading-relaxed break-words`}>
              {msg.content}
            </p>
            {msg.reply_to && (
              <span className="text-[9px] text-slate-600 font-mono mt-0.5 block">
                ↩ replying to {msg.reply_to}
              </span>
            )}
            {/* Quote & Reply button */}
            <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">
              <Button
                variant="ghost"
                size="sm"
                className="h-4 px-1 text-[8px] text-slate-500 hover:text-cyan-400"
                onClick={(e) => {
                  e.stopPropagation();
                  handleQuoteReply(msg);
                }}
              >
                <Quote className="h-2.5 w-2.5 mr-0.5" />
                Quote & Reply
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Header / Filter Bar */}
      <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40 space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <MessageCircle className="h-3 w-3 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Group Channel</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-500 font-mono">
              {filteredMessages.length}/{workersMessages.length}
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            {/* View mode toggle */}
            <Button
              variant="ghost"
              size="sm"
              className={`h-5 w-5 p-0 ${viewMode === 'flat' ? 'text-cyan-400' : 'text-slate-500 hover:text-cyan-400'}`}
              onClick={() => setViewMode('flat')}
              title="Flat view"
            >
              <LayoutList className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-5 w-5 p-0 ${viewMode === 'threaded' ? 'text-cyan-400' : 'text-slate-500 hover:text-cyan-400'}`}
              onClick={() => setViewMode('threaded')}
              title="Threaded view"
            >
              <ListTree className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2 text-slate-600" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search messages..."
            className="h-6 text-[10px] pl-7 bg-slate-800/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
          />
        </div>

        {/* Type Filters + Message count by type */}
        {showFilters && (
          <div className="space-y-1">
            <div className="flex flex-wrap gap-1">
              <Badge
                variant="outline"
                className={`text-[8px] px-1.5 py-0 h-4 cursor-pointer font-mono ${
                  filterType === 'all'
                    ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                    : 'border-slate-600/50 text-slate-500 hover:border-slate-500/50'
                }`}
                onClick={() => setFilterType('all')}
              >
                All
              </Badge>
              {usedTypes.map((type) => {
                const style = MESSAGE_TYPE_BADGE_STYLES[type] || MESSAGE_TYPE_BADGE_STYLES.speak;
                return (
                  <Badge
                    key={type}
                    variant="outline"
                    className={`text-[8px] px-1.5 py-0 h-4 cursor-pointer font-mono ${
                      filterType === type
                        ? ''
                        : 'opacity-60 hover:opacity-100'
                    }`}
                    style={{
                      borderColor: filterType === type ? style.border : `${style.border}60`,
                      color: filterType === type ? style.text : `${style.text}80`,
                      backgroundColor: filterType === type ? style.bg : 'transparent',
                    }}
                    onClick={() => setFilterType(type)}
                  >
                    {MESSAGE_TYPE_ICONS[type] || '💬'} {type} ({typeCounts[type]})
                  </Badge>
                );
              })}
            </div>
            {/* Message count by type indicator bar */}
            {workersMessages.length > 0 && (
              <div className="flex h-1 rounded overflow-hidden bg-slate-800/60">
                {usedTypes.map((type) => {
                  const style = MESSAGE_TYPE_BADGE_STYLES[type] || MESSAGE_TYPE_BADGE_STYLES.speak;
                  const pct = ((typeCounts[type] || 0) / workersMessages.length) * 100;
                  return (
                    <div
                      key={type}
                      className="h-full transition-all duration-300"
                      style={{ width: `${pct}%`, backgroundColor: style.text }}
                      title={`${type}: ${typeCounts[type]} (${pct.toFixed(0)}%)`}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reply bar */}
      {replyingTo && (
        <div className="flex-shrink-0 px-3 py-1.5 border-b border-cyan-500/20 bg-cyan-500/5">
          <div className="flex items-start gap-1.5">
            <Quote className="h-3 w-3 text-cyan-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-[8px] text-cyan-400 font-mono">Replying to {replyingTo.from_id}</p>
              <p className="text-[9px] text-slate-400 truncate">{replyingTo.content}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 mt-1">
            <Input
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Type your reply..."
              className="h-5 text-[10px] bg-slate-800/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
              onKeyDown={(e) => { if (e.key === 'Enter') handleSendReply(); }}
            />
            <Button
              size="sm"
              className="h-5 px-2 text-[8px] bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-200"
              onClick={handleSendReply}
            >
              Send
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1.5 text-[8px] text-slate-500"
              onClick={handleCancelReply}
            >
              ✕
            </Button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2 relative"
        onScroll={handleScroll}
      >
        {workersMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
            <span className="text-2xl">💬</span>
            <p className="text-center text-slate-600">
              Worker discussions will appear here during execution.
            </p>
          </div>
        )}

        {viewMode === 'flat' ? (
          /* Flat view */
          filteredMessages.map((msg) => renderMessage(msg))
        ) : (
          /* Threaded view */
          threadGroups.length > 0 ? (
            <div className="space-y-3">
              {threadGroups.map(({ root, replies }) => (
                <div key={root.id} className="space-y-1">
                  {renderMessage(root)}
                  {replies.length > 0 && (
                    <div className="space-y-1">
                      {replies.map((reply) => renderMessage(reply, true))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : null
        )}
        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom */}
      {showScrollBtn && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute bottom-2 right-4 h-6 w-6 p-0 bg-slate-800/80 border border-slate-700/50 text-cyan-400 hover:text-cyan-300 rounded-full"
          onClick={scrollToBottom}
        >
          <ArrowUp className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
