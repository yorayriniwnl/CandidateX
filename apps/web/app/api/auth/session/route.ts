import { NextRequest, NextResponse } from 'next/server';
import { verifySession } from '../../../../lib/session';

export async function GET(request: NextRequest) {
  const sessionCookie = request.cookies.get('cx_session')?.value;
  if (sessionCookie) {
    const user = verifySession(sessionCookie);
    if (user) {
      return NextResponse.json({ user });
    }
  }

  return NextResponse.json({ user: null });
}
