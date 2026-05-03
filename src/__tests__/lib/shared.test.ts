import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  WORKER_SKILLS,
  estimateCost,
  parseJsonResponse,
  generateId,
  wait,
} from '@/lib/kantorku/shared';
import { WORKERS } from '@/lib/kantorku/workers-data';

// ── WORKER_SKILLS ─────────────────────────────────────────────────

describe('WORKER_SKILLS', () => {
  it('should have entries for all 13 workers', () => {
    const workerIds = WORKERS.map((w) => w.id);
    expect(workerIds).toHaveLength(13);

    for (const id of workerIds) {
      expect(WORKER_SKILLS).toHaveProperty(id);
    }
  });

  it('should map each worker ID to its role', () => {
    for (const worker of WORKERS) {
      expect(WORKER_SKILLS[worker.id]).toBe(worker.role);
    }
  });

  it('should contain the expected set of worker IDs', () => {
    const expectedIds = [
      'intake',
      'scout',
      'sentinel',
      'coder_backend',
      'coder_frontend',
      'coder_wiring',
      'verifier_engineer',
      'verifier_designer',
      'debugger',
      'auditor',
      'scribe',
      'narrator',
      'summarizer',
    ];
    const actualIds = Object.keys(WORKER_SKILLS).sort();
    expect(actualIds).toEqual(expectedIds.sort());
  });

  it('should be a plain object (Record<string, string>)', () => {
    expect(typeof WORKER_SKILLS).toBe('object');
    expect(Array.isArray(WORKER_SKILLS)).toBe(false);
    for (const value of Object.values(WORKER_SKILLS)) {
      expect(typeof value).toBe('string');
    }
  });
});

// ── estimateCost ──────────────────────────────────────────────────

describe('estimateCost', () => {
  it('should calculate cost for claude-opus-4-6', () => {
    // input: 1000 tokens * $0.015 = $0.015, output: 1000 tokens * $0.075 = $0.075
    const cost = estimateCost('claude-opus-4-6', 1000, 1000);
    expect(cost).toBeCloseTo(0.09, 4);
  });

  it('should calculate cost for claude-sonnet-4-6', () => {
    const cost = estimateCost('claude-sonnet-4-6', 1000, 1000);
    // 0.003 + 0.015 = 0.018
    expect(cost).toBeCloseTo(0.018, 4);
  });

  it('should calculate cost for gemini-3.1-pro', () => {
    const cost = estimateCost('gemini-3.1-pro', 1000, 1000);
    // 0.00125 + 0.005 = 0.00625
    expect(cost).toBeCloseTo(0.00625, 5);
  });

  it('should calculate cost for gemini-2.5-pro', () => {
    const cost = estimateCost('gemini-2.5-pro', 1000, 1000);
    // 0.00125 + 0.005 = 0.00625
    expect(cost).toBeCloseTo(0.00625, 5);
  });

  it('should calculate cost for minimax-m2.7', () => {
    const cost = estimateCost('minimax-m2.7', 1000, 1000);
    // 0.0004 + 0.0012 = 0.0016
    expect(cost).toBeCloseTo(0.0016, 5);
  });

  it('should calculate cost for minimax-m2.5', () => {
    const cost = estimateCost('minimax-m2.5', 1000, 1000);
    // 0.0003 + 0.001 = 0.0013
    expect(cost).toBeCloseTo(0.0013, 5);
  });

  it('should calculate cost for deepseek-v3.2', () => {
    const cost = estimateCost('deepseek-v3.2', 1000, 1000);
    // 0.00027 + 0.0011 = 0.00137
    expect(cost).toBeCloseTo(0.00137, 5);
  });

  it('should calculate cost for deepseek-v4-flash', () => {
    const cost = estimateCost('deepseek-v4-flash', 1000, 1000);
    // 0.0001 + 0.0004 = 0.0005
    expect(cost).toBeCloseTo(0.0005, 5);
  });

  it('should return 0 for ollama-llama3 (local model)', () => {
    const cost = estimateCost('ollama-llama3', 5000, 5000);
    expect(cost).toBe(0);
  });

  it('should calculate cost for conductor model', () => {
    const cost = estimateCost('conductor', 1000, 1000);
    // Same as claude-opus-4-6: 0.015 + 0.075 = 0.09
    expect(cost).toBeCloseTo(0.09, 4);
  });

  it('should use default rates for unknown model', () => {
    const cost = estimateCost('unknown-model', 1000, 1000);
    // Default: input 0.001, output 0.003 → 0.001 + 0.003 = 0.004
    expect(cost).toBeCloseTo(0.004, 4);
  });

  it('should return 0 when both token counts are 0', () => {
    const cost = estimateCost('claude-opus-4-6', 0, 0);
    expect(cost).toBe(0);
  });

  it('should calculate correctly for zero input tokens', () => {
    const cost = estimateCost('claude-sonnet-4-6', 0, 1000);
    expect(cost).toBeCloseTo(0.015, 4);
  });

  it('should calculate correctly for zero output tokens', () => {
    const cost = estimateCost('claude-sonnet-4-6', 1000, 0);
    expect(cost).toBeCloseTo(0.003, 4);
  });

  it('should handle fractional token counts', () => {
    const cost = estimateCost('claude-sonnet-4-6', 500, 200);
    // (500/1000)*0.003 + (200/1000)*0.015 = 0.0015 + 0.003 = 0.0045
    expect(cost).toBeCloseTo(0.0045, 5);
  });

  it('should handle large token counts', () => {
    const cost = estimateCost('claude-opus-4-6', 1_000_000, 100_000);
    // (1000000/1000)*0.015 + (100000/1000)*0.075 = 15 + 7.5 = 22.5
    expect(cost).toBeCloseTo(22.5, 2);
  });
});

// ── parseJsonResponse ─────────────────────────────────────────────

describe('parseJsonResponse', () => {
  describe('direct JSON parsing', () => {
    it('should parse a valid JSON object string', () => {
      const result = parseJsonResponse('{"name": "test", "value": 42}');
      expect(result).toEqual({ name: 'test', value: 42 });
    });

    it('should parse a valid JSON array string', () => {
      const result = parseJsonResponse('[1, 2, 3]');
      expect(result).toEqual([1, 2, 3]);
    });

    it('should parse nested JSON', () => {
      const result = parseJsonResponse('{"a": {"b": [1, 2]}}');
      expect(result).toEqual({ a: { b: [1, 2] } });
    });
  });

  describe('markdown code block JSON', () => {
    it('should extract JSON from a ```json code block', () => {
      const text = 'Here is the result:\n```json\n{"key": "value"}\n```';
      const result = parseJsonResponse(text);
      expect(result).toEqual({ key: 'value' });
    });

    it('should extract JSON from a ``` code block without language', () => {
      const text = '```\n{"key": "value"}\n```';
      const result = parseJsonResponse(text);
      expect(result).toEqual({ key: 'value' });
    });

    it('should handle code block with extra whitespace', () => {
      const text = '```json\n  {"key": "value"}  \n```';
      const result = parseJsonResponse(text);
      expect(result).toEqual({ key: 'value' });
    });
  });

  describe('embedded JSON (first { to last })', () => {
    it('should extract JSON embedded in text with braces', () => {
      const text = 'The result is {"name": "embedded"} and that is it.';
      const result = parseJsonResponse(text);
      expect(result).toEqual({ name: 'embedded' });
    });

    it('should extract JSON from surrounding prose', () => {
      const text = 'Here is the data: {"items": [1,2,3], "count": 3} end.';
      const result = parseJsonResponse(text);
      expect(result).toEqual({ items: [1, 2, 3], count: 3 });
    });
  });

  describe('array extraction (first [ to last ])', () => {
    it('should extract an array embedded in text', () => {
      const text = 'The list is [1, 2, 3] done.';
      const result = parseJsonResponse(text);
      expect(result).toEqual([1, 2, 3]);
    });

    it('should extract an array of objects', () => {
      const text = 'Results: [{"id": 1}, {"id": 2}] finish.';
      const result = parseJsonResponse(text);
      expect(result).toEqual([{ id: 1 }, { id: 2 }]);
    });
  });

  describe('null / error cases', () => {
    it('should return null for completely invalid text', () => {
      const result = parseJsonResponse('this is not JSON at all');
      expect(result).toBeNull();
    });

    it('should return null for empty string', () => {
      const result = parseJsonResponse('');
      expect(result).toBeNull();
    });

    it('should return null for malformed JSON in code block', () => {
      const text = '```json\n{invalid json}\n```';
      const result = parseJsonResponse(text);
      expect(result).toBeNull();
    });

    it('should return null for unbalanced braces', () => {
      const text = '{"key": "value"';
      const result = parseJsonResponse(text);
      expect(result).toBeNull();
    });
  });

  describe('type preservation', () => {
    it('should preserve string values', () => {
      const result = parseJsonResponse<Record<string, string>>('{"name": "Alice"}');
      expect(result).toEqual({ name: 'Alice' });
    });

    it('should preserve numeric values', () => {
      const result = parseJsonResponse<Record<string, number>>('{"count": 42, "pi": 3.14}');
      expect(result).toEqual({ count: 42, pi: 3.14 });
    });

    it('should preserve boolean values', () => {
      const result = parseJsonResponse<Record<string, boolean>>('{"active": true, "deleted": false}');
      expect(result).toEqual({ active: true, deleted: false });
    });

    it('should preserve null values within JSON', () => {
      const result = parseJsonResponse('{"value": null}');
      expect(result).toEqual({ value: null });
    });
  });
});

// ── generateId ────────────────────────────────────────────────────

describe('generateId', () => {
  it('should return a string with the given prefix', () => {
    const id = generateId('msg');
    expect(id).toMatch(/^msg_/);
  });

  it('should include the prefix exactly as given', () => {
    const id = generateId('worker');
    expect(id.startsWith('worker_')).toBe(true);
  });

  it('should have the format: prefix_timestamp_random', () => {
    const id = generateId('test');
    const parts = id.split('_');
    expect(parts.length).toBeGreaterThanOrEqual(3);
    expect(parts[0]).toBe('test');
    // The timestamp part should be a number
    expect(Number.isNaN(Number(parts[1]))).toBe(false);
  });

  it('should generate unique IDs on successive calls', () => {
    const ids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      ids.add(generateId('uniq'));
    }
    expect(ids.size).toBe(100);
  });

  it('should work with empty prefix', () => {
    const id = generateId('');
    expect(id).toMatch(/^_\d+_/);
  });

  it('should work with various prefixes', () => {
    const prefixes = ['msg', 'session', 'snap', 'trace', 'todo'];
    for (const prefix of prefixes) {
      const id = generateId(prefix);
      expect(id.startsWith(`${prefix}_`)).toBe(true);
    }
  });
});

// ── wait ──────────────────────────────────────────────────────────

describe('wait', () => {
  it('should resolve after the specified timeout', async () => {
    const start = Date.now();
    await wait(50);
    const elapsed = Date.now() - start;
    // Allow some tolerance for timer imprecision
    expect(elapsed).toBeGreaterThanOrEqual(40);
  });

  it('should resolve with undefined', async () => {
    const result = await wait(10);
    expect(result).toBeUndefined();
  });

  it('should resolve immediately for 0ms', async () => {
    const start = Date.now();
    await wait(0);
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(50);
  });

  it('should return a Promise', () => {
    const result = wait(10);
    expect(result).toBeInstanceOf(Promise);
    // Consume the promise to avoid unhandled rejection
    result.catch(() => {});
  });
});
