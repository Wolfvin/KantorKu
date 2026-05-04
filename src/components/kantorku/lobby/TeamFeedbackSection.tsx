'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { Users } from 'lucide-react';

export function TeamFeedbackSection() {
  const { contractState, teamFeedback } = useKantorkuStore();

  if (contractState !== 'team_consult' || teamFeedback.length === 0) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-violet-500/10 border border-violet-500/30" role="region" aria-label="Team feedback">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Users className="h-3 w-3 text-violet-400" />
        <span className="text-[10px] text-violet-400 font-mono font-semibold">TEAM FEEDBACK</span>
      </div>
      <div className="space-y-1 max-h-24 overflow-y-auto custom-scrollbar">
        {teamFeedback.map((fb, i) => (
          <div key={i} className="flex items-start gap-1.5">
            <span className="text-[9px]">
              {fb.feedback_type === 'concern' ? '⚠️' :
               fb.feedback_type === 'suggestion' ? '💡' :
               fb.feedback_type === 'agreement' ? '✅' : '❌'}
            </span>
            <div>
              <span className="text-[9px] text-slate-400 font-mono">{fb.worker_id}</span>
              <p className="text-[9px] text-slate-300">{fb.content}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
