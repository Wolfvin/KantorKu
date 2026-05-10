'use client';

import { useKantorkuStore } from '@/lib/kantorku/store';
import { useTranslations } from '@/i18n';
import { useContractLifecycle } from '@/hooks/use-contract-lifecycle';
import { ClientChatPanel } from './ChatPanel';
import { ContractCard } from './ContractCard';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CONTRACT_STATE_LABELS, CONTRACT_STATE_COLORS } from '@/lib/kantorku/workers-data';
import {
  MessageSquare,
  Zap,
  RefreshCcw,
  CheckCircle2,
  AlertTriangle,
  Users,
  Clock,
  FileText,
  ThumbsUp,
  Undo2,
  Redo2,
} from 'lucide-react';

// ── Inline Sub-components ───────────────────────────────────────────

function IntakeSection() {
  const intakeResult = useKantorkuStore((s) => s.intakeResult);
  const { t } = useTranslations();
  if (!intakeResult) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-slate-800/60 border border-slate-700/30">
      <div className="flex items-center gap-1.5 mb-1">
        <Zap className="h-3 w-3 text-amber-400" />
        <span className="text-[10px] text-amber-400 font-mono font-semibold">{t('lobby.intake')}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300">{intakeResult.type}</Badge>
        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-cyan-500/30 text-cyan-300">{intakeResult.urgency}</Badge>
        <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-violet-500/30 text-violet-300">{intakeResult.estimated_complexity}</Badge>
        {intakeResult.estimated_workers && intakeResult.estimated_workers.length > 0 && (
          <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-teal-500/30 text-teal-300">{t('lobby.workersCount', { count: intakeResult.estimated_workers.length })}</Badge>
        )}
        {intakeResult.estimated_duration_ms && (
          <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-slate-500/30 text-slate-300">~{(intakeResult.estimated_duration_ms / 1000).toFixed(0)}s</Badge>
        )}
      </div>
      {intakeResult.summary && <p className="text-[9px] text-slate-500 mt-1">{intakeResult.summary}</p>}
    </div>
  );
}

function TeamFeedbackSection() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const teamFeedback = useKantorkuStore((s) => s.teamFeedback);
  const { t } = useTranslations();
  if (contractState !== 'team_consult' || teamFeedback.length === 0) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-violet-500/10 border border-violet-500/30">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Users className="h-3 w-3 text-violet-400" />
        <span className="text-[10px] text-violet-400 font-mono font-semibold">{t('lobby.teamFeedback')}</span>
      </div>
      <div className="space-y-1 max-h-24 overflow-y-auto custom-scrollbar">
        {teamFeedback.map((fb, i) => (
          <div key={`fb-${i}`} className="flex items-start gap-1.5">
            <span className="text-[9px]">
              {fb.feedback_type === 'concern' ? '⚠️' : fb.feedback_type === 'suggestion' ? '💡' : fb.feedback_type === 'agreement' ? '✅' : '❌'}
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

function ApprovalGatesSection() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const approvalGates = useKantorkuStore((s) => s.approvalGates);
  const { t } = useTranslations();
  if (contractState !== 'team_review' || approvalGates.length === 0) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-teal-500/10 border border-teal-500/30">
      <div className="flex items-center gap-1.5 mb-1.5">
        <CheckCircle2 className="h-3 w-3 text-teal-400" />
        <span className="text-[10px] text-teal-400 font-mono font-semibold">{t('lobby.approvalGates')}</span>
      </div>
      <div className="space-y-1">
        {approvalGates.map((gate) => (
          <div key={gate.id} className="flex items-center justify-between">
            <span className="text-[9px] text-slate-300">{gate.gate_type}</span>
            <Badge variant="outline" className={`text-[8px] px-1 py-0 h-3.5 ${
              gate.status === 'approved' ? 'border-green-500/30 text-green-300' :
              gate.status === 'rejected' ? 'border-red-500/30 text-red-300' : 'border-amber-500/30 text-amber-300'
            }`}>{gate.status}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function DebriefSection() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const debriefResult = useKantorkuStore((s) => s.debriefResult);
  const { t } = useTranslations();
  if (contractState !== 'done' || !debriefResult) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-green-500/10 border border-green-500/30">
      <div className="flex items-center gap-1.5 mb-1.5">
        <FileText className="h-3 w-3 text-green-400" />
        <span className="text-[10px] text-green-400 font-mono font-semibold">{t('lobby.debrief')}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5 mb-1.5">
        <div className="text-center p-1.5 rounded bg-slate-900/60">
          <p className="text-xs font-bold text-cyan-300 font-mono">{(debriefResult.total_duration_ms / 1000).toFixed(1)}s</p>
          <p className="text-[8px] text-slate-500">{t('lobby.duration')}</p>
        </div>
        <div className="text-center p-1.5 rounded bg-slate-900/60">
          <p className="text-xs font-bold text-green-300 font-mono">${debriefResult.total_cost.toFixed(4)}</p>
          <p className="text-[8px] text-slate-500">{t('lobby.cost')}</p>
        </div>
      </div>
      <div className="space-y-1">
        {debriefResult.what_went_well.length > 0 && (
          <div>
            <span className="text-[9px] text-green-400 font-mono">✓ {t('lobby.wentWell')}</span>
            {debriefResult.what_went_well.map((w, i) => (
              <p key={`ww-${i}`} className="text-[9px] text-slate-400 ml-2">• {w}</p>
            ))}
          </div>
        )}
        {debriefResult.lessons_learned.length > 0 && (
          <div>
            <span className="text-[9px] text-amber-400 font-mono">💡 {t('lobby.lessons')}</span>
            {debriefResult.lessons_learned.map((l, i) => (
              <p key={`ll-${i}`} className="text-[9px] text-slate-400 ml-2">• {l}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TodoReviewSection() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const contract = useKantorkuStore((s) => s.contract);
  const { t } = useTranslations();
  if (contractState !== 'todo_review' || !contract) return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-teal-500/10 border border-teal-500/30">
      <div className="flex items-center gap-1.5 mb-1.5">
        <CheckCircle2 className="h-3 w-3 text-teal-400" />
        <span className="text-[10px] text-teal-400 font-mono font-semibold">{t('lobby.todoReview')}</span>
      </div>
      <div className="space-y-0.5 max-h-20 overflow-y-auto custom-scrollbar">
        {contract.todos.map((todo) => (
          <div key={todo.id} className="flex items-center gap-1.5 text-[9px]">
            <Clock className="h-2.5 w-2.5 text-teal-400" />
            <span className="text-slate-300 truncate">{todo.description}</span>
            {todo.assigned_to && <span className="text-teal-400 font-mono flex-shrink-0">→ {todo.assigned_to}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function ClientFeedbackPhase() {
  const contractState = useKantorkuStore((s) => s.contractState);
  const { t } = useTranslations();
  if (contractState !== 'client_feedback') return null;

  return (
    <div className="flex-shrink-0 mx-3 mt-2 p-2 rounded-md bg-amber-500/10 border border-amber-500/30">
      <div className="flex items-center gap-1.5">
        <ThumbsUp className="h-3 w-3 text-amber-400" />
        <span className="text-[10px] text-amber-400 font-mono font-semibold">{t('lobby.confirmed')}</span>
        <span className="text-[9px] text-amber-300/60 ml-1">{t('lobby.proceeding')}</span>
      </div>
    </div>
  );
}

function FailedTodosSection({ onRetry }: { onRetry: (todoId: string) => void }) {
  const contractState = useKantorkuStore((s) => s.contractState);
  const contract = useKantorkuStore((s) => s.contract);
  const { t } = useTranslations();
  if (contractState !== 'failed' || !contract) return null;

  const failedTodos = contract.todos.filter((todo) => todo.status === 'failed');
  if (failedTodos.length === 0) return null;

  return (
    <div className="space-y-1.5">
      {failedTodos.map((todo) => (
        <div key={todo.id} className="flex items-center gap-2 p-2 rounded-md bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-red-300 truncate">{todo.description}</p>
            {todo.error && <p className="text-[8px] text-red-400/60 truncate">{todo.error}</p>}
          </div>
          <Button onClick={() => onRetry(todo.id)} size="sm" variant="outline" className="h-6 text-[9px] border-amber-500/40 text-amber-300 hover:bg-amber-500/10 px-2">
            <RefreshCcw className="h-2.5 w-2.5 mr-1" />
            {t('common.retry')}
          </Button>
        </div>
      ))}
    </div>
  );
}

// ── Main LobbyZone ──────────────────────────────────────────────────
export function LobbyZone() {
  const {
    clientMessages,
    contract,
    contractState,
    isManagerThinking,
    isWorking,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useKantorkuStore();

  const {
    handleSendMessage,
    handleAccept,
    handleRevise,
    handleRetryTodo,
    handleNewSession,
    handleReject,
    handleAnswerQuestion,
  } = useContractLifecycle();
  const { t } = useTranslations();

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-slate-700/50 bg-slate-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white">{t('zones.lobby')}</h2>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => undo()}
              disabled={!canUndo()}
              className={`p-1 rounded-md transition-colors ${canUndo() ? 'text-slate-400 hover:text-cyan-400 hover:bg-slate-700/50' : 'text-slate-700 cursor-not-allowed'}`}
              title={t('common.undo')}
            >
              <Undo2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => redo()}
              disabled={!canRedo()}
              className={`p-1 rounded-md transition-colors ${canRedo() ? 'text-slate-400 hover:text-cyan-400 hover:bg-slate-700/50' : 'text-slate-700 cursor-not-allowed'}`}
              title={t('common.redo')}
            >
              <Redo2 className="h-3.5 w-3.5" />
            </button>
            <Badge
              variant="outline"
              className={`text-[9px] px-1.5 py-0 h-4 font-mono ${CONTRACT_STATE_COLORS[contractState]}`}
            >
              {CONTRACT_STATE_LABELS[contractState]}
            </Badge>
          </div>
        </div>
      </div>

      {/* Intake Result */}
      <IntakeSection />

      {/* Team Consult Feedback */}
      <TeamFeedbackSection />

      {/* Approval Gates */}
      <ApprovalGatesSection />

      {/* Debrief Summary */}
      <DebriefSection />

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <ClientChatPanel
          messages={clientMessages}
          onSend={handleSendMessage}
          isThinking={isManagerThinking}
          disabled={isWorking}
          onNewSession={handleNewSession}
          onAnswerQuestion={handleAnswerQuestion}
        />
      </div>

      {/* Todo Review Section */}
      <TodoReviewSection />

      {/* Client Feedback Phase */}
      <ClientFeedbackPhase />

      {/* Contract Card (if presented or in lifecycle phases) */}
      {contract && !['done', 'failed'].includes(contractState) && !isWorking && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1">
          <ContractCard
            contract={contract}
            onAccept={handleAccept}
            onRevise={handleRevise}
            onReject={handleReject}
            onRetryTodo={handleRetryTodo}
            isWorking={isWorking}
          />
        </div>
      )}

      {/* Working state - show contract card with progress */}
      {contract && isWorking && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1">
          <ContractCard
            contract={contract}
            onAccept={handleAccept}
            onRevise={handleRevise}
            onReject={handleReject}
            onRetryTodo={handleRetryTodo}
            isWorking={isWorking}
          />
        </div>
      )}

      {/* Done/Failed State Actions */}
      {(contractState === 'done' || contractState === 'failed') && (
        <div className="flex-shrink-0 px-3 pb-3 pt-1 space-y-2">
          <FailedTodosSection onRetry={handleRetryTodo} />
          <Button
            onClick={handleNewSession}
            className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs"
          >
            <RefreshCcw className="h-3.5 w-3.5 mr-1.5" />
            {t('common.newSession')}
          </Button>
        </div>
      )}
    </div>
  );
}
