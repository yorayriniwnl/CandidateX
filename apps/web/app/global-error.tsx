'use client';

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: '#030712', color: '#f1f5f9', fontFamily: 'system-ui, sans-serif', display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <div style={{ textAlign: 'center', padding: '40px 24px', maxWidth: '520px' }}>
          <h1 style={{ fontSize: '1.6rem', letterSpacing: '-0.04em' }}>Something went wrong</h1>
          <p style={{ color: '#94a3b8', fontSize: '15px', lineHeight: 1.7, marginTop: '12px' }}>
            A critical error occurred. No data was lost — resumes and results are request-scoped.
          </p>
          {error.digest && <p style={{ color: '#64748b', fontSize: '12px', marginTop: '12px' }}>Reference: <code>{error.digest}</code></p>}
          <button
            type="button"
            onClick={reset}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px', marginTop: '28px',
              minHeight: '44px', borderRadius: '999px', padding: '0 20px', fontSize: '14px', fontWeight: 650,
              color: '#0a0b10', background: '#c1b8ff', border: 'none', cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
