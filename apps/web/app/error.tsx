'use client';

import { useEffect } from 'react';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // TODO: Send to error reporting service (Sentry, etc.)
    console.error('[CandidateX Error]', error);
  }, [error]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-6">
      <div className="glass-card max-w-md w-full p-8 text-center space-y-4">
        <div className="w-12 h-12 mx-auto rounded-full bg-red-500/10 flex items-center justify-center">
          <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
        </div>
        <h2 className="text-lg font-semibold text-slate-100">Something went wrong</h2>
        <p className="text-sm text-slate-400">{error.message || 'An unexpected error occurred.'}</p>
        {error.digest && <p className="text-xs text-slate-500 font-mono">Error ID: {error.digest}</p>}
        <button onClick={reset} className="mt-4 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors">Try again</button>
      </div>
    </div>
  );
}
