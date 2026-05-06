import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';

// POST /api/library/ask — ask archivist
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { question, top_k, save_to_library } = body;

    // Try Python backend first
    try {
      const resp = await fetch(`${BACKEND_URL}/library/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k, save_to_library }),
        signal: AbortSignal.timeout(30000),
      });
      if (resp.ok) {
        const data = await resp.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    // Standalone mode — use z-ai-web-dev-sdk
    try {
      const ZAI = (await import('z-ai-web-dev-sdk')).default;
      const zai = await ZAI.create();

      const completion = await zai.chat.completions.create({
        messages: [
          {
            role: 'system',
            content: `You are Archivist, the knowledge retrieval AI for KantorKu Library.
Answer questions from the Library's stored knowledge. If you don't have specific library entries to reference, provide your best answer based on general knowledge and note that it's a general answer.
Cite sources using [1], [2] notation when referencing information.
Format: **Answer**: [your answer with citations] | **Confidence**: [high/medium/low]`,
          },
          { role: 'user', content: question },
        ],
        temperature: 0.3,
      });

      const answer = completion.choices?.[0]?.message?.content || 'I could not generate an answer.';

      return NextResponse.json({
        answer,
        sources: [],
        confidence: 0.6,
      });
    } catch {
      return NextResponse.json({
        answer: 'I could not process your question at this time. The backend is unavailable and the standalone AI could not be reached.',
        sources: [],
        confidence: 0,
      });
    }
  } catch (error) {
    return NextResponse.json({ error: 'Failed to ask archivist' }, { status: 500 });
  }
}
