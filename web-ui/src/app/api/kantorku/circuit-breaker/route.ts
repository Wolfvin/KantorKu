import { NextRequest } from 'next/server';
import { proxyGet } from '@/lib/kantorku/proxy-helper';

export async function GET(request: NextRequest) {
  return proxyGet(request, '/circuit-breaker');
}
