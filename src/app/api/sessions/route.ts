import { NextRequest, NextResponse } from 'next/server';
import type { Session, ContractState } from '@/lib/kantorku/types';
import { logger } from '@/lib/kantorku/logger';

// ── In-memory session store ───────────────────────────────────────
// In production, this would be backed by a database
const sessions = new Map<string, Session & { contract_title?: string; messages?: Array<{ role: string; content: string }> }>();

// ── GET: List all sessions ────────────────────────────────────────
export async function GET() {
  try {
    const sessionList = Array.from(sessions.values()).map((s) => ({
      session_id: s.session_id,
      state: s.state,
      contract_title: s.contract_title || '',
      created_at: s.created_at,
      updated_at: s.updated_at,
      message_count: s.message_count,
      total_cost: s.total_cost,
    }));

    return NextResponse.json({
      sessions: sessionList,
      total: sessionList.length,
    });
  } catch (error: unknown) {
    logger.error('sessions', 'GET error', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Failed to list sessions', details: message },
      { status: 500 }
    );
  }
}

// ── POST: Create a new session ────────────────────────────────────
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { title, initial_message } = body as {
      title?: string;
      initial_message?: string;
    };

    const sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const now = new Date().toISOString();

    const newSession: Session & {
      contract_title?: string;
      messages?: Array<{ role: string; content: string }>;
    } = {
      session_id: sessionId,
      state: 'idle' as ContractState,
      contract_title: title || 'New Session',
      created_at: now,
      updated_at: now,
      message_count: initial_message ? 1 : 0,
      total_cost: 0,
      messages: initial_message
        ? [{ role: 'user', content: initial_message }]
        : [],
    };

    sessions.set(sessionId, newSession);

    return NextResponse.json(
      {
        session: {
          session_id: newSession.session_id,
          state: newSession.state,
          contract_title: newSession.contract_title,
          created_at: newSession.created_at,
          updated_at: newSession.updated_at,
          message_count: newSession.message_count,
          total_cost: newSession.total_cost,
        },
      },
      { status: 201 }
    );
  } catch (error: unknown) {
    logger.error('sessions', 'POST error', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Failed to create session', details: message },
      { status: 500 }
    );
  }
}
