'use client';

export interface AuthUser {
  email: string;
  role: 'evaluator' | 'candidate';
  name?: string;
  loginTime: number;
}

// In-memory session cache for instant synchronous access in React lifecycle
let memoryUser: AuthUser | null = null;
let sessionFetchPromise: Promise<AuthUser | null> | null = null;

// Safe non-sensitive UI profile storage (display name/avatar cache only)
const CACHE_KEY = 'cx_user_profile_cache';

export function getStoredUser(): AuthUser | null {
  if (memoryUser) return memoryUser;
  if (typeof window === 'undefined') return null;

  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && typeof parsed.email === 'string') {
        memoryUser = parsed as AuthUser;
        return memoryUser;
      }
    }
  } catch {}

  // Clean up any legacy insecure client cookie
  try {
    if (document.cookie.includes('cx_auth=')) {
      document.cookie = 'cx_auth=; path=/; max-age=0; SameSite=Lax';
    }
    if (localStorage.getItem('cx_auth_session')) {
      localStorage.removeItem('cx_auth_session');
    }
  } catch {}

  return null;
}

export function setStoredUser(user: AuthUser): void {
  memoryUser = user;
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(user));
    // Clean up legacy insecure storage
    localStorage.removeItem('cx_auth_session');
    document.cookie = 'cx_auth=; path=/; max-age=0; SameSite=Lax';
    window.dispatchEvent(new Event('cx-auth-change'));
  } catch {}
}

function clearProfileCache(): void {
  memoryUser = null;
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.removeItem(CACHE_KEY);
    localStorage.removeItem('cx_auth_session');
    document.cookie = 'cx_auth=; path=/; max-age=0; SameSite=Lax';
    window.dispatchEvent(new Event('cx-auth-change'));
  } catch {}
}

export function clearStoredUser(): void {
  clearProfileCache();
  if (typeof window === 'undefined') return;
  // Only an explicit sign-out should invalidate the HttpOnly session cookie.
  fetch('/api/auth/signout', { method: 'POST' }).catch(() => {});
}

export async function fetchUserSession(): Promise<AuthUser | null> {
  if (typeof window === 'undefined') return null;
  if (sessionFetchPromise) return sessionFetchPromise;

  sessionFetchPromise = (async () => {
    try {
      const res = await fetch('/api/auth/session', {
        method: 'GET',
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      });
      if (!res.ok) {
        clearProfileCache();
        return null;
      }
      const data = await res.json();
      if (data?.user) {
        const user: AuthUser = {
          email: data.user.email,
          role: data.user.role === 'candidate' ? 'candidate' : 'evaluator',
          name: data.user.name,
          loginTime: data.user.loginTime || Date.now(),
        };
        setStoredUser(user);
        return user;
      } else {
        clearProfileCache();
        return null;
      }
    } catch {
      return getStoredUser();
    } finally {
      sessionFetchPromise = null;
    }
  })();

  return sessionFetchPromise;
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
