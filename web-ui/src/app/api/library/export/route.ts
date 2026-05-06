import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// GET /api/library/export — export entries
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const format = searchParams.get('format') || 'json';
    const qualityThreshold = parseFloat(searchParams.get('quality_threshold') || '0');

    // Try Python backend first
    try {
      const params = new URLSearchParams();
      params.set('format', format);
      if (qualityThreshold > 0) params.set('quality_threshold', String(qualityThreshold));

      const resp = await fetch(`${BACKEND_URL}/library/export?${params.toString()}`, {
        signal: AbortSignal.timeout(15000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    // Standalone mode — return empty export
    return NextResponse.json({
      format,
      entries: [],
      count: 0,
      quality_threshold: qualityThreshold,
    });
  } catch (error) {
    return NextResponse.json({ error: 'Export failed' }, { status: 500 });
  }
}
