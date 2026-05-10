import { NextRequest, NextResponse } from 'next/server';
import type { IntakeResult } from '@/lib/kantorku/types';
import { logger } from '@/lib/kantorku/logger';
import { handleApiError } from '@/lib/kantorku/errors';
import { z } from 'zod';

// ── System Prompt ─────────────────────────────────────────────────
const SYSTEM_PROMPT_INTAKE = `You are the Intake worker of kantorku — a digital office.
Your job is to deeply classify and structure incoming client messages.

Analyze the message carefully and respond with JSON in this EXACT format:
\`\`\`json
{
  "type": "new_request|follow_up|revision|question|feedback",
  "urgency": "low|medium|high|critical",
  "domain": ["web_development", "api", "database", "design", "mobile", "devops", "security", "analytics", "other"],
  "technologies": ["react", "typescript", "python", "postgresql", etc.],
  "summary": "Concise summary of what the client wants",
  "key_requirements": ["specific requirement 1", "specific requirement 2", ...],
  "estimated_complexity": "simple|moderate|complex|very_complex",
  "estimated_workers": ["worker_id_1", "worker_id_2", ...],
  "estimated_duration_ms": 30000
}
\`\`\`

## Classification Guidelines

### Type
- **new_request**: A fresh project or task request
- **follow_up**: Additional info or continuation of a previous request
- **revision**: Request to change something already discussed or contracted
- **question**: Pure inquiry, no task requested
- **feedback**: Feedback on delivered work

### Urgency
- **low**: No deadline, exploratory
- **medium**: Normal project, reasonable timeline
- **high**: Tight deadline, business-critical
- **critical**: Production down, security breach, immediate attention needed

### Domain (can be multiple)
- web_development, api, database, design, mobile, devops, security, analytics, documentation, testing, other

### Estimated Complexity
- **simple**: Single component, straightforward logic
- **moderate**: Multiple components, some integration needed
- **complex**: Multi-system integration, significant architecture
- **very_complex**: Enterprise-level, many interconnected systems

### Estimated Workers
Map the requirements to the most appropriate workers:
- **intake**: Message classification
- **scout**: Research and information gathering
- **sentinel**: Quality assurance
- **coder_backend**: Backend development (APIs, databases, server logic)
- **coder_frontend**: Frontend development (UI, components)
- **coder_wiring**: Integration work (API wiring, WebSocket)
- **verifier_engineer**: Code verification
- **verifier_designer**: Design verification
- **debugger**: Bug fixing
- **auditor**: Security auditing
- **scribe**: Documentation
- **narrator**: Presentations
- **summarizer**: Summarization

### Estimated Duration
- simple: 10000-30000ms
- moderate: 30000-60000ms
- complex: 60000-120000ms
- very_complex: 120000-300000ms

Be thorough but concise. This classification drives the entire orchestration pipeline.`;

// ── Default intake result for fallback ─────────────────────────────
function getDefaultIntake(message: string): IntakeResult {
  return {
    original_message: message,
    type: 'new_request',
    urgency: 'medium',
    domain: [],
    technologies: [],
    summary: message.substring(0, 100),
    key_requirements: [],
    estimated_complexity: 'moderate',
    estimated_workers: [],
    estimated_duration_ms: 30000,
  };
}

// ── Parse JSON from LLM response ─────────────────────────────────
function parseIntakeResponse(text: string): Record<string, unknown> | null {
  try {
    let jsonStr = text;
    if (jsonStr.includes('```json')) {
      jsonStr = jsonStr.split('```json')[1]?.split('```')[0]?.trim() || '';
    } else if (jsonStr.includes('```')) {
      jsonStr = jsonStr.split('```')[1]?.split('```')[0]?.trim() || '';
    }
    const data = JSON.parse(jsonStr.trim());
    return data;
  } catch {
    return null;
  }
}

// ── Validate and normalize intake fields ──────────────────────────
function validateIntake(
  raw: Record<string, unknown>,
  message: string
): IntakeResult {
  const validTypes: IntakeResult['type'][] = [
    'new_request', 'follow_up', 'revision', 'question', 'feedback',
  ];
  const validUrgencies: IntakeResult['urgency'][] = [
    'low', 'medium', 'high', 'critical',
  ];
  const validComplexities: IntakeResult['estimated_complexity'][] = [
    'simple', 'moderate', 'complex', 'very_complex',
  ];
  const validWorkers = [
    'intake', 'scout', 'sentinel', 'coder_backend', 'coder_frontend',
    'coder_wiring', 'verifier_engineer', 'verifier_designer', 'debugger',
    'auditor', 'scribe', 'narrator', 'summarizer',
  ];

  return {
    original_message: message,
    type: validTypes.includes(raw.type as IntakeResult['type'])
      ? (raw.type as IntakeResult['type'])
      : 'new_request',
    urgency: validUrgencies.includes(raw.urgency as IntakeResult['urgency'])
      ? (raw.urgency as IntakeResult['urgency'])
      : 'medium',
    domain: Array.isArray(raw.domain)
      ? raw.domain.filter((d): d is string => typeof d === 'string')
      : [],
    technologies: Array.isArray(raw.technologies)
      ? raw.technologies.filter((t): t is string => typeof t === 'string')
      : [],
    summary: typeof raw.summary === 'string' ? raw.summary : message.substring(0, 100),
    key_requirements: Array.isArray(raw.key_requirements)
      ? raw.key_requirements.filter((r): r is string => typeof r === 'string')
      : [],
    estimated_complexity: validComplexities.includes(
      raw.estimated_complexity as IntakeResult['estimated_complexity']
    )
      ? (raw.estimated_complexity as IntakeResult['estimated_complexity'])
      : 'moderate',
    estimated_workers: Array.isArray(raw.estimated_workers)
      ? raw.estimated_workers.filter((w): w is string =>
          typeof w === 'string' && validWorkers.includes(w)
        )
      : undefined,
    estimated_duration_ms: typeof raw.estimated_duration_ms === 'number'
      ? raw.estimated_duration_ms
      : undefined,
  };
}

// ── Zod Validation Schema ────────────────────────────────────────
const RequestSchema = z.object({
  message: z.string(),
  context: z.array(z.object({ role: z.string(), content: z.string() })).optional(),
});

// ── Route Handler ─────────────────────────────────────────────────
export async function POST(req: NextRequest) {
  const startTime = Date.now();

  try {
    const body = RequestSchema.parse(await req.json());
    const { message, context } = body;

    // Build messages with optional context for follow-up classification
    const messages = [
      { role: 'system' as const, content: SYSTEM_PROMPT_INTAKE },
      ...(context || [])
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-6)
        .map((m) => ({
          role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
          content: m.content,
        })),
      { role: 'user' as const, content: message },
    ];

    // Use z-ai-web-dev-sdk
    const ZAI = (await import('z-ai-web-dev-sdk')).default;
    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
      messages,
      temperature: 0.2, // Low temperature for consistent classification
    });

    const responseText = completion.choices?.[0]?.message?.content || '';

    // Track token usage
    const usage = completion.usage;
    const inputTokens = usage?.prompt_tokens || 0;
    const outputTokens = usage?.completion_tokens || 0;
    const latencyMs = Date.now() - startTime;

    // Parse and validate the intake result
    const parsed = parseIntakeResponse(responseText);
    const intakeResult: IntakeResult = parsed
      ? validateIntake(parsed, message)
      : getDefaultIntake(message);

    return NextResponse.json({
      ...intakeResult,
      _meta: {
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        latency_ms: latencyMs,
        model: completion.model || 'unknown',
      },
    });
  } catch (error: unknown) {
    // For validation errors, return proper error response via handleApiError
    if (typeof error === 'object' && error !== null && 'issues' in error && Array.isArray((error as { issues: unknown }).issues)) {
      return handleApiError(error, 'intake');
    }

    // For other errors, log and return fallback classification
    // Intake is non-critical; the system can proceed with defaults
    logger.error('intake', 'Error', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';

    const fallbackBody = typeof (error as Record<string, unknown>)?.message === 'string'
      ? ((error as Record<string, unknown>).message as string)
      : '';
    const fallbackIntake = getDefaultIntake(fallbackBody || 'unknown message');

    return NextResponse.json({
      ...fallbackIntake,
      _meta: {
        error: errorMessage,
        fallback: true,
        latency_ms: Date.now() - startTime,
      },
    });
  }
}
