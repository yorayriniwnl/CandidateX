'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { isUserAuthenticated, getAnalyzeTargetUrl } from '../../lib/auth';

export interface AnalyzeLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  targetHref?: string;
  className?: string;
  children: React.ReactNode;
}

export function AnalyzeLink({
  targetHref = '/analyze',
  className,
  children,
  onClick,
  ...props
}: AnalyzeLinkProps) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
    setAuthenticated(isUserAuthenticated());

    const handleAuthChange = () => {
      setAuthenticated(isUserAuthenticated());
    };

    window.addEventListener('cx-auth-change', handleAuthChange);
    window.addEventListener('storage', handleAuthChange);

    return () => {
      window.removeEventListener('cx-auth-change', handleAuthChange);
      window.removeEventListener('storage', handleAuthChange);
    };
  }, []);

  const href = mounted && authenticated ? targetHref : `/login?redirect=${encodeURIComponent(targetHref)}`;

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented) return;

    if (!isUserAuthenticated()) {
      e.preventDefault();
      router.push(`/login?redirect=${encodeURIComponent(targetHref)}`);
    }
  };

  return (
    <Link href={href} onClick={handleClick} className={className} {...props}>
      {children}
    </Link>
  );
}
