import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const sessionCookie = request.cookies.get('cx_session')?.value;
  if (sessionCookie) {
    try {
      const user = JSON.parse(sessionCookie);
      return NextResponse.json({ user });
    } catch {}
  }

  const authCookie = request.cookies.get('cx_auth')?.value;
  if (authCookie) {
    return NextResponse.json({
      user: {
        email: decodeURIComponent(authCookie),
        role: 'evaluator',
        loginTime: Date.now(),
      },
    });
  }

  return NextResponse.json({ user: null });
}
