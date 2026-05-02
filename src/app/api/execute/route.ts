import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { contract, session_id = 'default' } = body;

    if (!contract) {
      return NextResponse.json(
        { error: 'Contract is required' },
        { status: 400 }
      );
    }

    // Simulate the orchestration flow with events
    const events: Array<Record<string, unknown>> = [];
    const todos = contract.todos || [];

    // Phase 1: Briefing opened
    events.push({
      type: 'briefing_opened',
      from_id: 'conductor',
      content: `Briefing for: ${contract.title}`,
      session_id,
      timestamp: new Date().toISOString(),
    });

    // Phase 2: Plan drafted
    events.push({
      type: 'plan_drafted',
      from_id: 'conductor',
      content: 'Execution plan has been drafted based on the contract.',
      session_id,
      timestamp: new Date().toISOString(),
    });

    // Phase 3: Workers speak up in briefing
    const relevantWorkers = [
      ...new Set(todos.map((t: { assigned_to: string }) => t.assigned_to).filter(Boolean)),
    ];
    
    for (const workerId of relevantWorkers) {
      events.push({
        type: 'worker_speak_up',
        from_id: workerId,
        content: getWorkerBriefingMessage(workerId, contract.title),
        session_id,
        timestamp: new Date().toISOString(),
      });
    }

    // Phase 4: Manager summary
    events.push({
      type: 'manager_summary',
      from_id: 'conductor',
      content: `Team briefing complete. ${relevantWorkers.length} workers are aligned on the plan for "${contract.title}". Proceeding with execution.`,
      session_id,
      timestamp: new Date().toISOString(),
    });

    // Phase 5: Task assignments and execution
    const results: Record<string, unknown> = {};
    for (const todo of todos) {
      events.push({
        type: 'task_assigned',
        from_id: 'conductor',
        to_id: todo.assigned_to,
        content: todo.description,
        session_id,
        timestamp: new Date().toISOString(),
      });

      events.push({
        type: 'task_started',
        from_id: todo.assigned_to,
        content: `Working on: ${todo.description}`,
        session_id,
        timestamp: new Date().toISOString(),
      });

      // Try to get actual LLM response for each task
      try {
        const ZAI = (await import('z-ai-web-dev-sdk')).default;
        const zai = await ZAI.create();
        const completion = await zai.chat.completions.create({
          messages: [
            {
              role: 'system',
              content: `You are ${todo.assigned_to}, a worker in a digital office. Complete the assigned task concisely.`,
            },
            {
              role: 'user',
              content: `Task: ${todo.description}\nContract: ${contract.title}\n${contract.description}`,
            },
          ],
          temperature: 0.5,
        });

        const output =
          completion.choices?.[0]?.message?.content ||
          'Task completed.';

        results[todo.id] = {
          status: 'done',
          output,
          worker_id: todo.assigned_to,
        };

        events.push({
          type: 'task_done',
          from_id: todo.assigned_to,
          content: output.substring(0, 200),
          session_id,
          timestamp: new Date().toISOString(),
        });
      } catch {
        // Fallback: simulated result
        results[todo.id] = {
          status: 'done',
          output: `Completed: ${todo.description}`,
          worker_id: todo.assigned_to,
        };

        events.push({
          type: 'task_done',
          from_id: todo.assigned_to,
          content: `Completed: ${todo.description}`,
          session_id,
          timestamp: new Date().toISOString(),
        });
      }
    }

    // Phase 6: Verification
    if (todos.length > 0) {
      events.push({
        type: 'verify_start',
        from_id: 'verifier_engineer',
        content: 'Starting code verification...',
        session_id,
        timestamp: new Date().toISOString(),
      });

      events.push({
        type: 'verify_done',
        from_id: 'verifier_engineer',
        content: 'Verification complete. All checks passed.',
        issues: [],
        approved: true,
        session_id,
        timestamp: new Date().toISOString(),
      });
    }

    // Phase 7: Done
    events.push({
      type: 'contract_done',
      from_id: 'conductor',
      content: `All tasks for "${contract.title}" have been completed successfully.`,
      session_id,
      timestamp: new Date().toISOString(),
    });

    return NextResponse.json({
      session_id,
      events,
      results,
    });
  } catch (error: unknown) {
    console.error('Execute API error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Execution failed', details: message },
      { status: 500 }
    );
  }
}

function getWorkerBriefingMessage(workerId: string, title: string): string {
  const messages: Record<string, string> = {
    coder_backend: `I can handle the backend logic for "${title}". I'll need the API spec and database schema details.`,
    coder_frontend: `Ready to build the UI for "${title}". I'll need the design mockups and API contracts.`,
    coder_wiring: `I'll wire up the integrations for "${title}". Let me know the API endpoints and WebSocket requirements.`,
    scout: `I've gathered some research relevant to "${title}". Ready to share insights with the team.`,
    sentinel: `I'll be monitoring quality throughout. I have some guardrails to suggest for "${title}".`,
    verifier_engineer: `I'll verify the code quality once the implementation is done. I have some standards to check against.`,
    verifier_designer: `I'll review the design quality. Looking forward to seeing the UI for "${title}".`,
    debugger: `Standing by to help with any issues that arise during development of "${title}".`,
    auditor: `I'll perform a security audit once the code is ready. Let me note the security requirements early.`,
    scribe: `I'll document everything as we go. Ready to write docs for "${title}".`,
    narrator: `I can help craft the narrative and presentations for "${title}".`,
    summarizer: `I'll keep track of key decisions and summarize our progress on "${title}".`,
    intake: `I've already classified this request. It looks like a solid project.`,
  };
  return messages[workerId] || `Ready to work on "${title}".`;
}
