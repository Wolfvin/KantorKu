/**
 * KantorKu Shared Utilities
 *
 * Common functions extracted from API routes to avoid duplication.
 */

import { WORKERS } from './workers-data';

// ── Worker Skills Map ──────────────────────────────────────────
/** Maps worker IDs to their skill descriptions for LLM prompts */
export const WORKER_SKILLS: Record<string, string> = Object.fromEntries(
  WORKERS.map((w) => [w.id, w.role])
);

// ── Cost Estimation ────────────────────────────────────────────
/** Estimate cost in USD based on model, input/output tokens */
export function estimateCost(
  model: string,
  inputTokens: number,
  outputTokens: number
): number {
  const rates: Record<string, { input: number; output: number }> = {
    'claude-opus-4-6': { input: 0.015, output: 0.075 },
    'claude-sonnet-4-6': { input: 0.003, output: 0.015 },
    'gemini-3.1-pro': { input: 0.00125, output: 0.005 },
    'gemini-2.5-pro': { input: 0.00125, output: 0.005 },
    'minimax-m2.7': { input: 0.0004, output: 0.0012 },
    'minimax-m2.5': { input: 0.0003, output: 0.001 },
    'deepseek-v3.2': { input: 0.00027, output: 0.0011 },
    'deepseek-v4-flash': { input: 0.0001, output: 0.0004 },
    'ollama-llama3': { input: 0, output: 0 },
    'conductor': { input: 0.015, output: 0.075 },
  };

  const rate = rates[model] || { input: 0.001, output: 0.003 };
  return (inputTokens / 1000) * rate.input + (outputTokens / 1000) * rate.output;
}

// ── JSON Response Parser ───────────────────────────────────────
/** Try to extract a JSON object from an LLM response string */
export function parseJsonResponse<T>(text: string): T | null {
  // Try direct parse first
  try {
    return JSON.parse(text) as T;
  } catch {
    // Continue to extraction
  }

  // Try extracting JSON from markdown code block
  const jsonBlockMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (jsonBlockMatch) {
    try {
      return JSON.parse(jsonBlockMatch[1]) as T;
    } catch {
      // Continue to next method
    }
  }

  // Try finding first { to last }
  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    try {
      return JSON.parse(text.slice(firstBrace, lastBrace + 1)) as T;
    } catch {
      // Give up
    }
  }

  // Try finding first [ to last ]
  const firstBracket = text.indexOf('[');
  const lastBracket = text.lastIndexOf(']');
  if (firstBracket !== -1 && lastBracket > firstBracket) {
    try {
      return JSON.parse(text.slice(firstBracket, lastBracket + 1)) as T;
    } catch {
      // Give up
    }
  }

  return null;
}

// ── ID Generator ───────────────────────────────────────────────
/** Generate a unique ID with a prefix */
export function generateId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// ── Wait Utility ───────────────────────────────────────────────
/** Async sleep for simulating delays */
export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
