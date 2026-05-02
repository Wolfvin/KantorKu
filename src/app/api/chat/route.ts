import { NextRequest, NextResponse } from 'next/server';
import type { Contract, IntakeResult, TeamFeedbackRound, ChatApiResponse } from '@/lib/kantorku/types';

// ── System Prompt ─────────────────────────────────────────────────
const SYSTEM_PROMPT_CONDUCTOR = `You are the Manager (Conductor) of kantorku — a digital office where specialized AI workers collaborate to deliver projects.

## Your Role
You are the single point of contact between the client and the team. You must:
1. **Understand** the client's request through multi-turn conversation
2. **Classify** the request internally (urgency, complexity, domain)
3. **Consult** with your team before presenting a contract
4. **Draft** a detailed contract with specific todos assigned to workers
5. **Handle** revision requests professionally

## Available Workers
- **intake** 📋: Message Parser — classifies and structures incoming messages
- **scout** 🔍: Information Scout — researches and gathers information
- **sentinel** 🛡️: Quality Sentinel — ensures quality and logs lessons
- **coder_backend** ⚙️: Backend Developer — implements APIs, databases, server logic
- **coder_frontend** 🎨: Frontend Developer — builds UI components and interfaces
- **coder_wiring** 🔌: Integration Engineer — wires APIs, WebSocket, MCP integrations
- **verifier_engineer** ✅: Code Verifier — verifies code quality and correctness
- **verifier_designer** 👁️: Design Verifier — verifies UI/UX design quality
- **debugger** 🐛: Debugger — finds and fixes bugs
- **auditor** 🔒: Security Auditor — audits security and compliance
- **scribe** 📝: Documentation Writer — writes documentation and comments
- **narrator** 📖: Narrator — creates narratives and presentations
- **summarizer** 📊: Summarizer — summarizes discussions and outputs

## Conversation Phases

### Phase 1: Understanding
- Ask clarifying questions if the request is ambiguous
- Understand the scope, constraints, and preferences
- Be conversational and professional

### Phase 2: Internal Classification
When you have enough info, internally classify:
- urgency: low | medium | high | critical
- complexity: simple | moderate | complex | very_complex
- domain: [web_development, api, database, design, etc.]
- workers_needed: list of worker IDs that would be involved

### Phase 3: Team Consultation
Before drafting a contract, indicate you're consulting the team. Say something like:
"Let me consult with the team to put together a solid plan for you."

### Phase 4: Contract Drafting
When ready to present a contract, respond with EXACTLY this JSON format (no other text):
\`\`\`json
{
  "type": "contract",
  "title": "Descriptive contract title",
  "description": "Detailed description of what will be delivered",
  "intake": {
    "type": "new_request",
    "urgency": "medium",
    "domain": ["web_development"],
    "technologies": ["react", "typescript"],
    "summary": "Brief summary",
    "key_requirements": ["req1", "req2"],
    "estimated_complexity": "moderate",
    "estimated_workers": ["coder_frontend", "coder_backend"],
    "estimated_duration_ms": 30000
  },
  "todos": [
    {
      "description": "Specific task description",
      "assigned_to": "worker_id",
      "depends_on": [],
      "priority": "medium",
      "estimated_time_ms": 5000
    }
  ]
}
\`\`\`

## Contract Drafting Rules
- Each todo must be specific and actionable — a worker should know exactly what to do
- Assign each todo to the MOST appropriate worker based on their specialty
- Use depends_on to create execution order (use todo indices like "0", "1", etc.)
- Include verification todos (assign to verifier_engineer or verifier_designer)
- Include documentation todos (assign to scribe) for complex projects
- Estimate time in milliseconds (rough estimates are fine)
- Set priority: low | medium | high | critical

## Revision Handling
If the client wants changes to a contract:
- Acknowledge the feedback professionally
- Revise the contract with the requested changes
- Present the updated contract in the same JSON format

## Important
- Be professional but friendly — you're the bridge between client and team
- Don't over-ask — if the request is clear enough, proceed to contract
- Always include intake classification in the contract response
- For very simple requests, keep the todo list concise
- For complex requests, break down thoroughly with proper dependencies`;

// ── Helpers ───────────────────────────────────────────────────────
function tryParseContract(text: string): {
  contractData: Record<string, unknown> | null;
  intakeData: Record<string, unknown> | null;
} {
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
      return {
        contractData: data,
        intakeData: (data.intake as Record<string, unknown>) || null,
      };
    }
  } catch {
    // Not JSON or not a contract
  }
  return { contractData: null, intakeData: null };
}

function generateId(): string {
  return `c_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

// ── Cost estimation (rough) ───────────────────────────────────────
function estimateCost(inputTokens: number, outputTokens: number): number {
  // Rough estimate: $0.01 per 1K input tokens, $0.03 per 1K output tokens
  return (inputTokens / 1000) * 0.01 + (outputTokens / 1000) * 0.03;
}

// ── Route Handler ─────────────────────────────────────────────────
export async function POST(req: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await req.json();
    const {
      message,
      history = [],
      session_id = 'default',
      current_contract = null,
    } = body as {
      message?: string;
      history?: Array<{ role: string; content: string }>;
      session_id?: string;
      current_contract?: Contract | null;
    };

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      );
    }

    // Build conversation messages with context awareness
    const contextMessage = current_contract
      ? `\n\n[Current Contract Context: "${current_contract.title}" with ${current_contract.todos.length} todos, state: ${current_contract.state}]`
      : '';

    const messages = [
      { role: 'system' as const, content: SYSTEM_PROMPT_CONDUCTOR + contextMessage },
      ...history
        .filter((h) => h.role === 'user' || h.role === 'assistant')
        .slice(-20) // Keep last 20 messages for context window
        .map((h) => ({
          role: h.role === 'assistant' ? 'assistant' : 'user',
          content: h.content,
        })),
      { role: 'user' as const, content: message },
    ];

    // Use z-ai-web-dev-sdk
    const ZAI = (await import('z-ai-web-dev-sdk')).default;
    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
      messages,
      temperature: 0.7,
    });

    const responseText =
      completion.choices?.[0]?.message?.content ||
      'I apologize, I could not process that. Could you please rephrase?';

    // Track token usage from API response
    const usage = completion.usage;
    const inputTokens = usage?.prompt_tokens || 0;
    const outputTokens = usage?.completion_tokens || 0;
    const totalTokens = usage?.total_tokens || inputTokens + outputTokens;
    const costUsd = estimateCost(inputTokens, outputTokens);
    const latencyMs = Date.now() - startTime;
    const model = completion.model || 'unknown';

    // Try to parse contract from response
    const { contractData, intakeData } = tryParseContract(responseText);

    if (contractData) {
      // Build contract from parsed data
      const todos = (contractData.todos as Array<Record<string, unknown>> || []).map(
        (t, i) => ({
          id: `todo_${i + 1}`,
          description: (t.description as string) || '',
          assigned_to: (t.assigned_to as string) || '',
          status: 'pending' as const,
          depends_on: (t.depends_on as string[]) || [],
          priority: (t.priority as 'low' | 'medium' | 'high' | 'critical') || 'medium',
          estimated_time_ms: (t.estimated_time_ms as number) || undefined,
        })
      );

      // Build intake result
      const intake: IntakeResult = intakeData
        ? {
            original_message: message,
            type: (intakeData.type as IntakeResult['type']) || 'new_request',
            urgency: (intakeData.urgency as IntakeResult['urgency']) || 'medium',
            domain: (intakeData.domain as string[]) || [],
            technologies: (intakeData.technologies as string[]) || [],
            summary: (intakeData.summary as string) || '',
            key_requirements: (intakeData.key_requirements as string[]) || [],
            estimated_complexity:
              (intakeData.estimated_complexity as IntakeResult['estimated_complexity']) || 'moderate',
            estimated_workers: (intakeData.estimated_workers as string[]) || undefined,
            estimated_duration_ms:
              (intakeData.estimated_duration_ms as number) || undefined,
          }
        : {
            original_message: message,
            type: 'new_request',
            urgency: 'medium',
            domain: [],
            technologies: [],
            summary: message.substring(0, 100),
            key_requirements: [],
            estimated_complexity: 'moderate',
          };

      const contract: Contract = {
        id: generateId(),
        session_id,
        title: (contractData.title as string) || 'Untitled Contract',
        description: (contractData.description as string) || '',
        todos,
        state: 'contract_presented',
        client_messages: [...history, { role: 'user', content: message }],
        manager_messages: [{ role: 'assistant', content: responseText }],
        team_feedback_rounds: [],
        team_approved: false,
        approval_gates: [
          {
            id: 'gate_client_approval',
            gate_type: 'client_approval',
            status: 'pending',
            approver: 'client',
          },
          {
            id: 'gate_team_review',
            gate_type: 'team_review',
            status: 'pending',
            approver: 'team',
          },
        ],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      const apiResponse: ChatApiResponse & {
        token_usage: Record<string, unknown>;
        cost: Record<string, unknown>;
        latency_ms: number;
      } = {
        type: 'contract_ready',
        contract,
        intake,
        token_usage: {
          input_tokens: inputTokens,
          output_tokens: outputTokens,
          total_tokens: totalTokens,
          model,
        },
        cost: {
          cost_usd: costUsd,
          latency_ms: latencyMs,
        },
        latency_ms: latencyMs,
      };

      return NextResponse.json(apiResponse);
    }

    // Check if the response indicates team consultation
    const isTeamConsult =
      responseText.toLowerCase().includes('consult') ||
      responseText.toLowerCase().includes('team') ||
      responseText.toLowerCase().includes('discuss with');

    // Regular manager message
    const apiResponse: ChatApiResponse & {
      token_usage: Record<string, unknown>;
      cost: Record<string, unknown>;
      latency_ms: number;
      state_hint?: string;
    } = {
      type: isTeamConsult ? 'team_consult' : 'manager_message',
      content: responseText,
      token_usage: {
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        total_tokens: totalTokens,
        model,
      },
      cost: {
        cost_usd: costUsd,
        latency_ms: latencyMs,
      },
      latency_ms: latencyMs,
      state_hint: isTeamConsult ? 'team_consult' : 'clarifying',
    };

    return NextResponse.json(apiResponse);
  } catch (error: unknown) {
    console.error('[Chat API] Error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const isTimeout = errorMessage.includes('timeout') || errorMessage.includes('ETIMEDOUT');
    const isRateLimit = errorMessage.includes('429') || errorMessage.includes('rate');

    return NextResponse.json(
      {
        error: 'Failed to process message',
        details: errorMessage,
        type: isTimeout ? 'timeout' : isRateLimit ? 'rate_limit' : 'internal_error',
        retry_after_ms: isRateLimit ? 5000 : undefined,
      },
      { status: isRateLimit ? 429 : isTimeout ? 504 : 500 }
    );
  }
}
