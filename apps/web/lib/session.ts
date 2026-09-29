import { cookies } from 'next/headers';
import { signSession, verifySession, type SessionUser } from './session-core';

export { signSession, verifySession, type SessionUser };

export async function getSessionFromRequest(): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get('cx_session')?.value;
  if (!sessionCookie) return null;
  return verifySession(sessionCookie);
}
