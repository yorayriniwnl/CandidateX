import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const host = request.headers.get('host') || 'localhost:3000';
  const protocol =
    request.headers.get('x-forwarded-proto') ||
    (host.startsWith('localhost') || host.startsWith('127.0.0.1') ? 'http' : 'https');
  const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_APP_URL || `${protocol}://${host}`;

  const response = NextResponse.json({ success: true });
  response.cookies.delete('cx_session');
  response.cookies.delete('cx_auth');
  response.cookies.delete('cx_oauth_state');

  return response;
}
