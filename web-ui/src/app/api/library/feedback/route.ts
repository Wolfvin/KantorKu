import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// POST /api/library/feedback — mark helpful/unhelpful
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { entry_id, feedback_type } = body;

    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_id, feedback_type }),
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    // Standalone mode
    return NextResponse.json({
      entry_id,
      feedback_type,
      recorded: true,
    });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to record feedback' }, { status: 500 });
  }
}
