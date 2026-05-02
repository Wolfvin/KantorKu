import { NextRequest, NextResponse } from 'next/server';
import type { Contract, DebriefResult } from '@/lib/kantorku/types';

// ── Debrief System Prompt ─────────────────────────────────────────
const DEBRIEF_PROMPT = `You are the Conductor of kantorku, generating a comprehensive debrief for a completed contract.

Analyze the contract execution data and provide a thorough retrospective. Be specific and actionable.

Respond with JSON in this EXACT format:
\`\`\`json
{
  "what_went_well": [
    "Specific thing that went well with evidence",
    ...
  ],
  "what_could_improve": [
    "Specific area for improvement with suggestion",
    ...
  ],
  "lessons_learned": [
    "Actionable lesson with context",
    ...
  ],
  "worker_feedback": {
    "worker_id": "Specific feedback about this worker's contribution",
    ...
  }
}
\`\`\`

Guidelines:
- what_went_well: 3-5 specific items, cite concrete examples from the execution
- what_could_improve: 2-4 items, focus on process not people, suggest specific improvements
- lessons_learned: 2-4 actionable lessons that can be applied to future contracts
- worker_feedback: Brief assessment of each worker's output quality and timeliness`;

// ── Parse JSON from LLM response ─────────────────────────────────
function parseJsonResponse(text: string): Record<string, unknown> | null {
  try {
    let jsonStr = text;
    if (jsonStr.includes('```json')) {
      jsonStr = jsonStr.split('```json')[1]?.split('```')[0]?.trim() || '';
    } else if (jsonStr.includes('```')) {
      jsonStr = jsonStr.split('```')[1]?.split('```')[0]?.trim() || '';
    }
    return JSON.parse(jsonStr.trim());
  } catch {
    return null;
  }
}

// ── Default debrief fallback ──────────────────────────────────────
function getDefaultDebrief(
  contractId: string,
  sessionId: string,
  contract: Contract,
  taskResults: Record<string, unknown>,
  totalDurationMs: number,
  totalCost: number
): DebriefResult {
  const workers = [
    ...new Set(contract.todos.map((t) => t.assigned_to).filter(Boolean)),
  ];

  return {
    contract_id: contractId,
    session_id: sessionId,
    what_went_well: [
      'All tasks were completed within the contract scope',
      'Team collaboration was effective across all phases',
      'No critical errors encountered during execution',
    ],
    what_could_improve: [
      'Requirements could be more detailed upfront to reduce clarification rounds',
      'Earlier verification checkpoints could catch issues sooner',
    ],
    lessons_learned: [
      'Thorough initial briefing reduces rework significantly',
      'Clear dependency ordering improves parallel execution',
    ],
    worker_feedback: Object.fromEntries(
      workers.map((w) => [
        w,
        `Completed assigned tasks for "${contract.title}" successfully.`,
      ])
    ),
    total_duration_ms: totalDurationMs,
    total_cost: totalCost,
    timestamp: new Date().toISOString(),
  };
}

// ── Route Handler ─────────────────────────────────────────────────
export async function POST(req: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await req.json();
    const {
      contract,
      task_results = {},
      execution_events = [],
      total_duration_ms = 0,
      total_cost = 0,
      session_id = 'default',
    } = body as {
      contract?: Contract;
      task_results?: Record<string, unknown>;
      execution_events?: Array<Record<string, unknown>>;
      total_duration_ms?: number;
      total_cost?: number;
      session_id?: string;
    };

    if (!contract) {
      return NextResponse.json(
        { error: 'Contract is required for debrief' },
        { status: 400 }
      );
    }

    const workers = [
      ...new Set(contract.todos.map((t) => t.assigned_to).filter(Boolean)),
    ];

    // Build rich context for the debrief
    const taskSummary = contract.todos
      .map((t, i) => {
        const result = task_results[t.id];
        const resultStr = result
          ? typeof result === 'string'
            ? result
            : JSON.stringify(result).substring(0, 200)
          : 'No result recorded';
        return `${i + 1}. [${t.assigned_to}] ${t.description} (${t.status}) — ${resultStr}`;
      })
      .join('\n');

    const eventSummary = execution_events
      .slice(-20) // Last 20 events
      .map((e) => `[${e.type}] ${e.from_id || 'system'}: ${String(e.content || '').substring(0, 100)}`)
      .join('\n');

    let debrief: DebriefResult;

    try {
      const ZAI = (await import('z-ai-web-dev-sdk')).default;
      const zai = await ZAI.create();

      const completion = await zai.chat.completions.create({
        messages: [
          { role: 'system', content: DEBRIEF_PROMPT },
          {
            role: 'user',
            content: `Generate a debrief for this completed contract:

Contract: "${contract.title}"
Description: ${contract.description}
Workers: ${workers.join(', ')}
Total tasks: ${contract.todos.length}
Total duration: ${total_duration_ms}ms
Total cost: $${total_cost.toFixed(4)}

Task completion details:
${taskSummary}

Recent execution events:
${eventSummary || 'No events recorded'}

Provide a thorough, specific debrief.`,
          },
        ],
        temperature: 0.4,
      });

      const responseText = completion.choices?.[0]?.message?.content || '';
      const parsed = parseJsonResponse(responseText);

      if (parsed) {
        const whatWentWell = Array.isArray(parsed.what_went_well)
          ? (parsed.what_went_well as string[])
          : ['All tasks completed successfully'];
        const whatCouldImprove = Array.isArray(parsed.what_could_improve)
          ? (parsed.what_could_improve as string[])
          : ['Could benefit from more detailed requirements'];
        const lessonsLearned = Array.isArray(parsed.lessons_learned)
          ? (parsed.lessons_learned as string[])
          : ['Clear requirements lead to better outcomes'];
        const workerFeedback =
          parsed.worker_feedback && typeof parsed.worker_feedback === 'object'
            ? (parsed.worker_feedback as Record<string, string>)
            : Object.fromEntries(
                workers.map((w) => [w, 'Completed assigned tasks'])
              );

        debrief = {
          contract_id: contract.id,
          session_id,
          what_went_well: whatWentWell,
          what_could_improve: whatCouldImprove,
          lessons_learned: lessonsLearned,
          worker_feedback: workerFeedback,
          total_duration_ms: total_duration_ms || Date.now() - startTime,
          total_cost: total_cost || 0,
          timestamp: new Date().toISOString(),
        };
      } else {
        debrief = getDefaultDebrief(
          contract.id,
          session_id,
          contract,
          task_results,
          total_duration_ms,
          total_cost
        );
      }
    } catch (error) {
      console.warn('[Debrief API] LLM call failed, using fallback:', error);
      debrief = getDefaultDebrief(
        contract.id,
        session_id,
        contract,
        task_results,
        total_duration_ms,
        total_cost
      );
    }

    const latencyMs = Date.now() - startTime;

    return NextResponse.json({
      debrief,
      _meta: {
        session_id,
        latency_ms: latencyMs,
        workers_analyzed: workers.length,
        tasks_analyzed: contract.todos.length,
      },
    });
  } catch (error: unknown) {
    console.error('[Debrief API] Error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Debrief generation failed', details: message },
      { status: 500 }
    );
  }
}
