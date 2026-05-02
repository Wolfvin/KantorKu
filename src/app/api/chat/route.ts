import { NextRequest, NextResponse } from 'next/server';

const SYSTEM_PROMPT_UNDERSTAND = `You are the Manager (Conductor) of kantorku — a digital office.

Your job is to understand what the client wants. You can:
1. Ask clarifying questions if the request is ambiguous
2. Draft a contract when you have enough information

A contract should be specific and actionable. Break it into clear todo items.
Each todo should be something a specific worker can execute.

Available workers:
- intake: Message Parser (classifies messages)
- scout: Information Scout (research)
- sentinel: Quality Sentinel (quality assurance)
- coder_backend: Backend Developer (APIs, databases)
- coder_frontend: Frontend Developer (UI components)
- coder_wiring: Integration Engineer (API wiring, WebSocket)
- verifier_engineer: Code Verifier (code quality)
- verifier_designer: Design Verifier (UI/UX quality)
- debugger: Debugger (find and fix bugs)
- auditor: Security Auditor (security and compliance)
- scribe: Documentation Writer (docs and comments)
- narrator: Narrator (presentations)
- summarizer: Summarizer (summaries)

When you're ready to present a contract, respond with JSON:
\`\`\`json
{
  "type": "contract",
  "title": "...",
  "description": "...",
  "todos": [
    {"description": "...", "assigned_to": "suggested_worker_id"},
    ...
  ]
}
\`\`\`

When you need clarification, respond normally (not JSON).
Be professional but friendly. You're the bridge between client and team.`;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { message, history = [], session_id = 'default' } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Build conversation messages
    const messages = [
      { role: 'system', content: SYSTEM_PROMPT_UNDERSTAND },
      ...history.map((h: { role: string; content: string }) => ({
        role: h.role,
        content: h.content,
      })),
      { role: 'user', content: message },
    ];

    // Use z-ai-web-dev-sdk
    const ZAI = (await import('z-ai-web-dev-sdk')).default;
    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
      messages,
      temperature: 0.7,
    });

    const responseText =
      completion.choices?.[0]?.message?.content || 'I apologize, I could not process that.';

    // Try to parse contract from response
    const contractData = tryParseContract(responseText);

    if (contractData) {
      return NextResponse.json({
        type: 'contract_ready',
        contract: {
          id: Math.random().toString(36).substring(2, 14),
          session_id,
          title: contractData.title || 'Untitled Contract',
          description: contractData.description || '',
          todos: (contractData.todos || []).map(
            (t: { description?: string; assigned_to?: string }, i: number) => ({
              id: `todo_${i + 1}`,
              description: t.description || '',
              assigned_to: t.assigned_to || '',
              status: 'pending',
              depends_on: [],
            })
          ),
          state: 'contract_presented',
          client_messages: [...history, { role: 'user', content: message }],
          manager_messages: [{ role: 'assistant', content: responseText }],
          team_feedback_rounds: [],
          team_approved: false,
        },
      });
    }

    return NextResponse.json({
      type: 'manager_message',
      content: responseText,
    });
  } catch (error: unknown) {
    console.error('Chat API error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Failed to process message', details: message },
      { status: 500 }
    );
  }
}

function tryParseContract(text: string): Record<string, unknown> | null {
  try {
    let jsonStr = '';
    if (text.includes('```json')) {
      jsonStr = text.split('```json')[1]?.split('```')[0]?.trim() || '';
    } else if (text.includes('```')) {
      jsonStr = text.split('```')[1]?.split('```')[0]?.trim() || '';
    } else {
      jsonStr = text.trim();
    }
    const data = JSON.parse(jsonStr);
    if (data.type === 'contract' && Array.isArray(data.todos)) {
      return data;
    }
  } catch {
    // Not JSON or not a contract
  }
  return null;
}
