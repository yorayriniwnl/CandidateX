'use client';

import { useEffect, useLayoutEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

export function NavigationScrollManager() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Prevent browser from automatically restoring previous scroll position across route changes
  useEffect(() => {
    if (typeof window !== 'undefined' && 'scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }
  }, []);

  // When pathname or searchParams change (i.e. on navigation/redirect), force page to open from the top
  useLayoutEffect(() => {
    if (typeof window === 'undefined') return;

    // If an in-page hash anchor is targeted (e.g. /#loop-title), allow scrolling to that element
    if (window.location.hash) {
      const targetId = window.location.hash.replace('#', '');
      const targetElement = document.getElementById(targetId);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth' });
        return;
      }
    }

    // Temporarily force scroll-behavior to auto to prevent smooth scrolling from clamping mid-way
    const html = document.documentElement;
    const previousBehavior = html.style.scrollBehavior;
    html.style.scrollBehavior = 'auto';

    const scrollToTop = () => {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    };

    // Immediate scroll
    scrollToTop();

    // Re-check across animation frames and after DOM hydration/layout stabilization
    const rafId = requestAnimationFrame(() => {
      scrollToTop();
    });

    const timer1 = setTimeout(scrollToTop, 20);
    const timer2 = setTimeout(scrollToTop, 80);
    const timer3 = setTimeout(scrollToTop, 180);

    // Restore previous scroll-behavior after page settles
    const restoreTimer = setTimeout(() => {
      html.style.scrollBehavior = previousBehavior;
    }, 250);

    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(restoreTimer);
      html.style.scrollBehavior = previousBehavior;
    };
  }, [pathname, searchParams]);

  return null;
}
