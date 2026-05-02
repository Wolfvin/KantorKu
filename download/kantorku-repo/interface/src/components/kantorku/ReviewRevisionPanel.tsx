'use client';

import { useState, useMemo } from 'react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { WORKERS } from '@/lib/kantorku/workers-data';
import type { ReviewRevision } from '@/lib/kantorku/types';
import {
  Eye, CheckCircle2, XCircle, Clock, MessageSquare,
  AlertTriangle, FileText, ChevronDown, ChevronRight, Filter,
} from 'lucide-react';

const STATUS_CONFIG: Record<string, { color: string; bg: string; border: string; icon: typeof Clock }> = {
  pending: { color: 'text-amber-300', bg: 'bg-amber-500/10', border: 'border-amber-500/30', icon: Clock },
  approved: { color: 'text-green-300', bg: 'bg-green-500/10', border: 'border-green-500/30', icon: CheckCircle2 },
  changes_requested: { color: 'text-red-300', bg: 'bg-red-500/10', border: 'border-red-500/30', icon: XCircle },
  resolved: { color: 'text-blue-300', bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: CheckCircle2 },
};

const TYPE_COLORS: Record<string, string> = {
  code: '#06b6d4',
  design: '#ec4899',
  security: '#ef4444',
  quality: '#f59e0b',
};

export function ReviewRevisionPanel() {
  const { reviews, addReview, updateReview, contract, workers } = useKantorkuStore();
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [commentText, setCommentText] = useState('');
  const [showNewReview, setShowNewReview] = useState(false);
  const [newReviewType, setNewReviewType] = useState<ReviewRevision['review_type']>('code');

  const filteredReviews = useMemo(() => {
    return reviews.filter((r) => {
      if (filterStatus !== 'all' && r.status !== filterStatus) return false;
      if (filterType !== 'all' && r.review_type !== filterType) return false;
      return true;
    });
  }, [reviews, filterStatus, filterType]);

  const getWorkerEmoji = (id: string) => {
    const w = workers.find((wk) => wk.id === id);
    return w?.emoji || '🤖';
  };

  const getWorkerColor = (id: string) => {
    const w = workers.find((wk) => wk.id === id);
    return w?.color || '#94a3b8';
  };

  const handleApprove = (id: string) => {
    updateReview(id, 'approved');
  };

  const handleRequestRevision = (id: string) => {
    const comments = commentText.trim() ? [commentText.trim()] : ['Revision requested'];
    updateReview(id, 'changes_requested', comments);
    setCommentText('');
  };

  const handleCreateReview = () => {
    if (!contract) return;
    const activeWorkers = contract.todos
      .map((t) => t.assigned_to)
      .filter((v, i, a) => v && a.indexOf(v) === i);

    if (activeWorkers.length === 0) return;

    addReview({
      id: `rev_${Date.now()}`,
      contract_id: contract.id,
      reviewer: activeWorkers[Math.floor(Math.random() * activeWorkers.length)] || 'auditor',
      review_type: newReviewType,
      status: 'pending',
      comments: [],
      timestamp: new Date().toISOString(),
    });
    setShowNewReview(false);
  };

  // Demo data if no reviews exist
  const displayReviews = filteredReviews.length > 0 ? filteredReviews : [];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Eye className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Review & Revisi</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-600/50 text-slate-500 font-mono">
              {reviews.length}
            </Badge>
          </div>
          {contract && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowNewReview(!showNewReview)}
              className="h-5 px-2 text-[9px] text-cyan-400 hover:text-cyan-300"
            >
              + Review
            </Button>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
          <Filter className="h-2.5 w-2.5 text-slate-600" />
          {['all', 'pending', 'approved', 'changes_requested', 'resolved'].map((s) => (
            <Badge
              key={s}
              variant="outline"
              className={`text-[8px] px-1 py-0 h-3 cursor-pointer font-mono ${
                filterStatus === s
                  ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                  : 'border-slate-700/30 text-slate-500 hover:border-slate-500/40'
              }`}
              onClick={() => setFilterStatus(s)}
            >
              {s === 'all' ? 'ALL' : s === 'changes_requested' ? 'REVISION' : s.toUpperCase()}
            </Badge>
          ))}
        </div>
      </div>

      {/* New Review Form */}
      {showNewReview && (
        <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-800/60">
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileText className="h-3 w-3 text-cyan-400" />
            <span className="text-[10px] text-cyan-300 font-mono">BUAT REVIEW BARU</span>
          </div>
          <div className="flex items-center gap-1.5 mb-1.5">
            {(['code', 'design', 'security', 'quality'] as const).map((t) => (
              <Badge
                key={t}
                variant="outline"
                className={`text-[8px] px-1.5 py-0 h-4 cursor-pointer font-mono ${
                  newReviewType === t ? '' : 'border-slate-700/30 text-slate-500'
                }`}
                style={newReviewType === t ? {
                  borderColor: `${TYPE_COLORS[t]}40`,
                  color: TYPE_COLORS[t],
                  backgroundColor: `${TYPE_COLORS[t]}10`,
                } : undefined}
                onClick={() => setNewReviewType(t)}
              >
                {t}
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Button onClick={handleCreateReview} size="sm" className="flex-1 text-[10px] bg-cyan-600 hover:bg-cyan-500">
              Create
            </Button>
            <Button onClick={() => setShowNewReview(false)} variant="outline" size="sm" className="text-[10px] border-slate-600/50 text-slate-400">
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Reviews List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2">
        {displayReviews.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Eye className="h-8 w-8 text-slate-600/50 mb-2" />
            <p className="text-[10px] text-center text-slate-600">
              Belum ada review.<br />
              Review akan muncul setelah eksekusi kontrak.
            </p>
          </div>
        ) : (
          displayReviews.map((review) => {
            const config = STATUS_CONFIG[review.status] || STATUS_CONFIG.pending;
            const StatusIcon = config.icon;
            const isExpanded = expandedId === review.id;
            const reviewer = WORKERS.find((w) => w.id === review.reviewer);

            return (
              <Card key={review.id} className={`${config.bg} ${config.border} border backdrop-blur-sm`}>
                <CardContent className="p-2.5">
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setExpandedId(isExpanded ? null : review.id)}
                  >
                    <div className="flex items-center gap-2">
                      <StatusIcon className={`h-3.5 w-3.5 ${config.color}`} />
                      <Badge
                        variant="outline"
                        className="text-[8px] px-1.5 py-0 h-3.5 font-mono"
                        style={{
                          borderColor: `${TYPE_COLORS[review.review_type] || '#94a3b8'}40`,
                          color: TYPE_COLORS[review.review_type] || '#94a3b8',
                        }}
                      >
                        {review.review_type}
                      </Badge>
                      <span className="text-[11px] font-mono" style={{ color: getWorkerColor(review.reviewer) }}>
                        {reviewer?.emoji || '🤖'} {review.reviewer}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Badge variant="outline" className={`text-[8px] px-1 py-0 h-3.5 ${config.border} ${config.color}`}>
                        {review.status === 'changes_requested' ? 'REVISION' : review.status.toUpperCase()}
                      </Badge>
                      {isExpanded ? (
                        <ChevronDown className="h-3 w-3 text-slate-500" />
                      ) : (
                        <ChevronRight className="h-3 w-3 text-slate-500" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-2 pt-2 border-t border-slate-700/20 space-y-2">
                      {/* Timestamp */}
                      <div className="flex items-center gap-1">
                        <Clock className="h-2.5 w-2.5 text-slate-600" />
                        <span className="text-[9px] text-slate-500 font-mono">
                          {new Date(review.timestamp).toLocaleString()}
                        </span>
                      </div>

                      {/* Comments */}
                      {review.comments.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[9px] text-slate-400 font-mono uppercase">Komentar:</span>
                          {review.comments.map((c, i) => (
                            <div key={i} className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
                              <p className="text-[10px] text-slate-300">{c}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Actions for pending reviews */}
                      {review.status === 'pending' && (
                        <div className="space-y-1.5">
                          <Textarea
                            value={commentText}
                            onChange={(e) => setCommentText(e.target.value)}
                            placeholder="Tambahkan komentar revisi..."
                            className="min-h-[40px] text-[11px] bg-slate-900/60 border-slate-700/50 text-slate-200 placeholder:text-slate-600 resize-none"
                          />
                          <div className="flex gap-2">
                            <Button
                              onClick={() => handleApprove(review.id)}
                              size="sm"
                              className="flex-1 text-[10px] bg-green-600 hover:bg-green-500 text-white"
                            >
                              <CheckCircle2 className="h-3 w-3 mr-1" />
                              Setujui
                            </Button>
                            <Button
                              onClick={() => handleRequestRevision(review.id)}
                              size="sm"
                              variant="outline"
                              className="flex-1 text-[10px] border-red-500/40 text-red-300 hover:bg-red-500/10"
                            >
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Minta Revisi
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Diff hint */}
                      {review.status === 'changes_requested' && (
                        <div className="p-1.5 rounded bg-red-500/10 border border-red-500/20">
                          <div className="flex items-center gap-1 mb-1">
                            <MessageSquare className="h-2.5 w-2.5 text-red-400" />
                            <span className="text-[9px] text-red-300 font-mono">REVISI DIPERLUKAN</span>
                          </div>
                          <div className="text-[9px] font-mono space-y-0.5">
                            <p className="text-green-300">+ Perubahan yang diminta</p>
                            <p className="text-red-300">- Konten asli yang perlu direvisi</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
