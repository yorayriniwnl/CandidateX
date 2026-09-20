'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, Menu, Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import { NAVIGATION_ITEMS, SURFACE_COPY, type Surface, type SurfaceStatus } from './navigation';
import { SurfaceBadge } from './SurfaceBadge';

export type PlatformHeaderProps = {
  surface: Surface;
  status?: SurfaceStatus;
};

export function PlatformHeader({ surface, status }: PlatformHeaderProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const copy = SURFACE_COPY[surface];

  return (
    <header className="platform-header">
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

        <Link href="/analyze" className="platform-header__cta">
          Start an analysis
          <ArrowUpRight size={15} aria-hidden="true" />
        </Link>
      </div>
    </header>
  );
}
