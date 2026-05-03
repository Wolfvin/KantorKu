import { NextRequest } from 'next/server';
import { proxyGet, proxyDelete } from '@/lib/kantorku/proxy-helper';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;
  return proxyGet(request, `/sessions/${sessionId}`);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;
  return proxyDelete(request, `/sessions/${sessionId}`);
}
