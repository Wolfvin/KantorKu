'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { Button } from '@/components/ui/button';
import { ThumbsUp, ThumbsDown, CheckCircle2 } from 'lucide-react';
import type { Contract } from '@/lib/kantorku/types';

interface ContractActionsProps {
  contract: Contract;
  onAccept: () => void;
  onRevise: (feedback: string) => void;
  onReject: () => void;
  isWorking: boolean;
}

export function ContractActions({ contract, onAccept, onRevise, onReject, isWorking }: ContractActionsProps) {
  const { contractState } = useKantorkuStore();

  if (['done', 'failed'].includes(contractState)) return null;

  return (
    <div className="flex items-center gap-2" role="group" aria-label="Contract actions">
      {contractState === 'contract_presented' && !isWorking && (
        <>
          <Button
            onClick={onAccept}
            size="sm"
            className="bg-green-600 hover:bg-green-500 text-white text-[11px] px-3"
            aria-label="Accept contract"
          >
            <ThumbsUp className="h-3.5 w-3.5 mr-1" />
            Accept
          </Button>
          <Button
            onClick={() => {
              const feedback = prompt('What changes would you like?');
              if (feedback) onRevise(feedback);
            }}
            variant="outline"
            size="sm"
            className="border-amber-500/30 text-amber-300 hover:bg-amber-500/10 text-[11px] px-3"
            aria-label="Request revisions"
          >
            Revise
          </Button>
          <Button
            onClick={onReject}
            variant="outline"
            size="sm"
            className="border-red-500/30 text-red-300 hover:bg-red-500/10 text-[11px] px-3"
            aria-label="Reject contract"
          >
            <ThumbsDown className="h-3.5 w-3.5 mr-1" />
            Reject
          </Button>
        </>
      )}
      {contractState === 'todo_review' && (
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3 w-3 text-teal-400" />
          <span className="text-[10px] text-teal-400 font-mono">Reviewing todos...</span>
        </div>
      )}
    </div>
  );
}
