import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ provider: string }> }
) {
  const { provider } = await context.params;
  const searchParams = request.nextUrl.searchParams;
  const redirectTarget = searchParams.get('redirect') || '/workspace';

  const host = request.headers.get('host') || 'localhost:3000';
  const protocol =
    request.headers.get('x-forwarded-proto') ||
    (host.startsWith('localhost') || host.startsWith('127.0.0.1') ? 'http' : 'https');
  const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_APP_URL || `${protocol}://${host}`;

  // Unique CSRF state containing destination
  const stateToken = crypto.randomUUID();
  const statePayload = Buffer.from(
    JSON.stringify({ token: stateToken, redirect: redirectTarget })
  ).toString('base64url');

  if (provider === 'github') {
    const clientId = process.env.GITHUB_CLIENT_ID;
    if (!clientId) {
      return NextResponse.redirect(
        new URL(
          `/login?error=missing_credentials&provider=github&redirect=${encodeURIComponent(redirectTarget)}`,
          baseUrl
        )
      );
    }

    const callbackUrl = `${baseUrl}/api/auth/callback/github`;
    const githubUrl = new URL('https://github.com/login/oauth/authorize');
    githubUrl.searchParams.set('client_id', clientId);
    githubUrl.searchParams.set('redirect_uri', callbackUrl);
    githubUrl.searchParams.set('scope', 'read:user user:email');
    githubUrl.searchParams.set('state', statePayload);

    const response = NextResponse.redirect(githubUrl);
    response.cookies.set('cx_oauth_state', statePayload, {
      httpOnly: true,
      secure: protocol === 'https',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 15, // 15 minutes
    });

    return response;
  }

  if (provider === 'google') {
    const clientId = process.env.GOOGLE_CLIENT_ID;
    if (!clientId) {
      return NextResponse.redirect(
        new URL(
          `/login?error=missing_credentials&provider=google&redirect=${encodeURIComponent(redirectTarget)}`,
          baseUrl
        )
      );
    }

    const callbackUrl = `${baseUrl}/api/auth/callback/google`;
    const googleUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    googleUrl.searchParams.set('client_id', clientId);
    googleUrl.searchParams.set('redirect_uri', callbackUrl);
    googleUrl.searchParams.set('response_type', 'code');
    googleUrl.searchParams.set('scope', 'openid email profile');
    googleUrl.searchParams.set('state', statePayload);
    googleUrl.searchParams.set('access_type', 'offline');
    googleUrl.searchParams.set('prompt', 'select_account');

    const response = NextResponse.redirect(googleUrl);
    response.cookies.set('cx_oauth_state', statePayload, {
      httpOnly: true,
      secure: protocol === 'https',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 15,
    });

    return response;
  }

  return NextResponse.redirect(new URL('/login?error=unsupported_provider', baseUrl));
}
