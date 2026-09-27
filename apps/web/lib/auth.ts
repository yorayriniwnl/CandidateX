'use client';

export interface AuthUser {
  email: string;
  role: 'evaluator' | 'candidate';
  name?: string;
  loginTime: number;
}

const STORAGE_KEY = 'cx_auth_session';
const COOKIE_NAME = 'cx_auth';

export function getStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && typeof parsed.email === 'string') {
        return parsed as AuthUser;
      }
    }

    // Cookie fallback set by OAuth callback
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const [key, val] = c.trim().split('=');
      if (key === COOKIE_NAME && val) {
        const email = decodeURIComponent(val);
        const user: AuthUser = {
          email,
          role: 'evaluator',
          loginTime: Date.now(),
        };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
        } catch {}
        return user;
      }
    }
  } catch {
    return null;
  }
  return null;
}

export function setStoredUser(user: AuthUser): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(user.email)}; path=/; max-age=2592000; SameSite=Lax`;
    window.dispatchEvent(new Event('cx-auth-change'));
  } catch {}
}

export function clearStoredUser(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(STORAGE_KEY);
    document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
    window.dispatchEvent(new Event('cx-auth-change'));
    // Call server signout to clear httpOnly session
    fetch('/api/auth/signout', { method: 'POST' }).catch(() => {});
  } catch {}
}

export function isUserAuthenticated(): boolean {
  return getStoredUser() !== null;
}

export function getAnalyzeTargetUrl(target: string = '/analyze'): string {
  if (typeof window !== 'undefined' && isUserAuthenticated()) {
    return target;
  }
  return `/login?redirect=${encodeURIComponent(target)}`;
}
