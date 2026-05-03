import { NextRequest, NextResponse } from 'next/server';
import type {
  Contract,
  GroupMessage,
  DiscussionRound,
  BriefingResult,
  BriefingApiResponse,
  MessageType,
} from '@/lib/kantorku/types';
import { logger } from '@/lib/kantorku/logger';

// ── Briefing System Prompt ────────────────────────────────────────
const BRIEFING_MANAGER_PROMPT = `You are the Conductor facilitating a team briefing in the kantorku digital office.

Your job is to:
1. Present the contract to the team
2. Facilitate multi-round discussion
3. Elicit concerns, suggestions, and agreements
4. Drive toward consensus
5. Summarize decisions

After each round, provide:
- A summary of the discussion
- List of decisions made
- Whether consensus has been reached

Format your response as JSON:
\`\`\`json
{
  "summary": "Round summary",
  "decisions": ["decision1", "decision2"],
  "consensus_reached": true/false,
  "next_topics": ["topic if not consensus yet"]
}
\`\`\``;

// ── Worker briefing persona prompt ────────────────────────────────
function getWorkerBriefingPersona(
  workerId: string,
  contract: Contract,
  skillDescription: string
): string {
  const myTodos = contract.todos
    .filter((t) => t.assigned_to === workerId)
    .map((t) => `- [${t.priority || 'medium'}] ${t.description}`)
    .join('\n');

  return `You are ${workerId}, a worker in the kantorku digital office.
Your specialty: ${skillDescription}

Contract: "${contract.title}"
Description: ${contract.description}

Your assigned tasks:
${myTodos || 'No specific tasks assigned yet — you may be consulted for expertise.'}

In the briefing discussion, you should:
- Share your perspective on the tasks
- Raise any concerns about feasibility, dependencies, or timeline
- Suggest improvements or alternatives
- Agree or disagree with proposals

Respond as your worker persona. Be professional but expressive.
Choose your message type: speak, concern, suggestion, agreement, disagreement, question, or info.`;
}

// ── Worker skill map ──────────────────────────────────────────────
const WORKER_SKILLS: Record<string, string> = {
  intake: 'Classify and structure messages',
  scout: 'Research and gather information from external sources',
  sentinel: 'Monitor quality and ensure standards are met',
  coder_backend: 'Implement backend logic, APIs, databases, server-side code',
  coder_frontend: 'Build UI components, pages, and client-side interfaces',
  coder_wiring: 'Wire APIs, integrate services, WebSocket connections',
  verifier_engineer: 'Verify code quality, correctness, and best practices',
  verifier_designer: 'Verify UI/UX design quality and accessibility',
  debugger: 'Find and fix bugs in code',
  auditor: 'Audit security, compliance, and potential vulnerabilities',
  scribe: 'Write documentation, comments, and technical guides',
  narrator: 'Create narratives, presentations, and user-facing content',
  summarizer: 'Summarize discussions, outputs, and key information',
};

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

// ── Route Handler ─────────────────────────────────────────────────
export async function POST(req: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await req.json();
    const {
      contract,
      workers,
      max_rounds = 3,
      session_id = 'default',
    } = body as {
      contract?: Contract;
      workers?: string[];
      max_rounds?: number;
      session_id?: string;
    };

    if (!contract) {
      return NextResponse.json(
        { error: 'Contract is required' },
        { status: 400 }
      );
    }

    // Determine which workers participate
    const involvedWorkers = workers || [
      ...new Set(contract.todos.map((t) => t.assigned_to).filter(Boolean)),
    ];

    if (involvedWorkers.length === 0) {
      return NextResponse.json(
        { error: 'At least one worker must be involved' },
        { status: 400 }
      );
    }

    const ZAI = (await import('z-ai-web-dev-sdk')).default;
    const zai = await ZAI.create();

    const rounds: DiscussionRound[] = [];
    let consensusReached = false;
    const allDecisions: string[] = [];
    const volunteerAssignments: Record<string, string> = {};

    // ── Multi-round Briefing Discussion ──────────────────────────
    for (let roundNum = 1; roundNum <= max_rounds; roundNum++) {
      const roundMessages: GroupMessage[] = [];
      const roundStart = Date.now();

      // Each worker speaks in the round
      for (const workerId of involvedWorkers) {
        try {
          const skill = WORKER_SKILLS[workerId] || 'general tasks';
          const persona = getWorkerBriefingPersona(workerId, contract, skill);

          // Build context from previous rounds
          const previousContext = rounds.length > 0
            ? `\n\nPrevious rounds summary:\n${rounds.map((r) => `Round ${r.round_number}: ${r.summary}`).join('\n')}`
            : '';

          const completion = await zai.chat.completions.create({
            messages: [
              { role: 'system', content: persona + previousContext },
              {
                role: 'user',
                content: roundNum === 1
                  ? 'This is the first round of briefing. Share your initial thoughts, concerns, or suggestions about this contract.'
                  : `This is round ${roundNum}. Previous discussion: ${rounds[roundNum - 2]?.summary || 'N/A'}. Do you have additional thoughts? Can we reach consensus?`,
              },
            ],
            temperature: 0.7,
          });

          const responseText =
            completion.choices?.[0]?.message?.content || 'No comment.';

          // Determine message type from the content
          let messageType: MessageType = 'speak';
          const lower = responseText.toLowerCase();
          if (lower.includes('concern') || lower.includes('worried') || lower.includes('risk')) {
            messageType = 'concern';
          } else if (lower.includes('suggest') || lower.includes('recommend') || lower.includes('could also')) {
            messageType = 'suggestion';
          } else if (lower.includes('agree') || lower.includes('sounds good') || lower.includes('looks great')) {
            messageType = 'agreement';
          } else if (lower.includes('disagree') || lower.includes("don't think") || lower.includes('not a good idea')) {
            messageType = 'disagreement';
          } else if (lower.includes('?')) {
            messageType = 'question';
          }

          const msg: GroupMessage = {
            id: `gm_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            session_id,
            from_id: workerId,
            message_type: messageType,
            content: responseText,
            reply_to: '',
            timestamp: new Date().toISOString(),
            metadata: { round: roundNum },
          };
          roundMessages.push(msg);
        } catch (error) {
          logger.warn('briefing', `Worker ${workerId} failed`, error);
          // Add fallback message
          roundMessages.push({
            id: `gm_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            session_id,
            from_id: workerId,
            message_type: 'speak',
            content: 'Ready to proceed with the contract as planned.',
            reply_to: '',
            timestamp: new Date().toISOString(),
            metadata: { round: roundNum, fallback: true },
          });
        }
      }

      // Manager summarizes the round
      let roundSummary = '';
      let roundDecisions: string[] = [];
      let roundConsensus = false;

      try {
        const workerOutputs = roundMessages
          .map((m) => `[${m.from_id}] (${m.message_type}): ${m.content}`)
          .join('\n');

        const summaryCompletion = await zai.chat.completions.create({
          messages: [
            { role: 'system', content: BRIEFING_MANAGER_PROMPT },
            {
              role: 'user',
              content: `Briefing round ${roundNum} for contract "${contract.title}".

Worker statements:
${workerOutputs}

Please summarize this round, note decisions, and assess consensus.`,
            },
          ],
          temperature: 0.3,
        });

        const summaryText =
          summaryCompletion.choices?.[0]?.message?.content || '';

        const parsed = parseJsonResponse(summaryText);
        if (parsed) {
          roundSummary = (parsed.summary as string) || `Round ${roundNum} discussion completed.`;
          roundDecisions = Array.isArray(parsed.decisions)
            ? (parsed.decisions as string[])
            : [];
          roundConsensus = parsed.consensus_reached === true;
        } else {
          roundSummary = summaryText.substring(0, 200) || `Round ${roundNum} completed.`;
          roundDecisions = [];
          roundConsensus = roundNum >= 2; // Assume consensus after 2 rounds if parsing fails
        }
      } catch {
        roundSummary = `Round ${roundNum}: All ${involvedWorkers.length} workers provided input.`;
        roundDecisions = ['Proceed with current plan'];
        roundConsensus = roundNum >= 2;
      }

      // Build volunteer assignments from agreement messages
      for (const msg of roundMessages) {
        if (msg.message_type === 'agreement' || msg.message_type === 'suggestion') {
          const workerTodos = contract.todos.filter(
            (t) => t.assigned_to === msg.from_id
          );
          if (workerTodos.length > 0) {
            volunteerAssignments[msg.from_id] = workerTodos
              .map((t) => t.description)
              .join('; ');
          }
        }
      }

      allDecisions.push(...roundDecisions);

      rounds.push({
        round_number: roundNum,
        messages: roundMessages,
        summary: roundSummary,
        decisions: roundDecisions,
        consensus_reached: roundConsensus,
      });

      // If consensus reached, stop early
      if (roundConsensus) {
        consensusReached = true;
        break;
      }
    }

    // ── Build Briefing Result ────────────────────────────────────
    const briefingResult: BriefingResult = {
      plan: {
        contract_title: contract.title,
        todos: contract.todos.length,
        workers: involvedWorkers,
      },
      rounds_completed: rounds.length,
      consensus_reached: consensusReached,
      concerns: rounds.flatMap((r) =>
        r.messages
          .filter((m) => m.message_type === 'concern')
          .map((m) => ({ worker_id: m.from_id, content: m.content }))
      ),
      decisions: allDecisions,
      volunteer_assignments: volunteerAssignments,
      estimated_total_time_ms: contract.todos.reduce(
        (sum, t) => sum + (t.estimated_time_ms || 5000),
        0
      ),
    };

    const apiResponse: BriefingApiResponse = {
      rounds,
      consensus_reached: consensusReached,
      decisions: allDecisions,
      volunteer_assignments: volunteerAssignments,
    };

    const latencyMs = Date.now() - startTime;

    return NextResponse.json({
      ...apiResponse,
      briefing: briefingResult,
      _meta: {
        session_id,
        latency_ms: latencyMs,
        rounds_completed: rounds.length,
      },
    });
  } catch (error: unknown) {
    logger.error('briefing', 'Error', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Briefing failed', details: message },
      { status: 500 }
    );
  }
}
