import Link from 'next/link';
import styles from './landing.module.css';

export default function HomePage() {
  return (
    <main className={styles.page}>
      <nav className={styles.nav} aria-label="Main navigation">
        <Link href="/" className={styles.wordmark} aria-label="CandidateX home">
          <span className={styles.mark} aria-hidden="true">C</span>
          <span>CandidateX</span>
        </Link>
        <div className={styles.navMeta}>
          <span>ROLE-AWARE CAPABILITY INTELLIGENCE</span>
          <Link href="/research-demo">Research demo <span aria-hidden="true">↗</span></Link>
        </div>
      </nav>

      <section className={styles.hero} aria-labelledby="landing-title">
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}><span className={styles.liveDot} /> CandidateX / Evidence OS</p>
          <h1 id="landing-title">Evidence before interviews.</h1>
          <p className={styles.lede}>
            CandidateX turns resumes and supplied public technical sources into an inspectable,
            role-aware capability dossier.
          </p>
          <p className={styles.promise}>Static analysis. Traceable evidence. Explicit unknowns.</p>
          <p className={styles.attribution}>Made by <strong>Archi Srivastava &amp; Ayush Roy</strong> · Under the guidance of <strong>Dr. Debachudamani Prusti</strong></p>
          <div className={styles.actions}>
            <Link href="/analyze" className={styles.primaryAction}>
              Analyze candidate <span aria-hidden="true">→</span>
            </Link>
            <Link href="/research-demo" className={styles.secondaryAction}>
              View research demo <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <p className={styles.disclosure}>
            Decision support for technical interviews. CandidateX does not verify identity, employment,
            or mastery, and it does not make hiring decisions.
          </p>
        </div>

        <div className={styles.flow} aria-label="Evidence moves from candidate declarations and public sources through traceable observations into a capability dossier">
          <div className={styles.flowHead}>
            <span>THE EVIDENCE PATH</span>
            <span className={styles.flowIndex}>01 — 04</span>
          </div>
          <div className={styles.flowGrid}>
            <div className={styles.inputs}>
              <div className={styles.flowNode}>
                <span className={styles.nodeIndex}>01</span>
                <span><strong>Resume</strong><small>Candidate declarations</small></span>
              </div>
              <div className={styles.flowNode}>
                <span className={styles.nodeIndex}>02</span>
                <span><strong>Public sources</strong><small>Repositories · supplied links</small></span>
              </div>
              <div className={styles.connector} aria-hidden="true"><span /><span /></div>
            </div>

            <div className={styles.graphNode}>
              <div className={styles.graphGlyph} aria-hidden="true">
                <span /><span /><span /><span /><span />
                <svg viewBox="0 0 130 100" role="presentation">
                  <path d="M19 23 59 48M19 76 59 53M70 49l38-27M70 54l38 25M65 49v30" />
                </svg>
              </div>
              <strong>Evidence graph</strong>
              <small>Observation · source · provenance</small>
            </div>

            <div className={styles.outcome} aria-hidden="true">
              <span className={styles.outcomeLine} />
              <span className={styles.outcomeArrow}>→</span>
            </div>
            <div className={styles.dossierNode}>
              <span className={styles.dossierGlyph} aria-hidden="true">CX</span>
              <strong>Capability dossier</strong>
              <small>Estimates with explicit unknowns</small>
            </div>
          </div>
          <div className={styles.flowFoot}>
            <span><i className={styles.legendObserved} /> OBSERVED</span>
            <span><i className={styles.legendUnknown} /> UNKNOWN</span>
            <span><i className={styles.legendRole} /> ROLE CONTEXT</span>
          </div>
        </div>
      </section>

      <div className={styles.bottomRail}>
        <span>01 <b>Inspect declared inputs</b></span>
        <span>02 <b>Trace static evidence</b></span>
        <span>03 <b>Surface gaps to investigate</b></span>
        <span className={styles.bottomNote}>NO CODE EXECUTION · NO SYNTHETIC LIVE RESULTS</span>
      </div>
    </main>
  );
}
