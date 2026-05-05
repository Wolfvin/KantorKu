'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useKantorkuStore } from '@/lib/kantorku/store';
import {
  Save,
  RotateCcw,
  Clock,
  Shield,
  Database,
  CheckCircle2,
  AlertTriangle,
  HardDrive,
  Plus,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

// ── Snapshot Types ──────────────────────────────────────────────────
interface SnapshotInfo {
  id: string;
  timestamp: string;
  type: 'office' | 'session';
  sessionId?: string;
  contractState?: string;
  workerCount?: number;
  costUsd?: number;
}

// ── Derive snapshots from store + mock data ─────────────────────────
function getAvailableSnapshots(): SnapshotInfo[] {
  const store = useKantorkuStore.getState();
  const { sessions, contractState, workers, costReport } = store;

  // Create snapshot entries from existing sessions
  const sessionSnapshots: SnapshotInfo[] = sessions.map((s) => ({
    id: `snap_session_${s.session_id}`,
    timestamp: s.updated_at,
    type: 'session',
    sessionId: s.session_id,
    contractState: s.state,
    costUsd: s.total_cost,
  }));

  // Add a mock office snapshot if we have any data
  const officeSnapshot: SnapshotInfo | null = sessions.length > 0 ? {
    id: 'snap_office_latest',
    timestamp: new Date().toISOString(),
    type: 'office',
    workerCount: workers.length,
    contractState: contractState || 'idle',
    costUsd: costReport?.total_cost || 0,
  } : null;

  return [...(officeSnapshot ? [officeSnapshot] : []), ...sessionSnapshots];
}

export function CrashRecoveryPanel() {
  const [restoring, setRestoring] = useState<string | null>(null);
  const [autoRecovery, setAutoRecovery] = useState(true);
  const [manualSnapshots, setManualSnapshots] = useState<SnapshotInfo[]>([]);

  const contractState = useKantorkuStore((s) => s.contractState);
  const sessions = useKantorkuStore((s) => s.sessions);
  const costReport = useKantorkuStore((s) => s.costReport);

  // Compute snapshots reactively from store
  const storeSnapshots = useMemo(() => getAvailableSnapshots(), [contractState, sessions, costReport]);
  const snapshots = [...manualSnapshots, ...storeSnapshots];

  const handleRestore = async (snapshotId: string) => {
    setRestoring(snapshotId);
    // Simulate restore operation
    await new Promise((r) => setTimeout(r, 1500));
    setRestoring(null);
    toast.success('Snapshot restored', {
      description: `Restored from ${snapshotId}`,
      duration: 3000,
    });
  };

  const handleCreateSnapshot = async () => {
    const store = useKantorkuStore.getState();
    const newSnapshot: SnapshotInfo = {
      id: `snap_manual_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: 'office',
      workerCount: store.workers.length,
      contractState: store.contractState || 'idle',
      costUsd: store.costReport?.total_cost || 0,
    };
    setManualSnapshots((prev) => [newSnapshot, ...prev]);
    toast.success('Manual snapshot created', {
      description: `Office state captured at ${new Date().toLocaleTimeString()}`,
      duration: 3000,
    });
  };

  const formatTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return ts;
    }
  };

  return (
    <Card className="border-slate-700/30 bg-slate-800/40 backdrop-blur-sm">
      <CardHeader className="p-2.5 pb-1">
        <CardTitle className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
          <Shield className="h-3 w-3 text-amber-400" />
          CRASH RECOVERY
          <Badge variant="outline" className="text-[7px] px-1 py-0 h-3 border-amber-500/30 text-amber-300 ml-1">
            {snapshots.length} snapshots
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-2.5 pt-1 space-y-2">
        {/* Auto-recovery toggle */}
        <div className="flex items-center justify-between p-1.5 rounded bg-slate-900/60 border border-slate-700/20">
          <div className="flex items-center gap-1.5">
            <RotateCcw className="h-3 w-3 text-amber-400" />
            <span className="text-[9px] text-slate-300">Auto-recovery on startup</span>
          </div>
          <div
            onClick={() => setAutoRecovery(!autoRecovery)}
            className={`relative h-4 w-7 rounded-full cursor-pointer transition-colors ${
              autoRecovery ? 'bg-cyan-600' : 'bg-slate-700'
            }`}
          >
            <div
              className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-transform ${
                autoRecovery ? 'translate-x-3.5' : 'translate-x-0.5'
              }`}
            />
          </div>
        </div>

        {/* Create manual snapshot */}
        <Button
          onClick={handleCreateSnapshot}
          variant="outline"
          size="sm"
          className="w-full h-6 text-[9px] border-amber-500/30 text-amber-300 hover:bg-amber-500/10"
        >
          <Plus className="h-2.5 w-2.5 mr-1" />
          Create Manual Snapshot
        </Button>

        {/* Available Snapshots */}
        <div className="space-y-1 max-h-48 overflow-y-auto custom-scrollbar">
          {snapshots.length > 0 ? snapshots.map((snap) => (
            <div
              key={snap.id}
              className="p-1.5 rounded bg-slate-900/60 border border-slate-700/20 space-y-1"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 min-w-0">
                  <HardDrive className="h-2.5 w-2.5 text-slate-500 flex-shrink-0" />
                  <Badge
                    variant="outline"
                    className={`text-[7px] px-0.5 py-0 h-3 flex-shrink-0 ${
                      snap.type === 'office'
                        ? 'border-amber-500/30 text-amber-300'
                        : 'border-cyan-500/30 text-cyan-300'
                    }`}
                  >
                    {snap.type.toUpperCase()}
                  </Badge>
                  <span className="text-[8px] text-slate-500 font-mono truncate">
                    {snap.id.slice(0, 20)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-[8px] text-slate-500">
                <div className="flex items-center gap-0.5">
                  <Clock className="h-2 w-2" />
                  <span>{formatTimestamp(snap.timestamp)}</span>
                </div>
                {snap.contractState && (
                  <span className="font-mono">state: {snap.contractState}</span>
                )}
                {snap.costUsd !== undefined && (
                  <span className="font-mono">${snap.costUsd.toFixed(4)}</span>
                )}
              </div>
              {snap.workerCount !== undefined && (
                <div className="flex items-center gap-0.5 text-[8px] text-slate-600">
                  <Database className="h-2 w-2" />
                  <span>{snap.workerCount} workers tracked</span>
                </div>
              )}
              <div className="flex items-center gap-1 pt-0.5">
                <Button
                  onClick={() => handleRestore(snap.id)}
                  disabled={restoring === snap.id}
                  variant="ghost"
                  size="sm"
                  className="h-4 px-1.5 text-[8px] text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10"
                >
                  {restoring === snap.id ? (
                    <>
                      <Loader2 className="h-2 w-2 mr-0.5 animate-spin" />
                      Restoring...
                    </>
                  ) : (
                    <>
                      <RotateCcw className="h-2 w-2 mr-0.5" />
                      Restore
                    </>
                  )}
                </Button>
              </div>
            </div>
          )) : (
            <div className="flex items-center gap-2 text-slate-600 py-2">
              <AlertTriangle className="h-3 w-3" />
              <p className="text-[9px]">No snapshots available. Execute a contract or create a manual snapshot.</p>
            </div>
          )}
        </div>

        {/* Recovery info */}
        <div className="p-1.5 rounded bg-slate-900/40 border border-slate-700/10">
          <p className="text-[7px] text-slate-600 leading-relaxed">
            Snapshots are stored atomically (tmp+rename pattern). On startup, CrashRecovery tries: office snapshot → session snapshots → Ring1. Keep last 10 snapshots, auto-rotate older.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
