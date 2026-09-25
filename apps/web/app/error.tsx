'use client';

import styles from './home.module.css';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className={styles.home}>
      <main className={styles.homeMain} style={{ paddingTop: '120px', textAlign: 'center' }}>
        <h1 style={{ color: '#f8fafc', fontSize: '2rem', letterSpacing: '-0.04em' }}>Something went wrong</h1>
        <p style={{ color: '#a5afc4', fontSize: '16px', lineHeight: 1.7, marginTop: '16px', maxWidth: '480px', marginInline: 'auto' }}>
          {error.message || 'An unexpected error occurred. No data was lost — your resume and results are request-scoped.'}
        </p>
        {error.digest && <p style={{ color: '#68728a', fontSize: '12px', marginTop: '12px' }}>Error reference: <code>{error.digest}</code></p>}
        <button
          type="button"
          onClick={reset}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px', marginTop: '32px',
            minHeight: '48px', borderRadius: '999px', padding: '0 24px', fontSize: '14px', fontWeight: 650,
            color: '#0a0b10', background: '#c1b8ff', border: 'none', cursor: 'pointer',
          }}
        >
          Try again
        </button>
      </main>
    </div>
  );
}
