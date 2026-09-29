import { NextRequest, NextResponse } from 'next/server';
import { signSession } from '../../../../lib/session';

interface DemoAccount {
  label: string;
  role: 'evaluator' | 'candidate';
  email: string;
  pass: string;
}

const STATIC_ACCOUNTS: DemoAccount[] = [
  {
    label: 'Yorayriniwnl',
    role: 'evaluator',
    email: 'Yorayriniwnl',
    pass: 'Yorayriniwnl',
  },
  {
    label: 'Archi',
    role: 'candidate',
    email: 'Archi',
    pass: 'Archi',
  },
];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, role } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required.' },
        { status: 400 }
      );
    }

    const trimmedInput = String(email).trim().toLowerCase();
    const matchedAccount = STATIC_ACCOUNTS.find(
      (acc) =>
        acc.email.toLowerCase() === trimmedInput &&
        (acc.pass === password || acc.pass.toLowerCase() === String(password).toLowerCase())
    );

    if (!matchedAccount) {
      return NextResponse.json(
        { error: 'Invalid credentials. Access is restricted to authorized accounts.' },
        { status: 401 }
      );
    }

    const effectiveRole = role === 'candidate' || role === 'evaluator' ? role : matchedAccount.role;

    const sessionPayload = {
      email: matchedAccount.email,
      name: matchedAccount.label,
      role: effectiveRole,
      provider: 'credentials',
      loginTime: Date.now(),
    };

    const signedToken = signSession(sessionPayload);

    const isSecure = process.env.NODE_ENV === 'production' && request.nextUrl.protocol === 'https:';

    const response = NextResponse.json({
      success: true,
      user: {
        email: matchedAccount.email,
        name: matchedAccount.label,
        role: effectiveRole,
      },
    });

    // Set secure, HttpOnly signed session cookie
    response.cookies.set('cx_session', signedToken, {
      httpOnly: true,
      secure: isSecure,
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 days
    });

    // Delete any legacy insecure cookies
    response.cookies.delete('cx_auth');

    return response;
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || 'Authentication error occurred.' },
      { status: 500 }
    );
  }
}
