import crypto from 'crypto';

const DEV_SESSION_SECRET = 'dev-insecure-fallback-change-me';

function getSessionSecret(): string {
  const configured = process.env.SESSION_SECRET;
  if (configured) return configured;
  if (process.env.NODE_ENV === 'production') {
    throw new Error('SESSION_SECRET is required in production');
  }
  return DEV_SESSION_SECRET;
}

export interface SessionUser {
  email: string;
  name?: string;
  avatar?: string;
  provider: string;
  role?: string;
  loginTime: number;
  exp?: number;
}

function base64url(str: string | Buffer): string {
  const buf = typeof str === 'string' ? Buffer.from(str) : str;
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function signSession(payload: any): string {
  const withExp = {
    ...payload,
    exp: payload.exp || Date.now() + 1000 * 60 * 60 * 24 * 30,
  };
  const data = base64url(JSON.stringify(withExp));
  const hmac = crypto.createHmac('sha256', getSessionSecret()).update(data).digest();
  const signature = base64url(hmac);
  return `${data}.${signature}`;
}

export function verifySession(cookie: string): SessionUser | null {
  try {
    const [data, signature] = cookie.split('.');
    if (!data || !signature) return null;
    const hmac = crypto.createHmac('sha256', getSessionSecret()).update(data).digest();
    const expectedSignature = base64url(hmac);
    if (signature !== expectedSignature) return null;
    const user = JSON.parse(Buffer.from(data.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8'));
    if (user && typeof user.exp === 'number' && Date.now() > user.exp) {
      return null;
    }
    return user;
  } catch {
    return null;
  }
}