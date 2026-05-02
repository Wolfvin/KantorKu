import { NextRequest, NextResponse } from 'next/server';

const SYSTEM_PROMPT_INTAKE = `You are the Intake worker of kantorku — a digital office.
Your job is to classify and structure incoming client messages.

Analyze the message and respond with JSON:
\`\`\`json
{
  "type": "new_request|follow_up|revision|question|feedback",
  "urgency": "low|medium|high|critical",
  "domain": ["web_development", "api", "database", etc.],
  "technologies": ["react", "python", etc.],
  "summary": "Brief summary of what the client wants",
  "key_requirements": ["req1", "req2", ...],
  "estimated_complexity": "simple|moderate|complex|very_complex"
}
\`\`\`

Be thorough but concise. This classification helps the Conductor understand the request.`;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { message } = body;

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Use z-ai-web-dev-sdk
    const ZAI = (await import('z-ai-web-dev-sdk')).default;
    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'system', content: SYSTEM_PROMPT_INTAKE },
        { role: 'user', content: message },
      ],
      temperature: 0.3,
    });

    const responseText =
      completion.choices?.[0]?.message?.content || '';

    // Parse the intake result
    let intakeResult;
    try {
      let jsonStr = responseText;
      if (jsonStr.includes('```json')) {
        jsonStr = jsonStr.split('```json')[1]?.split('```')[0]?.trim() || '';
      } else if (jsonStr.includes('```')) {
        jsonStr = jsonStr.split('```')[1]?.split('```')[0]?.trim() || '';
      }
      intakeResult = JSON.parse(jsonStr);
    } catch {
      intakeResult = {
        type: 'new_request',
        urgency: 'medium',
        domain: [],
        technologies: [],
        summary: message.substring(0, 100),
        key_requirements: [],
        estimated_complexity: 'moderate',
      };
    }

    return NextResponse.json({
      original_message: message,
      ...intakeResult,
    });
  } catch (error: unknown) {
    console.error('Intake API error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Intake failed', details: message },
      { status: 500 }
    );
  }
}
