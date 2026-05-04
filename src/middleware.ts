import { NextRequest, NextResponse } from 'next/server';

// ─── Rate Limiting Types & Constants ────────────────────────────────────────

interface RateLimitEntry {
  count: number;
  windowStart: number;
}

const WINDOW_MS = 60_000; // 60 seconds
const MAX_ENTRIES = 10_000;

const RATE_LIMITS = {
  /** LLM-calling routes — most strict */
  strict: { max: 5, paths: ['/api/chat', '/api/execute', '/api/intake'] },
  /** General API routes */
  api: { max: 20 },
  /** Everything else (pages, etc.) */
  general: { max: 100 },
} as const;

type RateLimitTier = keyof typeof RATE_LIMITS;

// ─── In-Memory Rate Limit Store ─────────────────────────────────────────────

const rateLimitMap = new Map<string, RateLimitEntry>();
let lastCleanup = Date.now();

function getRateLimitTier(pathname: string): RateLimitTier {
  for (const path of RATE_LIMITS.strict.paths) {
    if (pathname.startsWith(path)) {
      return 'strict';
    }
  }
  if (pathname.startsWith('/api/')) {
    return 'api';
  }
  return 'general';
}

function getMaxForTier(tier: RateLimitTier): number {
  return RATE_LIMITS[tier].max;
}

function cleanupExpiredEntries(): void {
  const now = Date.now();
  for (const [key, entry] of rateLimitMap) {
    if (now - entry.windowStart >= WINDOW_MS) {
      rateLimitMap.delete(key);
    }
  }
  lastCleanup = now;
}

function checkRateLimit(ip: string, tier: RateLimitTier): {
  allowed: boolean;
  remaining: number;
  retryAfter: number;
} {
  const now = Date.now();

  // Periodic cleanup: every 60s or when map exceeds max entries
  if (now - lastCleanup >= WINDOW_MS || rateLimitMap.size > MAX_ENTRIES) {
    cleanupExpiredEntries();
  }

  // If still over the limit after cleanup, evict the oldest entries
  if (rateLimitMap.size > MAX_ENTRIES) {
    const entries = [...rateLimitMap.entries()].sort(
      (a, b) => a[1].windowStart - b[1].windowStart
    );
    const excess = rateLimitMap.size - MAX_ENTRIES;
    for (let i = 0; i < excess; i++) {
      rateLimitMap.delete(entries[i][0]);
    }
  }

  const key = `${ip}:${tier}`;
  const entry = rateLimitMap.get(key);
  const max = getMaxForTier(tier);

  if (!entry || now - entry.windowStart >= WINDOW_MS) {
    // Start a new window
    rateLimitMap.set(key, { count: 1, windowStart: now });
    return { allowed: true, remaining: max - 1, retryAfter: 0 };
  }

  if (entry.count >= max) {
    const retryAfter = Math.ceil((entry.windowStart + WINDOW_MS - now) / 1000);
    return { allowed: false, remaining: 0, retryAfter: Math.max(retryAfter, 1) };
  }

  entry.count += 1;
  return { allowed: true, remaining: max - entry.count, retryAfter: 0 };
}

// ─── IP Extraction ──────────────────────────────────────────────────────────

function getClientIP(request: NextRequest): string {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    // x-forwarded-for may contain a comma-separated list; first entry is client
    return forwarded.split(',')[0].trim();
  }
  const realIP = request.headers.get('x-real-ip');
  if (realIP) {
    return realIP.trim();
  }
  return 'unknown';
}

// ─── Security Headers ───────────────────────────────────────────────────────

function applySecurityHeaders(response: NextResponse): void {
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=()'
  );
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' ws: wss: https:;"
  );
  response.headers.set(
    'Strict-Transport-Security',
    'max-age=63072000; includeSubDomains; preload'
  );
}

// ─── CORS Headers (API routes only) ─────────────────────────────────────────

function applyCorsHeaders(response: NextResponse): void {
  const allowedOrigin = process.env.CORS_ORIGIN ?? '*';
  response.headers.set('Access-Control-Allow-Origin', allowedOrigin);
  response.headers.set(
    'Access-Control-Allow-Methods',
    'GET, POST, OPTIONS'
  );
  response.headers.set(
    'Access-Control-Allow-Headers',
    'Content-Type, Authorization'
  );
}

function createCorsPreflightResponse(): NextResponse {
  const response = new NextResponse(null, { status: 204 });
  applyCorsHeaders(response);
  return response;
}

// ─── Health Check Bypass ────────────────────────────────────────────────────

function isHealthCheckRoute(pathname: string): boolean {
  if (pathname === '/api/health') return true;
  if (pathname.startsWith('/api/kantorku/health/')) return true;
  return false;
}

// ─── Main Middleware ────────────────────────────────────────────────────────

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // ── Skip static assets & _next internals ──
  // These are excluded by the matcher too, but double-check for safety
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/static') ||
    /\.(jpg|jpeg|png|gif|svg|ico|webp|woff|woff2|ttf|eot|css|js|map)$/i.test(pathname)
  ) {
    return NextResponse.next();
  }

  const isApiRoute = pathname.startsWith('/api/');

  // ── Handle CORS preflight for API routes ──
  if (isApiRoute && request.method === 'OPTIONS') {
    const preflight = createCorsPreflightResponse();
    applySecurityHeaders(preflight);
    return preflight;
  }

  // ── Rate limiting (skip for health check routes) ──
  if (!isHealthCheckRoute(pathname)) {
    const ip = getClientIP(request);
    const tier = getRateLimitTier(pathname);
    const result = checkRateLimit(ip, tier);

    if (!result.allowed) {
      const response = NextResponse.json(
        {
          error: 'Too Many Requests',
          message: `Rate limit exceeded. Try again in ${result.retryAfter} seconds.`,
        },
        { status: 429 }
      );
      response.headers.set('Retry-After', String(result.retryAfter));
      applySecurityHeaders(response);
      if (isApiRoute) {
        applyCorsHeaders(response);
      }
      return response;
    }
  }

  // ── Continue with the request ──
  const response = NextResponse.next();

  // Apply security headers to all responses
  applySecurityHeaders(response);

  // Apply CORS headers to API routes
  if (isApiRoute) {
    applyCorsHeaders(response);
  }

  return response;
}

// ─── Matcher Configuration ──────────────────────────────────────────────────

export const config = {
  matcher: [
    /*
     * Match all routes except:
     * - _next (internal Next.js files)
     * - static assets (images, fonts, etc.)
     * - favicon
     *
     * We use a negative-lookahead pattern to exclude these while
     * matching API routes and page routes.
     */
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:jpg|jpeg|png|gif|svg|ico|webp|woff|woff2|ttf|eot|css|map)$).*)',
  ],
};
