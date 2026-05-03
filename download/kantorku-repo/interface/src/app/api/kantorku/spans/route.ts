import { NextRequest } from 'next/server';
import { proxyGet } from '@/lib/kantorku/proxy-helper';

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get('limit') || '100';
  return proxyGet(request, `/spans?limit=${limit}`);
}
