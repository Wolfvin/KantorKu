import { NextRequest, NextResponse } from 'next/server';
import type { ShelfNode } from '@/lib/kantorku/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// GET /api/library/shelves — shelf tree
export async function GET(req: NextRequest) {
  try {
    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/shelves`, {
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    // Standalone mode — return default shelf taxonomy
    const defaultShelves: ShelfNode[] = [
      {
        name: 'Engineering',
        path: ['Engineering'],
        entry_count: 0,
        quality_avg: 0,
        last_updated: null,
        children: [
          { name: 'Backend', path: ['Engineering', 'Backend'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
          { name: 'Frontend', path: ['Engineering', 'Frontend'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
          { name: 'DevOps', path: ['Engineering', 'DevOps'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
          { name: 'Security', path: ['Engineering', 'Security'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
        ],
      },
      {
        name: 'Mathematics',
        path: ['Mathematics'],
        entry_count: 0,
        quality_avg: 0,
        last_updated: null,
        children: [
          { name: 'Algebra', path: ['Mathematics', 'Algebra'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
          { name: 'Statistics', path: ['Mathematics', 'Statistics'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
        ],
      },
      {
        name: 'Science',
        path: ['Science'],
        entry_count: 0,
        quality_avg: 0,
        last_updated: null,
        children: [
          { name: 'Physics', path: ['Science', 'Physics'], entry_count: 0, quality_avg: 0, last_updated: null, children: [] },
        ],
      },
      {
        name: 'Business',
        path: ['Business'],
        entry_count: 0,
        quality_avg: 0,
        last_updated: null,
        children: [],
      },
      {
        name: 'Philosophy',
        path: ['Philosophy'],
        entry_count: 0,
        quality_avg: 0,
        last_updated: null,
        children: [],
      },
    ];

    return NextResponse.json({ shelves: defaultShelves });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to get shelves' }, { status: 500 });
  }
}
