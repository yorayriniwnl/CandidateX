'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  Eye,
  EyeOff,
  Fingerprint,
  FileCode2,
  Lock,
  Mail,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  UserCheck,
  X,
  AlertCircle,
  CheckCircle2,
  Loader2,
  LogOut,
} from 'lucide-react';
import { setStoredUser, getStoredUser, clearStoredUser, fetchUserSession, type AuthUser } from '../../lib/auth';
import styles from './login.module.css';

type UserRole = 'evaluator' | 'candidate';

interface DemoAccount {
  label: string;
  role: UserRole;
  email: string;
  pass: string;
  description: string;
}

const STATIC_ACCOUNTS: DemoAccount[] = [
  {
    label: 'Yorayriniwnl',
    role: 'evaluator',
    email: 'Yorayriniwnl',
    pass: 'Yorayriniwnl',
    description: 'Lead Evaluator & Workspace Admin',
  },
  {
    label: 'Archi',
    role: 'candidate',
    email: 'Archi',
    pass: 'Archi',
    description: 'Candidate Profile & Evidence Reviewer',
  },
];

export function LoginClient() {
  const [role, setRole] = useState<UserRole>('evaluator');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [socialLoading, setSocialLoading] = useState<'github' | 'google' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitted, setForgotSubmitted] = useState(false);

  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
    setCurrentUser(getStoredUser());
    fetchUserSession().then((u) => {
      if (u) setCurrentUser(u);
    });

    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const err = params.get('error');
      const prov = params.get('provider');
      if (err === 'missing_credentials') {
        setError(
          `Real ${prov === 'github' ? 'GitHub' : 'Google'} OAuth requires ${prov?.toUpperCase()}_CLIENT_ID and ${prov?.toUpperCase()}_CLIENT_SECRET configured in .env.local. You can also use the instant demo credentials below.`
        );
      } else if (err === 'oauth_denied') {
        setError(`${prov === 'github' ? 'GitHub' : 'Google'} sign in was cancelled.`);
      } else if (err) {
        setError(`Authentication issue: ${err}`);
      }
    }
  }, []);

  const handleSignOut = () => {
    clearStoredUser();
    setCurrentUser(null);
    setEmail('');
    setPassword('');
  };

  const getRedirectTarget = () => {
    if (typeof window === 'undefined') return null;
    const params = new URLSearchParams(window.location.search);
    const target = params.get('redirect') || params.get('next');
    if (!target?.startsWith('/')) return null;
    try {
      const url = new URL(target, window.location.origin);
      if (url.origin !== window.location.origin) return null;
      return url.pathname + url.search + url.hash;
    } catch {
      return null;
    }
  };

  const handleRoleSelect = (newRole: UserRole) => {
    setRole(newRole);
    setError(null);
  };

  const handleQuickFill = (account: DemoAccount) => {
    setRole(account.role);
    setEmail(account.email);
    setPassword(account.pass);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Basic validation
    if (!email.trim()) {
      setError('Please enter your email or username.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    const trimmedInput = email.trim().toLowerCase();
    const matchedAccount = STATIC_ACCOUNTS.find(
      (acc) =>
        acc.email.toLowerCase() === trimmedInput &&
        (acc.pass === password || acc.pass.toLowerCase() === password.toLowerCase())
    );

    if (!matchedAccount) {
      setError('Invalid credentials. Access is restricted to authorized static accounts.');
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password, role }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Invalid credentials. Access is restricted to authorized static accounts.');
        setIsSubmitting(false);
        return;
      }

      setStoredUser({
        email: data.user.email,
        role: data.user.role,
        name: data.user.name,
        loginTime: Date.now(),
      });

      setSuccess('Identity verified. Loading CandidateX workspace...');
      await new Promise((resolve) => setTimeout(resolve, 400));

      const redirectTarget = getRedirectTarget();
      if (typeof window !== 'undefined') {
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
      }
      // Request the destination with the new cookie instead of reusing an
      // unauthenticated redirect prefetched into Next's client router cache.
      window.location.assign(redirectTarget || (data.user.role === 'evaluator' ? '/workspace' : '/analyze'));
    } catch (err) {
      setError('Authentication failed. Please verify your credentials and try again.');
      setIsSubmitting(false);
    }
  };

  const handleSocialAuth = (provider: 'github' | 'google') => {
    setError(null);
    setSocialLoading(provider);

    const redirectTarget = getRedirectTarget() || (role === 'evaluator' ? '/workspace' : '/analyze');
    window.location.href = `/api/auth/${provider}?redirect=${encodeURIComponent(redirectTarget)}`;
  };

  const handleForgotSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail.trim()) return;
    setForgotSubmitted(true);
  };

  return (
    <main className={styles.loginMain}>
      <div className={styles.loginGrid}>
        {/* Left Column: Product Narrative & Guarantees */}
        <section className={styles.narrative} aria-labelledby="narrative-heading">
          <p className={styles.eyebrow}>
            <span className={styles.statusDot} aria-hidden="true" />
            01 / SECURE ACCESS
          </p>
          <h1 id="narrative-heading" className={styles.narrativeTitle}>
            Candidate<br />
            intelligence,<br />
            <span>with receipts.</span>
          </h1>
          <p className={styles.narrativeDescription}>
            Sign in to inspect evidence graphs, trace candidate claims to their repository provenance,
            and structure technical interviews with complete rigor and transparency.
          </p>

          <div className={styles.principlesList} aria-label="CandidateX Invariants">
            <article className={styles.principleItem}>
              <div className={styles.principleIcon} aria-hidden="true">
                <Fingerprint size={16} strokeWidth={1.4} />
              </div>
              <div className={styles.principleText}>
                <div className={styles.principleHeader}>
                  <span className={styles.principleNumber}>01 /</span>
                  <h2 className={styles.principleHeading}>Closed-world candidate manifest</h2>
                </div>
                <p className={styles.principleBody}>
                  Analysis is constrained strictly to resources explicitly declared by the candidate.
                  Zero unconstrained scraping.
                </p>
              </div>
            </article>

            <article className={styles.principleItem}>
              <div className={styles.principleIcon} aria-hidden="true">
                <FileCode2 size={16} strokeWidth={1.4} />
              </div>
              <div className={styles.principleText}>
                <div className={styles.principleHeader}>
                  <span className={styles.principleNumber}>02 /</span>
                  <h2 className={styles.principleHeading}>Candidate code is never executed</h2>
                </div>
                <p className={styles.principleBody}>
                  All repositories are analyzed safely via static AST parsers and text analyzers.
                  No containers or untrusted executions.
                </p>
              </div>
            </article>

            <article className={styles.principleItem}>
              <div className={styles.principleIcon} aria-hidden="true">
                <ScanSearch size={16} strokeWidth={1.4} />
              </div>
              <div className={styles.principleText}>
                <div className={styles.principleHeader}>
                  <span className={styles.principleNumber}>03 /</span>
                  <h2 className={styles.principleHeading}>Unknown stays unknown</h2>
                </div>
                <p className={styles.principleBody}>
                  Missing evidence lowers coverage; it is never penalized as an arbitrary zero score.
                  Human judgment makes the final call.
                </p>
              </div>
            </article>
          </div>

          <div>
            <div className={styles.securityFootprint}>
              <ShieldCheck size={14} aria-hidden="true" />
              <span>TLS 1.3 / AES-256 · ED25519 SIGNED LEDGER · ROLE-BASED ACCESS</span>
            </div>
          </div>
        </section>

        {/* Right Column: Authentication Card */}
        <section className={styles.authContainer} aria-labelledby="auth-card-title">
          <div className={styles.authCard} data-hydrated={hydrated ? 'true' : 'false'}>
            {/* Role Switcher */}
            <div className={styles.roleSwitcher} role="tablist" aria-label="Select role">
              <button
                type="button"
                role="tab"
                aria-selected={role === 'evaluator'}
                className={styles.roleTab}
                onClick={() => handleRoleSelect('evaluator')}
              >
                <UserCheck size={14} aria-hidden="true" />
                <span>Interviewer / Hiring</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={role === 'candidate'}
                className={styles.roleTab}
                onClick={() => handleRoleSelect('candidate')}
              >
                <Sparkles size={14} aria-hidden="true" />
                <span>Candidate / Reviewer</span>
              </button>
            </div>

            {currentUser && (
              <div className="mb-4 p-2.5 rounded-xl bg-[#bba0d510] border border-[#b99cd025] flex items-center justify-between text-xs text-[#cfb7eb]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d39988]" />
                  <span>Active session: <strong>{currentUser.email}</strong></span>
                </div>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors bg-white/5 hover:bg-white/10 px-2 py-0.5 rounded-md"
                >
                  <LogOut size={12} />
                  <span>Switch account</span>
                </button>
              </div>
            )}

            <div className={styles.cardHead}>
              <h2 id="auth-card-title" className={styles.cardTitle}>
                {role === 'evaluator' ? 'Sign in to workspace' : 'Review your evidence'}
              </h2>
              <p className={styles.cardSubtitle}>
                {role === 'evaluator'
                  ? 'Access candidate dossiers, capability matrices, and interview probes.'
                  : 'Inspect your extraction receipt and declared evidence claims.'}
              </p>
            </div>

            {/* Quick Demo Fill */}
            <div className={styles.demoBar}>
              <div className={styles.demoBarHeader}>
                <span className={styles.demoBarLabel}>Authorized static credentials</span>
                <span className={styles.demoBarBadge}>Instant fill</span>
              </div>
              <div className={styles.demoButtons}>
                {STATIC_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.label}
                    type="button"
                    className={styles.demoPill}
                    onClick={() => handleQuickFill(acc)}
                    title={acc.description}
                  >
                    <Sparkles size={11} aria-hidden="true" />
                    <span>{acc.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Social SSO Buttons */}
            <div className={styles.ssoGrid}>
              <button
                type="button"
                className={styles.ssoButton}
                onClick={() => handleSocialAuth('github')}
                disabled={socialLoading !== null || isSubmitting}
                aria-label="Continue with GitHub"
              >
                {socialLoading === 'github' ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    />
                  </svg>
                )}
                <span>GitHub</span>
              </button>

              <button
                type="button"
                className={styles.ssoButton}
                onClick={() => handleSocialAuth('google')}
                disabled={socialLoading !== null || isSubmitting}
                aria-label="Continue with Google"
              >
                {socialLoading === 'google' ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      fill="#EA4335"
                      d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z"
                    />
                    <path
                      fill="#4285F4"
                      d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5.1 3.7-8.8z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.8 0 12s.7 3.3 1.9 5.7l3.7-2.9z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z"
                    />
                  </svg>
                )}
                <span>Google</span>
              </button>
            </div>

            <div className={styles.divider}>
              <span>or continue with email or username</span>
            </div>

            {/* Status Feedback */}
            {error && (
              <div role="alert" data-testid="login-error" className={`${styles.alertBox} ${styles.alertError}`}>
                <AlertCircle size={16} className="shrink-0" />
                <div>{error}</div>
              </div>
            )}
            {success && (
              <div role="status" data-testid="login-success" className={`${styles.alertBox} ${styles.alertSuccess}`}>
                <CheckCircle2 size={16} className="shrink-0" />
                <div>{success}</div>
              </div>
            )}

            {/* Email / Password Form */}
            <form onSubmit={handleSubmit} action="#" method="POST" className={styles.form} noValidate>
              <div className={styles.fieldGroup}>
                <div className={styles.fieldLabelRow}>
                  <label htmlFor="login-email" className={styles.fieldLabel}>
                    Email or Username
                  </label>
                </div>
                <div className={styles.inputWrapper}>
                  <div className={styles.inputIcon}>
                    <Mail size={16} aria-hidden="true" />
                  </div>
                  <input
                    id="login-email"
                    type="text"
                    name="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter email or username"
                    autoComplete="username"
                    className={styles.inputControl}
                    aria-invalid={!!error && !email.trim()}
                    disabled={isSubmitting}
                  />
                  {email.length > 0 && !isSubmitting && (
                    <div className={styles.trailingAction}>
                      <button
                        type="button"
                        onClick={() => setEmail('')}
                        className={styles.iconButton}
                        aria-label="Clear email or username"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <div className={styles.fieldLabelRow}>
                  <label htmlFor="login-password" className={styles.fieldLabel}>
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setForgotEmail(email);
                      setForgotSubmitted(false);
                      setForgotModalOpen(true);
                    }}
                    className={styles.forgotLink}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className={styles.inputWrapper}>
                  <div className={styles.inputIcon}>
                    <Lock size={16} aria-hidden="true" />
                  </div>
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    autoComplete="current-password"
                    className={styles.inputControl}
                    aria-invalid={!!error && !password}
                    disabled={isSubmitting}
                  />
                  <div className={styles.trailingAction}>
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className={styles.iconButton}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
              </div>

              <div className={styles.optionsRow}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className={styles.checkboxInput}
                  />
                  <span>Remember this device for 30 days</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className={styles.submitAction}
              >
                <span>
                  {isSubmitting ? (
                    <Loader2 size={17} className="animate-spin" />
                  ) : (
                    <ArrowRight size={17} aria-hidden="true" />
                  )}
                </span>
                <strong>{isSubmitting ? 'Authenticating...' : 'Sign in to workspace'}</strong>
                <span aria-hidden="true" style={{ opacity: 0 }}>
                  <ArrowRight size={17} />
                </span>
              </button>
            </form>

            <div className={styles.cardFooter}>
              <span>Need access or credentials?</span>
              <button
                type="button"
                onClick={() => handleQuickFill(STATIC_ACCOUNTS[0])}
                className={styles.cardFooterLink}
              >
                Use authorized demo credentials
              </button>
            </div>
          </div>
        </section>
      </div>

      {/* Forgot Password Modal */}
      {forgotModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="forgot-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md"
        >
          <div className="relative w-full max-w-md p-6 rounded-2xl bg-[#140f1d] border border-[#b89bd334] shadow-[0_30px_100px_#0009] text-left">
            <button
              type="button"
              onClick={() => setForgotModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200"
              aria-label="Close dialog"
            >
              <X size={18} />
            </button>
            <h3 id="forgot-title" className="text-lg font-medium text-[#ede5f5] mb-2">
              Reset your password
            </h3>
            {forgotSubmitted ? (
              <div className="mt-4">
                <p className="text-xs text-slate-300 leading-relaxed">
                  If an account exists for <strong className="text-white">{forgotEmail}</strong>, we have dispatched a secure recovery token with verification instructions.
                </p>
                <button
                  type="button"
                  onClick={() => setForgotModalOpen(false)}
                  className="mt-6 w-full py-2.5 rounded-full bg-[#dfcff3] text-[#291c36] text-xs font-semibold hover:bg-[#f0e3ff] transition-colors"
                >
                  Return to sign in
                </button>
              </div>
            ) : (
              <form onSubmit={handleForgotSubmit} className="mt-4 space-y-4">
                <p className="text-xs text-[#9d8fa9] leading-relaxed">
                  Enter your verified email or username and we will send you a cryptographic reset link.
                </p>
                <div>
                  <label htmlFor="forgot-email" className="block text-xs text-slate-400 mb-1.5 font-medium">
                    Email or username
                  </label>
                  <input
                    id="forgot-email"
                    type="text"
                    required
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="Enter email or username"
                    className="w-full h-10 px-3.5 rounded-xl bg-[#0b0811] border border-[#b99cc62b] text-slate-100 text-xs focus:outline-none focus:border-[#ba98df88]"
                  />
                </div>
                <div className="flex gap-2.5 pt-2">
                  <button
                    type="button"
                    onClick={() => setForgotModalOpen(false)}
                    className="flex-1 py-2 rounded-full border border-white/10 text-slate-300 text-xs hover:bg-white/5"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-2 rounded-full bg-[#dfcff3] text-[#291c36] text-xs font-semibold hover:bg-[#f0e3ff]"
                  >
                    Send reset link
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
