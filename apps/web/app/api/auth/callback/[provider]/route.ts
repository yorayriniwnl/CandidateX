import { NextRequest, NextResponse } from 'next/server';
import { signSession } from '../../../../../lib/session';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ provider: string }> }
) {
  const { provider } = await context.params;
  const searchParams = request.nextUrl.searchParams;

  const host = request.headers.get('host') || 'localhost:3000';
  const protocol =
    request.headers.get('x-forwarded-proto') ||
    (host.startsWith('localhost') || host.startsWith('127.0.0.1') ? 'http' : 'https');
  const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_APP_URL || `${protocol}://${host}`;

  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const oauthError = searchParams.get('error');

  if (oauthError) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(oauthError)}&provider=${provider}`, baseUrl)
    );
  }

  if (!code) {
    return NextResponse.redirect(
      new URL(`/login?error=missing_code&provider=${provider}`, baseUrl)
    );
  }

  // Verify state
  let redirectTarget = '/workspace';
  const storedState = request.cookies.get('cx_oauth_state')?.value;

  if (!state || !storedState || state !== storedState) {
    return NextResponse.redirect(
      new URL(`/login?error=invalid_state&provider=${provider}`, baseUrl)
    );
  }

  try {
    const decoded = JSON.parse(Buffer.from(state, 'base64url').toString('utf8'));
    if (decoded.redirect) {
      redirectTarget = decoded.redirect;
    }
  } catch {}

  try {
    let userEmail = '';
    let userName = '';
    let userAvatar = '';

    if (provider === 'github') {
      const clientId = process.env.GITHUB_CLIENT_ID;
      const clientSecret = process.env.GITHUB_CLIENT_SECRET;

      if (!clientId || !clientSecret) {
        return NextResponse.redirect(
          new URL(`/login?error=missing_credentials&provider=github`, baseUrl)
        );
      }

      // Exchange code for token
      const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          code,
          redirect_uri: `${baseUrl}/api/auth/callback/github`,
        }),
      });

      const tokenData = await tokenRes.json();
      if (!tokenData.access_token) {
        throw new Error(tokenData.error_description || 'Failed to exchange GitHub authorization code');
      }

      // Fetch user profile
      const userRes = await fetch('https://api.github.com/user', {
        headers: {
          Authorization: `Bearer ${tokenData.access_token}`,
          'User-Agent': 'CandidateX-Auth',
        },
      });

      const ghUser = await userRes.json();
      userName = ghUser.name || ghUser.login || 'GitHub User';
      userAvatar = ghUser.avatar_url || '';
      userEmail = ghUser.email || '';

      // If email is private, fetch from emails endpoint
      if (!userEmail) {
        const emailsRes = await fetch('https://api.github.com/user/emails', {
          headers: {
            Authorization: `Bearer ${tokenData.access_token}`,
            'User-Agent': 'CandidateX-Auth',
          },
        });
        const emails = await emailsRes.json();
        if (Array.isArray(emails)) {
          const primary = emails.find((e: any) => e.primary && e.verified) || emails[0];
          userEmail = primary?.email || `${ghUser.login}@users.noreply.github.com`;
        }
      }
    } else if (provider === 'google') {
      const clientId = process.env.GOOGLE_CLIENT_ID;
      const clientSecret = process.env.GOOGLE_CLIENT_SECRET;

      if (!clientId || !clientSecret) {
        return NextResponse.redirect(
          new URL(`/login?error=missing_credentials&provider=google`, baseUrl)
        );
      }

      // Exchange code for token
      const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          code,
          client_id: clientId,
          client_secret: clientSecret,
          redirect_uri: `${baseUrl}/api/auth/callback/google`,
          grant_type: 'authorization_code',
        }),
      });

      const tokenData = await tokenRes.json();
      if (!tokenData.access_token) {
        throw new Error(tokenData.error_description || 'Failed to exchange Google authorization code');
      }

      // Fetch Google profile
      const userRes = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
        headers: {
          Authorization: `Bearer ${tokenData.access_token}`,
        },
      });

      const googleUser = await userRes.json();
      userEmail = googleUser.email || '';
      userName = googleUser.name || 'Google User';
      userAvatar = googleUser.picture || '';
    } else {
      return NextResponse.redirect(new URL('/login?error=unsupported_provider', baseUrl));
    }

    const sessionPayload = {
      email: userEmail || `${provider}.user@candidatex.dev`,
      name: userName,
      avatar: userAvatar,
      provider,
      role: 'evaluator',
      loginTime: Date.now(),
    };

    const finalTarget = redirectTarget.startsWith('/') ? redirectTarget : `/${redirectTarget}`;
    const response = NextResponse.redirect(new URL(finalTarget, baseUrl));

    // Set secure authentication cookies
    response.cookies.set('cx_session', signSession(sessionPayload), {
      httpOnly: true,
      secure: protocol === 'https',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 days
    });

    // Clean up any legacy insecure client cookies
    response.cookies.delete('cx_auth');

    // Clear state cookie
    response.cookies.delete('cx_oauth_state');

    return response;
  } catch (err: any) {
    console.error('OAuth Callback Exception:', err);
    return NextResponse.redirect(
      new URL(
        `/login?error=${encodeURIComponent(err.message || 'oauth_exchange_failed')}&provider=${provider}`,
        baseUrl
      )
    );
  }
}
