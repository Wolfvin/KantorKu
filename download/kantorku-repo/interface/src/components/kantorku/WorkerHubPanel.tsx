'use client';

import { useState, useMemo, useCallback } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { WORKERS } from '@/lib/kantorku/workers-data';
import {
  MessageSquare, Send, Radio, HelpCircle, AlertTriangle,
  Users, ChevronDown, ChevronRight, Search,
} from 'lucide-react';

type DMMessageType = 'dm' | 'broadcast' | 'help_request' | 'response';

interface DMMessage {
  id: string;
  from_id: string;
  to_id: string | 'all';
  type: DMMessageType;
  content: string;
  timestamp: string;
  isEscalation?: boolean;
}

export function WorkerHubPanel() {
  const { workers, contract } = useKantorkuStore();
  const [selectedWorker, setSelectedWorker] = useState<string | null>(null);
  const [messages, setMessages] = useState<DMMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [msgType, setMsgType] = useState<DMMessageType>('dm');
  const [searchQuery, setSearchQuery] = useState('');

  // Active workers (non-offline)
  const activeWorkers = useMemo(() => {
    return workers.filter((w) => w.status !== 'offline');
  }, [workers]);

  // Filtered workers
  const filteredWorkers = useMemo(() => {
    if (!searchQuery) return activeWorkers;
    const q = searchQuery.toLowerCase();
    return activeWorkers.filter(
      (w) => w.id.toLowerCase().includes(q) || w.role.toLowerCase().includes(q)
    );
  }, [activeWorkers, searchQuery]);

  // Messages for selected worker
  const workerMessages = useMemo(() => {
    if (!selectedWorker) return messages.filter((m) => m.type === 'broadcast');
    return messages.filter(
      (m) =>
        (m.from_id === selectedWorker || m.to_id === selectedWorker || m.to_id === 'all')
    );
  }, [messages, selectedWorker]);

  const handleSend = useCallback(() => {
    if (!inputText.trim()) return;

    const fromWorker = selectedWorker || 'conductor';
    const toId = msgType === 'broadcast' ? 'all' : msgType === 'help_request' ? 'conductor' : selectedWorker || 'conductor';

    const newMsg: DMMessage = {
      id: `dm_${Date.now()}`,
      from_id: fromWorker,
      to_id: toId,
      type: msgType,
      content: inputText.trim(),
      timestamp: new Date().toISOString(),
      isEscalation: msgType === 'help_request' && inputText.toLowerCase().includes('blocker'),
    };
    setMessages((prev) => [...prev, newMsg]);
    setInputText('');

    // Simulate response
    if (msgType !== 'broadcast') {
      const targetWorker = workers.find((w) => w.id === toId);
      if (targetWorker) {
        setTimeout(() => {
          const responses = [
            'Terima kasih, saya akan meninjaunya.',
            'Sip, sudah saya terima. Sedang diproses.',
            'Ada kendala di bagian ini, mungkin butuh bantuan.',
            'Sudah selesai. Hasilnya bisa dicek di panel task.',
            'Perlu koordinasi dengan tim lain untuk ini.',
          ];
          setMessages((prev) => [
            ...prev,
            {
              id: `dm_resp_${Date.now()}`,
              from_id: toId,
              to_id: fromWorker,
              type: 'response',
              content: responses[Math.floor(Math.random() * responses.length)],
              timestamp: new Date().toISOString(),
            },
          ]);
        }, 800 + Math.random() * 1200);
      }
    }
  }, [inputText, msgType, selectedWorker, workers]);

  const handleBroadcast = useCallback(() => {
    if (!inputText.trim()) return;
    setMsgType('broadcast');
    const fromWorker = selectedWorker || 'conductor';
    const newMsg: DMMessage = {
      id: `dm_bc_${Date.now()}`,
      from_id: fromWorker,
      to_id: 'all',
      type: 'broadcast',
      content: inputText.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newMsg]);
    setInputText('');
  }, [inputText, selectedWorker]);

  const onlineStatus = (status?: string) => {
    if (status === 'busy') return { dot: 'bg-cyan-400', label: 'sibuk' };
    if (status === 'error') return { dot: 'bg-red-400', label: 'error' };
    if (status === 'offline') return { dot: 'bg-slate-600', label: 'offline' };
    return { dot: 'bg-green-400', label: 'online' };
  };

  const typeColors: Record<DMMessageType, string> = {
    dm: '#06b6d4',
    broadcast: '#f59e0b',
    help_request: '#ef4444',
    response: '#10b981',
  };

  const typeIcons: Record<DMMessageType, typeof MessageSquare> = {
    dm: MessageSquare,
    broadcast: Radio,
    help_request: HelpCircle,
    response: MessageSquare,
  };

  const escalationCount = messages.filter((m) => m.isEscalation).length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar: worker list */}
        <div className="w-44 flex-shrink-0 border-r border-slate-700/30 flex flex-col">
          <div className="flex-shrink-0 px-2 py-1.5 border-b border-slate-700/30 bg-slate-900/40">
            <div className="flex items-center gap-1.5 mb-1">
              <Users className="h-3 w-3 text-cyan-400" />
              <span className="text-[10px] font-mono text-slate-400 uppercase">WorkerHub</span>
              {escalationCount > 0 && (
                <Badge variant="outline" className="text-[8px] px-0.5 py-0 h-3 border-red-500/30 text-red-300">
                  {escalationCount}!
                </Badge>
              )}
            </div>
            <div className="relative">
              <Search className="h-2.5 w-2.5 absolute left-1.5 top-1/2 -translate-y-1/2 text-slate-600" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Cari worker..."
                className="h-5 text-[10px] pl-5 bg-slate-900/60 border-slate-700/50 text-slate-300 placeholder:text-slate-600"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {/* All / Broadcast channel */}
            <button
              onClick={() => setSelectedWorker(null)}
              className={`w-full text-left px-2 py-1.5 text-[10px] font-mono flex items-center gap-1.5 transition-colors ${
                !selectedWorker ? 'bg-cyan-500/10 text-cyan-300' : 'text-slate-400 hover:bg-slate-800/40'
              }`}
            >
              <Radio className="h-3 w-3" />
              <span>Broadcast</span>
              <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-2.5 ml-auto border-slate-700/50 text-slate-500">
                {messages.filter((m) => m.type === 'broadcast').length}
              </Badge>
            </button>

            {filteredWorkers.map((worker) => {
              const status = onlineStatus(worker.status);
              const unread = messages.filter(
                (m) => m.from_id === worker.id && m.type === 'dm'
              ).length;
              return (
                <button
                  key={worker.id}
                  onClick={() => setSelectedWorker(worker.id)}
                  className={`w-full text-left px-2 py-1.5 text-[10px] font-mono flex items-center gap-1.5 transition-colors ${
                    selectedWorker === worker.id ? 'bg-cyan-500/10 text-cyan-300' : 'text-slate-400 hover:bg-slate-800/40'
                  }`}
                >
                  <div className={`h-1.5 w-1.5 rounded-full ${status.dot}`} title={status.label} />
                  <span className="truncate">{worker.emoji} {worker.id}</span>
                  {unread > 0 && (
                    <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-2.5 ml-auto border-cyan-500/30 text-cyan-300">
                      {unread}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: DM conversation */}
        <div className="flex-1 flex flex-col">
          {/* DM header */}
          <div className="flex-shrink-0 px-3 py-1.5 border-b border-slate-700/30 bg-slate-900/40">
            <div className="flex items-center gap-1.5">
              {selectedWorker ? (
                <>
                  <span className="text-sm">
                    {workers.find((w) => w.id === selectedWorker)?.emoji || '🤖'}
                  </span>
                  <span className="text-[10px] font-mono text-slate-300">{selectedWorker}</span>
                  <div className={`h-1.5 w-1.5 rounded-full ${onlineStatus(workers.find((w) => w.id === selectedWorker)?.status).dot}`} />
                </>
              ) : (
                <>
                  <Radio className="h-3 w-3 text-amber-400" />
                  <span className="text-[10px] font-mono text-amber-300">Broadcast Channel</span>
                </>
              )}
              <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 ml-auto border-slate-600/50 text-slate-500 font-mono">
                {workerMessages.length} pesan
              </Badge>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-1.5">
            {workerMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <MessageSquare className="h-8 w-8 text-slate-600/50 mb-2" />
                <p className="text-[10px] text-center text-slate-600">
                  {selectedWorker
                    ? `Mulai percakapan DM dengan ${selectedWorker}`
                    : 'Pesan broadcast akan muncul di sini'}
                </p>
              </div>
            ) : (
              workerMessages.map((msg) => {
                const TypeIcon = typeIcons[msg.type];
                const fromWorker = WORKERS.find((w) => w.id === msg.from_id);
                return (
                  <div
                    key={msg.id}
                    className={`p-2 rounded-md border transition-colors ${
                      msg.isEscalation
                        ? 'bg-red-500/10 border-red-500/30'
                        : msg.type === 'broadcast'
                        ? 'bg-amber-500/10 border-amber-500/20'
                        : msg.type === 'help_request'
                        ? 'bg-red-500/5 border-red-500/20'
                        : 'bg-slate-800/40 border-slate-700/20'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <TypeIcon className="h-2.5 w-2.5" style={{ color: typeColors[msg.type] }} />
                      <span className="text-[10px] font-mono font-semibold" style={{ color: fromWorker?.color || '#94a3b8' }}>
                        {fromWorker?.emoji || '🤖'} {msg.from_id}
                      </span>
                      {msg.to_id !== 'all' && (
                        <span className="text-[9px] text-slate-600">→ {msg.to_id}</span>
                      )}
                      {msg.isEscalation && (
                        <Badge variant="outline" className="text-[9px] px-0.5 py-0 h-2.5 border-red-500/30 text-red-300">
                          <AlertTriangle className="h-2 w-2 mr-0.5" />ESCALATION
                        </Badge>
                      )}
                      <span className="text-[8px] text-slate-600 font-mono ml-auto">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">{msg.content}</p>
                  </div>
                );
              })
            )}
          </div>

          {/* Input bar */}
          <div className="flex-shrink-0 px-2 py-1.5 border-t border-slate-700/30 bg-slate-900/40">
            <div className="flex items-center gap-1 mb-1">
              {(['dm', 'broadcast', 'help_request'] as const).map((t) => {
                const Icon = typeIcons[t];
                return (
                  <button
                    key={t}
                    onClick={() => setMsgType(t)}
                    className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors ${
                      msgType === t ? 'bg-slate-700/60 text-slate-200' : 'text-slate-600 hover:text-slate-400'
                    }`}
                  >
                    <Icon className="h-2.5 w-2.5" style={{ color: msgType === t ? typeColors[t] : undefined }} />
                    {t === 'dm' ? 'DM' : t === 'broadcast' ? 'Broadcast' : 'Bantuan'}
                  </button>
                );
              })}
            </div>
            <div className="flex gap-1.5">
              <Input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={
                  msgType === 'dm'
                    ? `Kirim DM ke ${selectedWorker || '...'}`
                    : msgType === 'broadcast'
                    ? 'Kirim pesan ke semua worker...'
                    : 'Minta bantuan...'
                }
                className="h-6 text-[11px] bg-slate-900/60 border-slate-700/50 text-slate-200 placeholder:text-slate-600"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
              <Button
                onClick={msgType === 'broadcast' ? handleBroadcast : handleSend}
                size="sm"
                disabled={!inputText.trim()}
                className="h-6 px-2 text-[10px] bg-cyan-600 hover:bg-cyan-500 text-white"
              >
                <Send className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
