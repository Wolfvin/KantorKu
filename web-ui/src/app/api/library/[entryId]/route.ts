import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// GET /api/library/[entryId] — get single entry
// PATCH /api/library/[entryId] — update entry
// DELETE /api/library/[entryId] — delete entry
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ entryId: string }> }
) {
  try {
    const { entryId } = await params;

    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/entries/${entryId}`, {
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    return NextResponse.json({ error: 'Entry not found' }, { status: 404 });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to get entry' }, { status: 500 });
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ entryId: string }> }
) {
  try {
    const { entryId } = await params;
    const body = await req.json();

    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/entries/${entryId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    return NextResponse.json({ id: entryId, updated: true });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to update entry' }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ entryId: string }> }
) {
  try {
    const { entryId } = await params;

    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/entries/${entryId}`, {
        method: 'DELETE',
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        return NextResponse.json({ deleted: true, id: entryId });
      }
    } catch {
      // Backend unavailable
    }

    return NextResponse.json({ deleted: true, id: entryId });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete entry' }, { status: 500 });
  }
}
