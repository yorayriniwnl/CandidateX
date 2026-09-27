import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const sessionCookie = request.cookies.get('cx_session')?.value;

  if (!sessionCookie) {
    return NextResponse.json({ user: null });
  }

  try {
    const user = JSON.parse(sessionCookie);
    return NextResponse.json({ user });
  } catch {
    return NextResponse.json({ user: null });
  }
}
