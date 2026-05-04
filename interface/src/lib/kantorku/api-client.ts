/**
 * KantorKu API Client — Typed client for the Python backend REST API
 *
 * All methods return typed responses matching the Python framework models.
 * Use this client to interact with the kantorku backend when in "backend mode".
 */

import type {
  AggregatedHealth,
  HealthDashboard,
  OfficeStatus,
  CostReport,
  MetricsSummary,
  CircuitBreakerStatus,
  Span,
  Session,
  SessionSnapshot,
} from './types';

export class KantorkuApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    // Remove trailing slash
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  private async fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  // ── Health Endpoints ───────────────────────────────────────────────

  async getHealthLive(): Promise<AggregatedHealth> {
    return this.fetchJson<AggregatedHealth>('/health/live');
  }

  async getHealthReady(): Promise<AggregatedHealth> {
    return this.fetchJson<AggregatedHealth>('/health/ready');
  }

  async getHealthDashboard(): Promise<HealthDashboard> {
    return this.fetchJson<HealthDashboard>('/health/dashboard');
  }

  // ── Status ─────────────────────────────────────────────────────────

  async getStatus(): Promise<OfficeStatus> {
    return this.fetchJson<OfficeStatus>('/status');
  }

  // ── Cost ───────────────────────────────────────────────────────────

  async getCost(): Promise<CostReport> {
    return this.fetchJson<CostReport>('/cost');
  }

  // ── Metrics ────────────────────────────────────────────────────────

  async getMetrics(): Promise<MetricsSummary> {
    return this.fetchJson<MetricsSummary>('/metrics');
  }

  // ── Circuit Breaker ────────────────────────────────────────────────

  async getCircuitBreakers(): Promise<Record<string, CircuitBreakerStatus>> {
    return this.fetchJson<Record<string, CircuitBreakerStatus>>('/circuit-breaker');
  }

  // ── Spans ──────────────────────────────────────────────────────────

  async getSpans(limit: number = 100): Promise<{ spans: Span[] }> {
    return this.fetchJson<{ spans: Span[] }>(`/spans?limit=${limit}`);
  }

  // ── Sessions ───────────────────────────────────────────────────────

  async getSessions(): Promise<{ sessions: Session[] }> {
    return this.fetchJson<{ sessions: Session[] }>('/sessions');
  }

  async getSession(id: string): Promise<SessionSnapshot> {
    return this.fetchJson<SessionSnapshot>(`/sessions/${id}`);
  }

  async deleteSession(id: string): Promise<{ status: string; session_id: string }> {
    return this.fetchJson<{ status: string; session_id: string }>(`/sessions/${id}`, {
      method: 'DELETE',
    });
  }

  // ── Root ───────────────────────────────────────────────────────────

  async getRoot(): Promise<{
    name: string;
    version: string;
    status: string;
    workers: number;
  }> {
    return this.fetchJson<{
      name: string;
      version: string;
      status: string;
      workers: number;
    }>('/');
  }
}

/**
 * Get the API client for the configured backend URL.
 * Returns null if no backend is configured.
 */
export function getApiClient(backendUrl: string | null): KantorkuApiClient | null {
  if (!backendUrl) return null;
  return new KantorkuApiClient(backendUrl);
}
