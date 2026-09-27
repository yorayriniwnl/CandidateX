'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, Menu, Sparkles, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { NAVIGATION_ITEMS, SURFACE_COPY, type Surface, type SurfaceStatus } from './navigation';
import { SurfaceBadge } from './SurfaceBadge';
import { AnalyzeLink } from './AnalyzeLink';
import { getStoredUser, clearStoredUser, type AuthUser } from '../../lib/auth';

export type PlatformHeaderProps = {
  surface: Surface;
  status?: SurfaceStatus;
};

export function PlatformHeader({ surface, status }: PlatformHeaderProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const copy = SURFACE_COPY[surface];

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
        document.querySelector<HTMLButtonElement>('.platform-menu-toggle')?.focus();
      }
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [menuOpen]);

  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setCurrentUser(getStoredUser());
    const onAuthChange = () => setCurrentUser(getStoredUser());
    window.addEventListener('cx-auth-change', onAuthChange);
    window.addEventListener('storage', onAuthChange);
    return () => {
      window.removeEventListener('cx-auth-change', onAuthChange);
      window.removeEventListener('storage', onAuthChange);
    };
  }, []);

  return (
    <header className="platform-header" data-surface={surface}>
      <div className="platform-header__inner">
        <Link href="/" className="platform-brand" aria-label="CandidateX home">
          <span className="platform-brand__mark" aria-hidden="true"><Sparkles size={16} /></span>
          <span className="platform-brand__wordmark">CandidateX</span>
        </Link>

        <div className="platform-context" aria-label={`${copy.label}: ${copy.descriptor}`}>
          <span className="platform-context__slash">/</span>
          <span className="platform-context__label">{copy.label}</span>
          <span className="platform-context__descriptor">{copy.descriptor}</span>
        </div>

        <button
          type="button"
          className="platform-menu-toggle"
          aria-label="Toggle navigation"
          aria-controls="platform-navigation"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        <nav
          id="platform-navigation"
          className={`platform-navigation${menuOpen ? ' platform-navigation--open' : ''}`}
          aria-label="Primary navigation"
        >
          {NAVIGATION_ITEMS.map((item) => {
            const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
            return (
              <Link
                key={item.key}
                href={item.href}
                className={`platform-navigation__link${isActive ? ' platform-navigation__link--active' : ''}`}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {status && <SurfaceBadge status={status} />}

        {currentUser ? (
          <div className="hidden md:flex items-center gap-2.5 text-xs">
            <span className="text-[#a491b8]">{currentUser.email.split('@')[0]}</span>
            <button
              type="button"
              onClick={() => {
                clearStoredUser();
                setCurrentUser(null);
              }}
              className="text-[#8e7b9f] hover:text-[#e4d7fa] transition-colors text-[11px]"
            >
              Sign out
            </button>
          </div>
        ) : surface !== 'login' ? (
          <Link
            href="/login"
            className="hidden md:inline-flex items-center text-[11px] text-[#a89bb8] hover:text-[#efe6f8] px-2 py-1 transition-colors"
          >
            Sign in
          </Link>
        ) : null}

        <AnalyzeLink targetHref="/analyze" className="platform-header__cta">
          Start an analysis
          <ArrowUpRight size={15} aria-hidden="true" />
        </AnalyzeLink>
      </div>
    </header>
  );
}
