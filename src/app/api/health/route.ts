import { NextResponse } from 'next/server';
import type { HealthStatus } from '@/lib/kantorku/types';
import { WORKERS } from '@/lib/kantorku/workers-data';
import { logger } from '@/lib/kantorku/logger';
import { InternalError, isAppError } from '@/lib/kantorku/errors';

// ── System start time for uptime tracking ─────────────────────────
const SYSTEM_START_TIME = Date.now();

// ── Route Handler ─────────────────────────────────────────────────
export async function GET() {
  const checkStart = Date.now();

  try {
    // Check LLM API accessibility
    let providerHealthy = false;
    let providerLatency = 0;

    try {
      const ZAI = (await import('z-ai-web-dev-sdk')).default;
      const zai = await ZAI.create();

      const probeStart = Date.now();

      // Race the probe with a 10s timeout
      const probePromise = zai.chat.completions.create({
        messages: [
          { role: 'user', content: 'ping' },
        ],
        temperature: 0,
      });
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Health probe timeout')), 10000)
      );

      const completion = await Promise.race([probePromise, timeoutPromise]);
      providerLatency = Date.now() - probeStart;

      providerHealthy =
        !!completion.choices?.[0]?.message?.content ||
        !!completion.usage;
    } catch (error) {
      providerHealthy = false;
      providerLatency = Date.now() - checkStart;
      logger.warn('health', 'Provider check failed', error instanceof Error ? error.message : 'Unknown');
    }

    // Build provider health status
    const providers: HealthStatus['providers'] = {
      z_ai_gateway: {
        status: providerHealthy ? 'healthy' : 'unhealthy',
        latency_ms: providerLatency,
        error_rate: providerHealthy ? 0 : 1,
      },
    };

    // Build worker status summary
    const workerStatuses: HealthStatus['workers'] = {};
    for (const worker of WORKERS) {
      workerStatuses[worker.id] = {
        status: worker.status || 'idle',
        current_task: worker.current_task,
        latency_ms: worker.avg_latency_ms,
      };
    }

    // System metrics
    const uptimeMs = Date.now() - SYSTEM_START_TIME;
    const memoryUsage = process.memoryUsage();

    const healthStatus: HealthStatus & {
      system: {
        uptime_ms: number;
        memory: {
          rss_mb: number;
          heap_used_mb: number;
          heap_total_mb: number;
          external_mb: number;
        };
        node_version: string;
        platform: string;
      };
      version: string;
      workers_summary: {
        total: number;
        idle: number;
        busy: number;
        error: number;
        offline: number;
      };
    } = {
      is_healthy: providerHealthy,
      message: providerHealthy
        ? 'All systems operational'
        : 'LLM provider is unreachable — running in degraded mode',
      providers,
      workers: workerStatuses,
      uptime_ms: uptimeMs,
      last_check: new Date().toISOString(),
      system: {
        uptime_ms: uptimeMs,
        memory: {
          rss_mb: Math.round((memoryUsage.rss / 1024 / 1024) * 100) / 100,
          heap_used_mb: Math.round((memoryUsage.heapUsed / 1024 / 1024) * 100) / 100,
          heap_total_mb: Math.round((memoryUsage.heapTotal / 1024 / 1024) * 100) / 100,
          external_mb: Math.round((memoryUsage.external / 1024 / 1024) * 100) / 100,
        },
        node_version: process.version,
        platform: process.platform,
      },
      version: '0.4.1',
      workers_summary: {
        total: WORKERS.length,
        idle: WORKERS.filter((w) => w.status === 'idle' || !w.status).length,
        busy: WORKERS.filter((w) => w.status === 'busy').length,
        error: WORKERS.filter((w) => w.status === 'error').length,
        offline: WORKERS.filter((w) => w.status === 'offline').length,
      },
    };

    return NextResponse.json(healthStatus, {
      status: providerHealthy ? 200 : 503,
    });
  } catch (error: unknown) {
    // Wrap with InternalError for consistent logging and classification
    const appError = isAppError(error)
      ? error
      : new InternalError(error instanceof Error ? error.message : 'Unknown error');
    logger.error('health', appError.message, appError);

    // Keep the special health check response format
    return NextResponse.json(
      {
        is_healthy: false,
        message: `Health check failed: ${appError.message}`,
        uptime_ms: Date.now() - SYSTEM_START_TIME,
        last_check: new Date().toISOString(),
      } satisfies HealthStatus,
      { status: 503 }
    );
  }
}
