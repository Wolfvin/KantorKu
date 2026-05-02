'use client';

import { useState, useRef } from 'react';
import { WorkerIdentity, WorkerEmotion } from '@/lib/kantorku/types';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useKantorkuStore } from '@/lib/kantorku/store';
import {
  ChevronDown, ChevronUp, Shield, Activity, Zap,
  ArrowRightLeft, TrendingUp, TrendingDown, Minus, Clock,
} from 'lucide-react';

interface WorkerCardProps {
  worker: WorkerIdentity;
  compact?: boolean;
}

const statusStyles: Record<string, { dot: string; bg: string; text: string }> = {
  idle: { dot: 'bg-slate-500', bg: 'bg-slate-800/60', text: 'text-slate-400' },
  busy: { dot: 'bg-cyan-400 animate-pulse', bg: 'bg-cyan-950/40', text: 'text-cyan-300' },
  error: { dot: 'bg-red-400', bg: 'bg-red-950/40', text: 'text-red-300' },
  offline: { dot: 'bg-slate-700', bg: 'bg-slate-900/60', text: 'text-slate-600' },
};

const EMOTION_EMOJI: Record<string, string> = {
  confident: '💪',
  uncertain: '🤔',
  frustrated: '😤',
  excited: '🤩',
  neutral: '😐',
};

// Animated trust score component
function AnimatedTrustScore({ score, trend }: { score: number; trend?: string }) {
  const [displayScore, setDisplayScore] = useState(score);
  const prevScore = useRef(score);
  const rafRef = useRef<number | null>(null);

  // Use requestAnimationFrame to animate score transitions
  // without calling setState directly inside useEffect body
  if (prevScore.current !== score && rafRef.current === null) {
    const start = prevScore.current;
    const end = score;
    const duration = 500;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = Math.round(start + (end - start) * eased);
      setDisplayScore(next);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        rafRef.current = null;
        prevScore.current = score;
      }
    };
    rafRef.current = requestAnimationFrame(animate);
  }

  const isAnimating = rafRef.current !== null;

  return (
    <div className="flex items-center gap-1.5">
      <Shield className="h-2.5 w-2.5 text-slate-500" />
      <div className="flex-1 max-w-[60px]">
        <Progress
          value={displayScore}
          className="h-1 bg-slate-900/60 transition-all"
        />
      </div>
      <span className={`text-[8px] font-mono transition-colors duration-300 ${
        isAnimating ? 'text-cyan-300' : 'text-slate-400'
      }`}>
        {displayScore}
      </span>
      {trend && (
        trend === 'improving' ? <TrendingUp className="h-2 w-2 text-green-400" /> :
        trend === 'declining' ? <TrendingDown className="h-2 w-2 text-red-400" /> :
        <Minus className="h-2 w-2 text-slate-600" />
      )}
      {isAnimating && (
        <span className="text-[7px] text-cyan-400 animate-pulse">●</span>
      )}
    </div>
  );
}

export function WorkerCard({ worker, compact = false }: WorkerCardProps) {
  const { trustScores, workerEmotions, delegations } = useKantorkuStore();
  const [expanded, setExpanded] = useState(false);

  const style = statusStyles[worker.status || 'idle'] || statusStyles.idle;
  const trust = trustScores.find((t) => t.worker_id === worker.id);
  const emotion: WorkerEmotion | undefined = workerEmotions.find((e) => e.worker_id === worker.id);
  const workerDelegations = delegations.filter(
    (d) => d.from_worker === worker.id || d.to_worker === worker.id
  );

  const trustScore = trust?.score ?? worker.trust_score ?? 0;
  const trustTrend = trust?.trend;
  const totalTasks = worker.total_tasks ?? 0;
  const successRate = worker.success_rate ?? 0;

  if (compact) {
    return (
      <div
        className={`flex items-center gap-2 px-2 py-1.5 rounded-md ${style.bg} border border-slate-700/30 transition-all duration-300`}
        style={{
          boxShadow: worker.status === 'busy' ? `0 0 8px ${worker.color}33` : 'none',
        }}
      >
        <span className="text-sm">{worker.emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            <span className="text-xs font-mono text-slate-300 truncate">
              {worker.id}
            </span>
            {emotion && (
              <span className="text-[10px]">{EMOTION_EMOJI[emotion.emotion] || '😐'}</span>
            )}
          </div>
          {worker.current_task && (
            <p className="text-[9px] text-slate-500 truncate mt-0.5">
              {worker.current_task}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <Card
      className={`${style.bg} border-slate-700/30 backdrop-blur-sm transition-all duration-300 hover:border-slate-600/50 cursor-pointer`}
      style={{
        boxShadow: worker.status === 'busy' ? `0 0 12px ${worker.color}22` : 'none',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-2.5">
          <div className="relative">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg text-lg"
              style={{ backgroundColor: `${worker.color}20` }}
            >
              {worker.emoji}
            </div>
            {/* Emotion indicator */}
            {emotion && (
              <span className="absolute -top-1 -right-1 text-[10px] leading-none">
                {EMOTION_EMOJI[emotion.emotion] || '😐'}
              </span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${style.dot}`} />
              <span className="text-sm font-mono text-white font-medium">
                {worker.id}
              </span>
              {workerDelegations.length > 0 && (
                <ArrowRightLeft className="h-2.5 w-2.5 text-amber-400" title="Has delegations" />
              )}
              <div className="ml-auto">
                {expanded ? (
                  <ChevronUp className="h-3 w-3 text-slate-500" />
                ) : (
                  <ChevronDown className="h-3 w-3 text-slate-500" />
                )}
              </div>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">{worker.role}</p>

            {/* Badges */}
            <div className="flex items-center gap-1.5 mt-1">
              <Badge
                variant="outline"
                className="text-[9px] px-1.5 py-0 h-4 border-slate-600/50 text-slate-500"
              >
                {worker.squad}
              </Badge>
              <Badge
                variant="outline"
                className={`text-[9px] px-1.5 py-0 h-4 ${style.text}`}
                style={{ borderColor: `${worker.color}40` }}
              >
                {worker.status || 'idle'}
              </Badge>
            </div>

            {/* Capabilities list (compact, in main view) */}
            {worker.capabilities && worker.capabilities.length > 0 && (
              <div className="flex flex-wrap gap-0.5 mt-1.5">
                {worker.capabilities.slice(0, 3).map((cap, i) => (
                  <Badge key={i} variant="outline" className="text-[7px] px-0.5 py-0 h-3 border-slate-700/50 text-slate-500">
                    {cap}
                  </Badge>
                ))}
                {worker.capabilities.length > 3 && (
                  <span className="text-[7px] text-slate-600">+{worker.capabilities.length - 3}</span>
                )}
              </div>
            )}

            {/* Animated Trust Score Bar */}
            <div className="mt-1.5">
              <AnimatedTrustScore score={trustScore} trend={trustTrend} />
            </div>

            {/* Task, Success & Latency Stats */}
            <div className="flex items-center gap-2 mt-0.5">
              <div className="flex items-center gap-0.5">
                <Activity className="h-2.5 w-2.5 text-slate-600" />
                <span className="text-[8px] text-slate-500 font-mono">{totalTasks} tasks</span>
              </div>
              <div className="flex items-center gap-0.5">
                <Zap className="h-2.5 w-2.5 text-slate-600" />
                <span className="text-[8px] text-slate-500 font-mono">
                  {successRate > 0 ? `${(successRate * 100).toFixed(0)}%` : '—'}
                </span>
              </div>
              {worker.avg_latency_ms !== undefined && (
                <div className="flex items-center gap-0.5">
                  <Clock className="h-2.5 w-2.5 text-slate-600" />
                  <span className="text-[8px] text-slate-500 font-mono">{worker.avg_latency_ms}ms</span>
                </div>
              )}
            </div>

            {worker.current_task && (
              <p className="text-[10px] text-cyan-400/80 mt-1.5 truncate font-mono">
                ⚡ {worker.current_task}
              </p>
            )}

            {/* Expanded Details */}
            {expanded && (
              <div className="mt-2 pt-2 border-t border-slate-700/30 space-y-1.5">
                <div className="grid grid-cols-2 gap-1.5">
                  <div className="p-1.5 rounded bg-slate-900/60">
                    <p className="text-[8px] text-slate-500 uppercase">Model</p>
                    <p className="text-[9px] text-slate-300 font-mono truncate">{worker.model}</p>
                  </div>
                  <div className="p-1.5 rounded bg-slate-900/60">
                    <p className="text-[8px] text-slate-500 uppercase">Squad</p>
                    <p className="text-[9px] text-slate-300 font-mono">{worker.squad}</p>
                  </div>
                  <div className="p-1.5 rounded bg-slate-900/60">
                    <p className="text-[8px] text-slate-500 uppercase">Trust</p>
                    <p className="text-[9px] text-slate-300 font-mono">{trustScore}/100 {trustTrend ? `(${trustTrend})` : ''}</p>
                  </div>
                  <div className="p-1.5 rounded bg-slate-900/60">
                    <p className="text-[8px] text-slate-500 uppercase">Success</p>
                    <p className="text-[9px] text-slate-300 font-mono">
                      {successRate > 0 ? `${(successRate * 100).toFixed(1)}%` : 'N/A'}
                    </p>
                  </div>
                </div>

                {worker.skill_md && (
                  <div className="p-1.5 rounded bg-slate-900/40">
                    <p className="text-[8px] text-slate-500 uppercase">Skills</p>
                    <p className="text-[9px] text-slate-400">{worker.skill_md}</p>
                  </div>
                )}

                {worker.personality && (
                  <div className="p-1.5 rounded bg-slate-900/40">
                    <p className="text-[8px] text-slate-500 uppercase">Personality</p>
                    <p className="text-[9px] text-slate-400">{worker.personality}</p>
                  </div>
                )}

                {worker.capabilities && worker.capabilities.length > 0 && (
                  <div>
                    <p className="text-[8px] text-slate-500 uppercase mb-0.5">All Capabilities</p>
                    <div className="flex flex-wrap gap-0.5">
                      {worker.capabilities.map((cap, i) => (
                        <Badge key={i} variant="outline" className="text-[7px] px-0.5 py-0 h-3 border-slate-700/50 text-slate-500">
                          {cap}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {worker.avg_latency_ms !== undefined && (
                  <div className="flex items-center gap-1">
                    <span className="text-[8px] text-slate-500">Avg Latency:</span>
                    <span className="text-[8px] text-slate-400 font-mono">{worker.avg_latency_ms}ms</span>
                  </div>
                )}

                {worker.hired_at && (
                  <div className="flex items-center gap-1">
                    <span className="text-[8px] text-slate-500">Hired:</span>
                    <span className="text-[8px] text-slate-400 font-mono">
                      {new Date(worker.hired_at).toLocaleDateString()}
                    </span>
                  </div>
                )}

                {emotion && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px]">{EMOTION_EMOJI[emotion.emotion]}</span>
                    <span className="text-[8px] text-slate-400">{emotion.emotion}</span>
                    <span className="text-[8px] text-slate-600 font-mono">({(emotion.confidence * 100).toFixed(0)}%)</span>
                  </div>
                )}

                {workerDelegations.length > 0 && (
                  <div>
                    <p className="text-[8px] text-slate-500 uppercase mb-0.5">Delegations</p>
                    <div className="space-y-0.5">
                      {workerDelegations.slice(0, 3).map((d) => (
                        <div key={d.id} className="flex items-center gap-1 text-[8px]">
                          <ArrowRightLeft className="h-2 w-2 text-amber-400" />
                          <span className="text-slate-400 font-mono">
                            {d.from_worker === worker.id ? `→ ${d.to_worker}` : `← ${d.from_worker}`}
                          </span>
                          <Badge
                            variant="outline"
                            className="text-[6px] px-0.5 py-0 h-2.5"
                            style={{
                              borderColor: d.status === 'accepted' ? '#22c55e40' : d.status === 'rejected' ? '#ef444440' : '#f59e0b40',
                              color: d.status === 'accepted' ? '#4ade80' : d.status === 'rejected' ? '#f87171' : '#fbbf24',
                            }}
                          >
                            {d.status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <p className="text-[9px] text-slate-600 mt-1 truncate" title={worker.model}>
              {worker.model}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
