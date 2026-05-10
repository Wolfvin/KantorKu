import { NextRequest, NextResponse } from 'next/server';
import type { LibraryStats } from '@/lib/kantorku/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// GET /api/library/stats — library statistics
export async function GET(req: NextRequest) {
  try {
    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/stats`, {
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    // Standalone mode — return default stats
    const stats: LibraryStats = {
      total_entries: 0,
      entries_by_type: { knowledge: 0, solution: 0, qa_pair: 0, procedure: 0 },
      quality_distribution: [
        { range: '0.0-0.2', count: 0 },
        { range: '0.2-0.4', count: 0 },
        { range: '0.4-0.6', count: 0 },
        { range: '0.6-0.8', count: 0 },
        { range: '0.8-1.0', count: 0 },
      ],
      top_shelves: [],
      trending_entries: [],
      total_usage: 0,
      avg_quality: 0,
      vector_coverage: 0,
      recent_entries: [],
    };

    return NextResponse.json(stats);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to get stats' }, { status: 500 });
  }
}
