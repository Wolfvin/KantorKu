import { NextRequest } from 'next/server';
import type { Contract, IntakeResult, TeamFeedbackRound, ChatApiResponse, InteractiveQuestion } from '@/lib/kantorku/types';
import { logger } from '@/lib/kantorku/logger';
import { handleApiError } from '@/lib/kantorku/errors';
import { z } from 'zod';

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

## Asking Clarifying Questions with Options
When you need to ask the client a clarifying question, you MUST use the interactive question format. This presents clickable options so the client can answer quickly.

Use EXACTLY this format when asking a question:

[ASK]
question: Your question text here?
A: Option A text
B: Option B text
C: Option C text
D: Option D text (optional, add as many as needed)
[/ASK]

You can add any additional explanation or context BEFORE the [ASK] block.

Rules for questions:
- Always provide at least 2 options (A, B, etc.)
- Keep option text concise and clear
- Use this format when you need to understand: technology preferences, design choices, scope decisions, priority levels, architecture decisions
- You may include a brief explanation before the [ASK] block
- Do NOT use this format for rhetorical questions — only when you genuinely need the client's input
- Example scenarios: "Which framework?", "What's the priority?", "Which design approach?", "What's the target audience?"

## Important
- Be professional but friendly — you're the bridge between client and team
- Don't over-ask — if the request is clear enough, proceed to contract
- Always include intake classification in the contract response
- For very simple requests, keep the todo list concise
- For complex requests, break down thoroughly with proper dependencies
- USE the [ASK] format when you need clarification — it creates interactive buttons for the client`;

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

function tryParseQuestion(text: string): {
  question: InteractiveQuestion | null;
  cleanedContent: string;
} {
  const askMatch = text.match(/\[ASK\]([\s\S]*?)\[\/ASK\]/);
  if (!askMatch) return { question: null, cleanedContent: text };

  const askBlock = askMatch[1].trim();
  const lines = askBlock.split('\n').map((l) => l.trim()).filter(Boolean);

  let questionText = '';
  const options: InteractiveQuestion['options'] = [];

  for (const line of lines) {
    const qMatch = line.match(/^question:\s*(.+)/i);
    if (qMatch) {
      questionText = qMatch[1].trim();
      continue;
    }
    const optMatch = line.match(/^([A-Z]):\s*(.+)/);
    if (optMatch) {
      options.push({ label: optMatch[1], text: optMatch[2].trim() });
    }
  }

  if (!questionText || options.length < 2) {
    return { question: null, cleanedContent: text };
  }

  // Remove the [ASK]...[/ASK] block from the content to display
  const cleanedContent = text.replace(/\[ASK\][\s\S]*?\[\/ASK\]/, '').trim();

  return {
    question: {
      id: `q_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      question: questionText,
      options,
      allow_other: true,
      answered: false,
    },
    cleanedContent,
  };
}

// Kept locally: differs from shared.generateId(prefix) — this version hardcodes 'c_' prefix instead of accepting one
function generateId(): string {
  return `c_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

// Kept locally: differs from shared.estimateCost(model, inputTokens, outputTokens) — this version uses 2 params with flat rates instead of model-based rates
function estimateCost(inputTokens: number, outputTokens: number): number {
  // Rough estimate: $0.01 per 1K input tokens, $0.03 per 1K output tokens
  return (inputTokens / 1000) * 0.01 + (outputTokens / 1000) * 0.03;
}

// ── Build the final JSON response from full streamed text ─────────
function buildResponseFromText(
  responseText: string,
  startTime: number,
  inputTokens: number,
  outputTokens: number,
  model: string,
  session_id: string,
  message: string,
  history: Array<{ role: string; content: string }>,
  current_contract: Contract | null,
): Response {
  const totalTokens = inputTokens + outputTokens;
  const costUsd = estimateCost(inputTokens, outputTokens);
  const latencyMs = Date.now() - startTime;

  // Try to parse contract from response
  const { contractData, intakeData } = tryParseContract(responseText);

  if (contractData) {
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

    return new Response(JSON.stringify(apiResponse), {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Try to parse interactive question from response
  const { question: parsedQuestion, cleanedContent } = tryParseQuestion(responseText);

  if (parsedQuestion) {
    const apiResponse: ChatApiResponse & {
      token_usage: Record<string, unknown>;
      cost: Record<string, unknown>;
      latency_ms: number;
      state_hint?: string;
    } = {
      type: 'question',
      content: cleanedContent || parsedQuestion.question,
      question: parsedQuestion,
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
      state_hint: 'clarifying',
    };

    return new Response(JSON.stringify(apiResponse), {
      headers: { 'Content-Type': 'application/json' },
    });
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

  return new Response(JSON.stringify(apiResponse), {
    headers: { 'Content-Type': 'application/json' },
  });
}

// ── Zod Validation Schema ────────────────────────────────────────
const RequestSchema = z.object({
  message: z.string(),
  history: z.array(z.object({ role: z.string(), content: z.string() })).default([]),
  session_id: z.string().default('default'),
  stream: z.boolean().default(false),
  current_contract: z.any().nullable().default(null),
});

// ── Route Handler with Streaming Support ──────────────────────────
export async function POST(req: NextRequest) {
  const startTime = Date.now();

  try {
    const body = RequestSchema.parse(await req.json());
    const {
      message,
      history,
      session_id,
      stream,
    } = body;
    const current_contract = body.current_contract as Contract | null;

    // Build conversation messages with context awareness
    const contextMessage = current_contract
      ? `\n\n[Current Contract Context: "${current_contract.title}" with ${current_contract.todos.length} todos, state: ${current_contract.state}]`
      : '';

    const messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> = [
      { role: 'system', content: SYSTEM_PROMPT_CONDUCTOR + contextMessage },
      ...history
        .filter((h) => h.role === 'user' || h.role === 'assistant')
        .slice(-20)
        .map((h) => ({
          role: (h.role === 'assistant' ? 'assistant' : 'user') as 'user' | 'assistant',
          content: h.content,
        })),
      { role: 'user', content: message },
    ];

    // Use z-ai-web-dev-sdk
    const ZAI = (await import('z-ai-web-dev-sdk')).default;
    const zai = await ZAI.create();

    // ── Streaming Mode ──────────────────────────────────────────
    if (stream) {
      const streamResponse = await zai.chat.completions.create({
        messages,
        temperature: 0.7,
        stream: true,
      });

      const encoder = new TextEncoder();
      let fullText = '';
      let tokenCount = { input: 0, output: 0 };
      let modelName = 'unknown';

      const readable = new ReadableStream({
        async start(controller) {
          try {
            for await (const chunk of streamResponse) {
              const content = chunk.choices?.[0]?.delta?.content || '';
              if (content) {
                fullText += content;
                controller.enqueue(
                  encoder.encode(`data: ${JSON.stringify({ type: 'chunk', content })}\n\n`)
                );
              }
              // Capture usage from the last chunk if available
              if (chunk.usage) {
                tokenCount.input = chunk.usage.prompt_tokens || 0;
                tokenCount.output = chunk.usage.completion_tokens || 0;
              }
              if (chunk.model) {
                modelName = chunk.model;
              }
            }

            // Estimate tokens if not provided by API
            if (tokenCount.input === 0) {
              tokenCount.input = Math.floor(messages.reduce((s, m) => s + m.content.length, 0) / 4);
            }
            if (tokenCount.output === 0) {
              tokenCount.output = Math.floor(fullText.length / 4);
            }

            // Send the final parsed response
            const finalResponse = buildResponseFromText(
              fullText,
              startTime,
              tokenCount.input,
              tokenCount.output,
              modelName,
              session_id,
              message,
              history,
              current_contract,
            );
            const finalJson = await finalResponse.text();

            controller.enqueue(
              encoder.encode(`data: ${JSON.stringify({ type: 'done', response: JSON.parse(finalJson) })}\n\n`)
            );
            controller.close();
          } catch (streamError) {
            logger.error('chat', 'Stream error', streamError);
            controller.enqueue(
              encoder.encode(`data: ${JSON.stringify({ type: 'error', message: streamError instanceof Error ? streamError.message : 'Stream error' })}\n\n`)
            );
            controller.close();
          }
        },
      });

      return new Response(readable, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }

    // ── Non-Streaming Mode (fallback) ───────────────────────────
    const completion = await zai.chat.completions.create({
      messages,
      temperature: 0.7,
    });

    const responseText =
      completion.choices?.[0]?.message?.content ||
      'I apologize, I could not process that. Could you please rephrase?';

    const usage = completion.usage;
    const inputTokens = usage?.prompt_tokens || 0;
    const outputTokens = usage?.completion_tokens || 0;
    const model = completion.model || 'unknown';

    return buildResponseFromText(
      responseText,
      startTime,
      inputTokens,
      outputTokens,
      model,
      session_id,
      message,
      history,
      current_contract,
    );
  } catch (error: unknown) {
    return handleApiError(error, 'chat');
  }
}
