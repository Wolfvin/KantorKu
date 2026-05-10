import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// In-memory reference (separate from main route store, but sufficient for standalone demo)
const demoEntries: Array<{
  id: string;
  title: string;
  content: string;
  keywords: string[];
  entry_type: string;
  quality_score: number;
}> = [];

// GET /api/library/search — search entries
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const query = searchParams.get('q') || '';
    const type = searchParams.get('type') || '';
    const minQuality = parseFloat(searchParams.get('min_quality') || '0');
    const limit = parseInt(searchParams.get('limit') || '20');

    // Try Python backend first
    try {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (type) params.set('type', type);
      params.set('min_quality', String(minQuality));
      params.set('limit', String(limit));

      const resp = await fetch(`${BACKEND_URL}/library/search?${params.toString()}`, {
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    // Standalone mode — simple text search
    const results = demoEntries
      .filter((e) => {
        if (type && e.entry_type !== type) return false;
        if (e.quality_score < minQuality) return false;
        if (!query) return true;
        const q = query.toLowerCase();
        return (
          e.title.toLowerCase().includes(q) ||
          e.content.toLowerCase().includes(q) ||
          e.keywords.some((k) => k.toLowerCase().includes(q))
        );
      })
      .map((entry) => ({
        entry,
        relevance: query ? (entry.title.toLowerCase().includes(query.toLowerCase()) ? 0.9 : 0.5) : 0,
      }))
      .slice(0, limit);

    return NextResponse.json({ results, total: results.length });
  } catch (error) {
    return NextResponse.json({ error: 'Search failed' }, { status: 500 });
  }
}
