import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KantorkuApiClient, getApiClient } from '@/lib/kantorku/api-client';

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Helper to create a successful JSON response
function jsonResponse<T>(data: T, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

// ── Constructor ──────────────────────────────────────────────────

describe('KantorkuApiClient constructor', () => {
  it('should create an instance with a base URL', () => {
    const client = new KantorkuApiClient('http://localhost:8000');
    expect(client).toBeInstanceOf(KantorkuApiClient);
  });

  it('should remove trailing slashes from base URL', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ name: 'kantorku', version: '0.1', status: 'running', workers: 13 }));

    const client = new KantorkuApiClient('http://localhost:8000///');
    await client.getRoot();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0] as string;
    // Should not have multiple slashes before the path
    expect(calledUrl).toBe('http://localhost:8000/');
    expect(calledUrl).not.toContain('///');
  });

  it('should preserve base URL without trailing slash', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ name: 'kantorku', version: '0.1', status: 'running', workers: 13 }));

    const client = new KantorkuApiClient('http://localhost:8000');
    await client.getRoot();

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toBe('http://localhost:8000/');
  });

  it('should handle base URL with port', () => {
    const client = new KantorkuApiClient('http://localhost:8080');
    expect(client).toBeInstanceOf(KantorkuApiClient);
  });

  it('should handle base URL with subpath', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ name: 'kantorku', version: '0.1', status: 'running', workers: 13 }));

    const client = new KantorkuApiClient('http://localhost:8000/api/v1');
    await client.getRoot();

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toBe('http://localhost:8000/api/v1/');
  });
});

// ── Method Generation (all REST methods exist) ──────────────────

describe('API client methods', () => {
  let client: KantorkuApiClient;

  beforeEach(() => {
    client = new KantorkuApiClient('http://localhost:8000');
  });

  it('should have getHealthLive method', () => {
    expect(typeof client.getHealthLive).toBe('function');
  });

  it('should have getHealthReady method', () => {
    expect(typeof client.getHealthReady).toBe('function');
  });

  it('should have getHealthDashboard method', () => {
    expect(typeof client.getHealthDashboard).toBe('function');
  });

  it('should have getStatus method', () => {
    expect(typeof client.getStatus).toBe('function');
  });

  it('should have getCost method', () => {
    expect(typeof client.getCost).toBe('function');
  });

  it('should have getMetrics method', () => {
    expect(typeof client.getMetrics).toBe('function');
  });

  it('should have getCircuitBreakers method', () => {
    expect(typeof client.getCircuitBreakers).toBe('function');
  });

  it('should have getSpans method', () => {
    expect(typeof client.getSpans).toBe('function');
  });

  it('should have getSessions method', () => {
    expect(typeof client.getSessions).toBe('function');
  });

  it('should have getSession method', () => {
    expect(typeof client.getSession).toBe('function');
  });

  it('should have deleteSession method', () => {
    expect(typeof client.deleteSession).toBe('function');
  });

  it('should have getRoot method', () => {
    expect(typeof client.getRoot).toBe('function');
  });
});

// ── URL Construction ─────────────────────────────────────────────

describe('URL construction with paths', () => {
  let client: KantorkuApiClient;

  beforeEach(() => {
    client = new KantorkuApiClient('http://localhost:8000');
  });

  it('should construct correct URL for getHealthLive', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ status: 'healthy', checks: {}, uptime_ms: 1000, version: '0.1' }));
    await client.getHealthLive();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/health/live');
  });

  it('should construct correct URL for getHealthReady', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ status: 'healthy', checks: {}, uptime_ms: 1000, version: '0.1' }));
    await client.getHealthReady();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/health/ready');
  });

  it('should construct correct URL for getHealthDashboard', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      overall: 'healthy',
      providers: {},
      workers: {},
      system: { uptime_ms: 1000, total_requests: 0, active_sessions: 0 },
      alerts: [],
    }));
    await client.getHealthDashboard();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/health/dashboard');
  });

  it('should construct correct URL for getStatus', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      status: 'running',
      active_sessions: 0,
      total_workers: 13,
      busy_workers: 0,
      uptime_ms: 5000,
      version: '0.1',
      provider_status: {},
      memory_rings: { ring1_entries: 0, ring2_entries: 0, ring3_entries: 0 },
      task_queue: { pending: 0, in_progress: 0, completed: 0, failed: 0 },
    }));
    await client.getStatus();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/status');
  });

  it('should construct correct URL for getCost', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      total_cost: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      entries: [],
      by_model: {},
      by_worker: {},
    }));
    await client.getCost();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/cost');
  });

  it('should construct correct URL for getMetrics', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      total_calls: 0,
      total_tokens: 0,
      total_cost: 0,
      avg_latency_ms: 0,
      success_rate: 1,
      p50_latency_ms: 0,
      p95_latency_ms: 0,
      p99_latency_ms: 0,
      by_model: {},
    }));
    await client.getMetrics();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/metrics');
  });

  it('should construct correct URL for getCircuitBreakers', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({}));
    await client.getCircuitBreakers();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/circuit-breaker');
  });

  it('should construct correct URL for getSpans with default limit', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ spans: [] }));
    await client.getSpans();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/spans?limit=100');
  });

  it('should construct correct URL for getSpans with custom limit', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ spans: [] }));
    await client.getSpans(50);
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/spans?limit=50');
  });

  it('should construct correct URL for getSessions', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ sessions: [] }));
    await client.getSessions();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/sessions');
  });

  it('should construct correct URL for getSession with id', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      session_id: 'abc',
      state: 'idle',
      contract: null,
      messages: [],
      worker_messages: [],
      intake: null,
      briefing: null,
      debrief: null,
      cost: null,
      traces: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
    await client.getSession('abc123');
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/sessions/abc123');
  });

  it('should construct correct URL for deleteSession with id', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ status: 'deleted', session_id: 'abc123' }));
    await client.deleteSession('abc123');
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/sessions/abc123');
  });

  it('should construct correct URL for getRoot', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ name: 'kantorku', version: '0.1', status: 'running', workers: 13 }));
    await client.getRoot();
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/');
  });
});

// ── Request Headers ──────────────────────────────────────────────

describe('Request headers', () => {
  let client: KantorkuApiClient;

  beforeEach(() => {
    client = new KantorkuApiClient('http://localhost:8000');
  });

  it('should send Content-Type: application/json header', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ name: 'kantorku', version: '0.1', status: 'running', workers: 13 }));
    await client.getRoot();

    const options = mockFetch.mock.calls[0][1] as RequestInit;
    expect(options?.headers).toHaveProperty('Content-Type', 'application/json');
  });

  it('should use DELETE method for deleteSession', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ status: 'deleted', session_id: 'test' }));
    await client.deleteSession('test');

    const options = mockFetch.mock.calls[0][1] as RequestInit;
    expect(options?.method).toBe('DELETE');
  });
});

// ── Error Handling ───────────────────────────────────────────────

describe('Error handling', () => {
  let client: KantorkuApiClient;

  beforeEach(() => {
    client = new KantorkuApiClient('http://localhost:8000');
  });

  it('should throw an error when response is not ok', async () => {
    mockFetch.mockResolvedValueOnce(new Response('Not Found', { status: 404, statusText: 'Not Found' }));

    await expect(client.getRoot()).rejects.toThrow('API error: 404 Not Found');
  });

  it('should throw an error for 500 status', async () => {
    mockFetch.mockResolvedValueOnce(new Response('Internal Server Error', { status: 500, statusText: 'Internal Server Error' }));

    await expect(client.getRoot()).rejects.toThrow('API error: 500 Internal Server Error');
  });

  it('should throw an error for 429 status', async () => {
    mockFetch.mockResolvedValueOnce(new Response('Too Many Requests', { status: 429, statusText: 'Too Many Requests' }));

    await expect(client.getRoot()).rejects.toThrow('API error: 429 Too Many Requests');
  });
});

// ── getApiClient factory ─────────────────────────────────────────

describe('getApiClient', () => {
  it('should return a KantorkuApiClient when backendUrl is provided', () => {
    const client = getApiClient('http://localhost:8000');
    expect(client).toBeInstanceOf(KantorkuApiClient);
  });

  it('should return null when backendUrl is null', () => {
    const client = getApiClient(null);
    expect(client).toBeNull();
  });

  it('should return null when backendUrl is empty string', () => {
    const client = getApiClient('');
    expect(client).toBeNull();
  });

  it('should return null when backendUrl is undefined', () => {
    const client = getApiClient(undefined as unknown as string);
    expect(client).toBeNull();
  });
});
