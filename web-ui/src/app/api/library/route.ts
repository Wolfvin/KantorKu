import { NextRequest, NextResponse } from 'next/server';
import type { LibraryEntry, EntryType } from '@/lib/kantorku/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// In-memory store for standalone mode
let entriesStore: LibraryEntry[] = [];

function generateId(): string {
  return `lib_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

// GET /api/library — list entries
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const type = searchParams.get('type');
    const shelf = searchParams.get('shelf');
    const minQuality = parseFloat(searchParams.get('min_quality') || '0');
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = parseInt(searchParams.get('offset') || '0');

    // Try Python backend first
    try {
      const params = new URLSearchParams();
      if (type) params.set('type', type);
      if (shelf) params.set('shelf', shelf);
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      if (minQuality > 0) params.set('min_quality', String(minQuality));

      const resp = await fetch(`${BACKEND_URL}/library/entries?${params.toString()}`, {
        signal: AbortSignal.timeout(3000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable, fall through to standalone mode
    }

    // Standalone mode — use in-memory store
    let filtered = [...entriesStore];
    if (type) filtered = filtered.filter((e) => e.entry_type === type);
    if (shelf) filtered = filtered.filter((e) => e.shelf_path.join('/').includes(shelf));
    if (minQuality > 0) filtered = filtered.filter((e) => e.quality_score >= minQuality);
    filtered = filtered.slice(offset, offset + limit);

    return NextResponse.json({ entries: filtered, total: entriesStore.length });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to list entries' }, { status: 500 });
  }
}

// POST /api/library — ingest entry
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { content, title, source, user_hint, classification } = body;

    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, title, source, user_hint }),
        signal: AbortSignal.timeout(10000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable, fall through to standalone mode
    }

    // Standalone mode — create entry with classification
    const entryType: EntryType = classification?.entry_type || 'knowledge';
    const now = new Date().toISOString();
    const entry: LibraryEntry = {
      id: generateId(),
      created_at: now,
      updated_at: now,
      source: source || 'manual',
      title: title || '',
      content: content || '',
      summary: classification?.summary || (content ? content.substring(0, 200) + '...' : ''),
      keywords: classification?.keywords || [],
      entry_type: entryType,
      domain: classification?.domain || 'web_text',
      lang: 'en',
      shelf_path: classification?.shelf_path || [],
      shelf_confidence: classification?.shelf_confidence || 0.3,
      related_ids: [],
      supersedes_id: null,
      solution_for: null,
      quality_score: classification?.quality_initial || 0.5,
      verified: false,
      usage_count: 0,
      was_helpful: 0,
      was_unhelpful: 0,
      origin_session_id: null,
      origin_worker_id: null,
      origin_task_id: null,
      problem_description: entryType === 'solution' ? content?.substring(0, 500) || null : null,
      failed_attempts: [],
      solution_code: null,
      verification_result: null,
      question: entryType === 'qa_pair' ? title || null : null,
      answer: entryType === 'qa_pair' ? content || null : null,
      source_entry_ids: [],
      steps: entryType === 'procedure' ? [] : [],
    };

    entriesStore.push(entry);

    return NextResponse.json({
      entry,
      classification: classification || {
        entry_type: entryType,
        keywords: [],
        shelf_path: [],
        quality_initial: 0.5,
        domain: 'web_text',
        shelf_confidence: 0.3,
        summary: entry.summary,
      },
    });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to ingest entry' }, { status: 500 });
  }
}
