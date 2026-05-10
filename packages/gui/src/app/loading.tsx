import { Skeleton } from '@/components/ui/skeleton';

export default function Loading() {
  return (
    <div className="h-screen w-screen bg-slate-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8 rounded-full bg-cyan-500/20" />
          <Skeleton className="h-6 w-32 bg-slate-800" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-64 w-80 rounded-lg bg-slate-800/60" />
          <Skeleton className="h-64 w-96 rounded-lg bg-slate-800/60" />
          <Skeleton className="h-64 w-72 rounded-lg bg-slate-800/60" />
        </div>
        <p className="text-sm text-slate-600 font-mono animate-pulse">Initializing KantorKu...</p>
      </div>
    </div>
  );
}
