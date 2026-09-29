import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const SECRET = process.env.SESSION_SECRET || 'dev-insecure-fallback-change-me';

async function verifySessionWebCrypto(cookie: string): Promise<any | null> {
  try {
    const [data, signature] = cookie.split('.');
    if (!data || !signature) return null;
    
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(SECRET),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const hmac = await crypto.subtle.sign(
      'HMAC',
      key,
      encoder.encode(data)
    );
    
    const hmacArray = Array.from(new Uint8Array(hmac));
    const hmacBase64 = btoa(String.fromCharCode.apply(null, hmacArray));
    const expectedSignature = hmacBase64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    
    if (signature !== expectedSignature) return null;
    
    const decodedStr = atob(data.replace(/-/g, '+').replace(/_/g, '/'));
    const user = JSON.parse(decodedStr);
    if (user && typeof user.exp === 'number' && Date.now() > user.exp) {
      return null;
    }
    return user;
  } catch (err) {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  const isProtected = ['/workspace', '/analyze', '/hr'].some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
  
  if (isProtected) {
    const sessionCookie = request.cookies.get('cx_session')?.value;
    const isValid = sessionCookie ? await verifySessionWebCrypto(sessionCookie) : null;
    
    if (!isValid) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  return response;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
