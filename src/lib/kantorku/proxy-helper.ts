/**
 * API Route Proxy Helper — Shared utilities for proxying to the KantorKu Python backend
 *
 * Each API route checks if a backend URL is configured and proxies the request.
 * If no backend is configured, returns 503 with standalone mode message.
 */

import { NextRequest, NextResponse } from 'next/server';

/**
 * Get the backend URL from environment or request headers.
 */
function getBackendUrl(request?: NextRequest): string | null {
  // Check environment variable first
  const envUrl = process.env.KANTORKU_BACKEND_URL;
  if (envUrl) return envUrl;

  // Check custom header (set by frontend from store)
  if (request) {
    const headerUrl = request.headers.get('x-kantorku-backend-url');
    if (headerUrl) return headerUrl;

    // Check query parameter
    const queryUrl = request.nextUrl.searchParams.get('backend_url');
    if (queryUrl) return queryUrl;
  }

  return null;
}

/**
 * Proxy a GET request to the Python backend.
 */
export async function proxyGet(
  request: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const backendUrl = getBackendUrl(request);

  if (!backendUrl) {
    return NextResponse.json(
      {
        error: 'Backend not configured - running in standalone mode',
        standalone: true,
      },
      { status: 503 }
    );
  }

  const targetUrl = `${backendUrl.replace(/\/+$/, '')}${backendPath}`;

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000), // 10s timeout
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json(
      {
        error: 'Backend request failed',
        details: message,
        backend_url: backendUrl,
        path: backendPath,
      },
      { status: 502 }
    );
  }
}

/**
 * Proxy a DELETE request to the Python backend.
 */
export async function proxyDelete(
  request: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const backendUrl = getBackendUrl(request);

  if (!backendUrl) {
    return NextResponse.json(
      {
        error: 'Backend not configured - running in standalone mode',
        standalone: true,
      },
      { status: 503 }
    );
  }

  const targetUrl = `${backendUrl.replace(/\/+$/, '')}${backendPath}`;

  try {
    const response = await fetch(targetUrl, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json(
      {
        error: 'Backend request failed',
        details: message,
        backend_url: backendUrl,
        path: backendPath,
      },
      { status: 502 }
    );
  }
}
