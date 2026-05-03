'use client';

import { lazy, Suspense } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  TrendingUp,
  Activity,
  Eye,
  Server,
  Database,
} from 'lucide-react';

// Lazy-load tab components
const OverviewTab = lazy(() =>
  import('./dashboard/OverviewTab').then((m) => ({ default: m.OverviewTab }))
);
const ObservabilityTab = lazy(() =>
  import('./dashboard/ObservabilityTab').then((m) => ({ default: m.ObservabilityTab }))
);
const InfrastructureTab = lazy(() =>
  import('./dashboard/InfrastructureTab').then((m) => ({ default: m.InfrastructureTab }))
);
const CachePanel = lazy(() =>
  import('./CachePanel').then((m) => ({ default: m.CachePanel }))
);

// ── Tab Loading Fallback ────────────────────────────────────────────
function TabLoadingFallback() {
  return (
    <div className="flex flex-col h-full overflow-y-auto custom-scrollbar px-3 py-2 space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} className="h-16 rounded-lg bg-slate-800/60" />
        ))}
      </div>
      <Skeleton className="h-32 rounded-lg bg-slate-800/40" />
      <Skeleton className="h-24 rounded-lg bg-slate-800/40" />
      <Skeleton className="h-20 rounded-lg bg-slate-800/40" />
    </div>
  );
}

// ── Main DashboardZone ──────────────────────────────────────────────
export function DashboardZone() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-slate-700/50 bg-slate-900/50">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-white">DASHBOARD</h2>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="overview" className="h-full flex flex-col">
          <TabsList className="flex-shrink-0 mx-3 mt-2 bg-slate-800/60 border border-slate-700/30 h-7 p-0.5">
            <TabsTrigger value="overview" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Activity className="h-3 w-3 mr-1" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="observability" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Eye className="h-3 w-3 mr-1" />
              Observability
            </TabsTrigger>
            <TabsTrigger value="infrastructure" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Server className="h-3 w-3 mr-1" />
              Infra
            </TabsTrigger>
            <TabsTrigger value="cache" className="text-[10px] px-2 py-0.5 h-5 data-[state=active]:bg-cyan-600/30 data-[state=active]:text-cyan-300">
              <Database className="h-3 w-3 mr-1" />
              Cache
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="flex-1 overflow-hidden mt-0">
            <Suspense fallback={<TabLoadingFallback />}>
              <OverviewTab />
            </Suspense>
          </TabsContent>
          <TabsContent value="observability" className="flex-1 overflow-hidden mt-0">
            <Suspense fallback={<TabLoadingFallback />}>
              <ObservabilityTab />
            </Suspense>
          </TabsContent>
          <TabsContent value="infrastructure" className="flex-1 overflow-hidden mt-0">
            <Suspense fallback={<TabLoadingFallback />}>
              <InfrastructureTab />
            </Suspense>
          </TabsContent>
          <TabsContent value="cache" className="flex-1 overflow-hidden mt-0">
            <Suspense fallback={<TabLoadingFallback />}>
              <CachePanel />
            </Suspense>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
