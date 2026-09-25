import Link from 'next/link';

export default function NotFound() {
  return (
    <main style={{ display: 'grid', placeItems: 'center', minHeight: 'calc(100vh - 160px)', padding: '40px 24px', textAlign: 'center' }}>
      <div style={{ maxWidth: '480px' }}>
        <p style={{ color: '#68728a', fontSize: '12px', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '16px', fontFamily: 'var(--font-mono), monospace' }}>
          404 · PAGE NOT FOUND
        </p>
        <h1 style={{ color: '#f8fafc', fontSize: '2rem', letterSpacing: '-0.04em', margin: '0 0 16px' }}>This page does not exist</h1>
        <p style={{ color: '#a5afc4', fontSize: '15px', lineHeight: 1.7 }}>
          CandidateX doesn&apos;t retain resumes, dossiers, or results across requests. If you had a dossier open, start a new evaluation.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '32px' }}>
          <Link
            href="/"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px', minHeight: '44px',
              borderRadius: '999px', padding: '0 20px', fontSize: '13px', fontWeight: 650,
              color: '#d4d0ff', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(175,164,255,0.24)',
              textDecoration: 'none',
            }}
          >
            Home
          </Link>
          <Link
            href="/analyze"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px', minHeight: '44px',
              borderRadius: '999px', padding: '0 20px', fontSize: '13px', fontWeight: 650,
              color: '#0a0b10', background: '#c1b8ff', border: 'none', textDecoration: 'none',
            }}
          >
            Start an analysis
          </Link>
        </div>
      </div>
    </main>
  );
}
