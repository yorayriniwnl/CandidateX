import { ArrowDown, ArrowRight, ArrowUpRight, Fingerprint, ScanSearch, MessagesSquare } from 'lucide-react';
import Link from 'next/link';
import { SignalConstellation } from '../components/home/SignalConstellation';
import { EvidenceWalkthrough } from '../components/home/EvidenceWalkthrough';
import { PlatformHeader } from '../components/navigation/PlatformHeader';
import { AnalyzeLink } from '../components/navigation/AnalyzeLink';
import styles from './home.module.css';

export default function HomePage() {
  return (
    <div className={styles.home}>
      <PlatformHeader surface="home" />
      <main className={styles.homeMain}>
        <section className={styles.hero} aria-labelledby="home-title">
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}><span className={styles.statusDot} /> Human potential. Real evidence.</p>
            <h1 id="home-title">Candidate<br />intelligence,<br /><span>with receipts.</span></h1>
            <p className={styles.heroDescription}>Go beyond what a résumé says. Connect the claims, explore the work, and walk into every interview with better questions.</p>
            <div className={styles.heroActions}>
              <AnalyzeLink targetHref="/analyze" className={styles.primaryAction}>Start with live evidence <span><ArrowUpRight size={17} aria-hidden="true" /></span></AnalyzeLink>
              <Link href="#loop-title" className={styles.secondaryAction}>Explore the process <ArrowDown size={14} aria-hidden="true" /></Link>
            </div>
            <p className={styles.heroNote}><span /> Evidence informs. People decide.</p>
          </div>
          <div className={styles.heroVisual}><SignalConstellation /></div>
          <div className={styles.heroFootnote}><span>INTELLIGENCE, MADE TRACEABLE.</span><a href="#loop-title">Follow the evidence <ArrowDown size={12} aria-hidden="true" /></a><span>EST. IN CURIOSITY / BUILT FOR CLARITY</span></div>
        </section>

        <div className={styles.principleRail} aria-label="Product principles">
          <p>A fuller picture.<br /><strong>A sharper conversation.</strong></p>
          <div><strong>12<span> /</span></strong><span>Capability dimensions</span></div>
          <div><strong>06<span> /</span></strong><span>Role-specific lenses</span></div>
          <div><strong>Human<span> /</span></strong><span>The final judgment. Always.</span></div>
        </div>

        <section className={styles.loopSection} aria-labelledby="loop-title">
          <div className={styles.sectionHeading}>
            <div><p className={styles.sectionEyebrow}>01 / THE EVIDENCE LOOP</p><h2 id="loop-title">From a claim.<br /><span>To a conversation.</span></h2></div>
            <p>There is a story behind every skill.<br />Follow one thread from a résumé to the question worth asking.</p>
          </div>
          <EvidenceWalkthrough />
        </section>

        <section className={styles.trustSection} aria-labelledby="trust-title">
          <div className={styles.trustIntro}><p className={styles.sectionEyebrow}>02 / BUILT WITH INTENTION</p><h2 id="trust-title">Powerful intelligence.<br /><span>Considered boundaries.</span></h2></div>
          <div className={styles.trustGrid}>
            <article><Fingerprint size={25} strokeWidth={1.2} aria-hidden="true" /><span className={styles.trustNumber}>01</span><h3>The person comes first.</h3><p>Evidence supports an interviewer’s judgment. CandidateX never makes the hiring decision.</p></article>
            <article><ScanSearch size={25} strokeWidth={1.2} aria-hidden="true" /><span className={styles.trustNumber}>02</span><h3>Unknown stays unknown.</h3><p>A missing signal is a reason to ask. Unobserved capability is never quietly turned into a zero.</p></article>
            <article><MessagesSquare size={25} strokeWidth={1.2} aria-hidden="true" /><span className={styles.trustNumber}>03</span><h3>Every question has a why.</h3><p>Follow the evidence, the gaps, and the context behind each interview probe. Candidate code is inspected, never executed.</p></article>
          </div>
        </section>

        <section className={styles.closing} aria-labelledby="closing-title">
          <div className={styles.closingOrbit} aria-hidden="true"><span /><span /><span /></div>
          <p className={styles.sectionEyebrow}>LOOK CLOSER. ASK BETTER.</p>
          <h2 id="closing-title">Meet the capability<br /><span>behind the claim.</span></h2>
          <AnalyzeLink targetHref="/analyze" className={styles.primaryAction}>Begin your first analysis <span><ArrowRight size={17} aria-hidden="true" /></span></AnalyzeLink>
          <p className={styles.closingNote}>Bring a résumé. Start a more informed conversation.</p>
        </section>
      </main>
      <footer className={styles.footer}>
        <div className={styles.footerMain}>
          <div className={styles.footerIdentity}>
            <Link href="/" className={styles.footerBrand} scroll={true}>Candidate<span>X</span></Link>
            <p>Research-informed intelligence.<br />Human-led decisions.</p>
          </div>
          <nav className={styles.footerColumn} aria-label="Product">
            <h2>Product</h2>
            <AnalyzeLink targetHref="/analyze">Live Evidence</AnalyzeLink>
            <Link href="/research-demo" scroll={true}>Research Demo</Link>
          </nav>
          <nav className={styles.footerColumn} aria-label="Explore">
            <h2>Explore</h2>
            <Link href="#loop-title">The Evidence Loop</Link>
            <Link href="#trust-title">Our Principles</Link>
          </nav>
          <div className={styles.footerColumn}>
            <h2>Project Credits</h2>
            <p><span>Under the Guidance of</span><strong>Dr. Debachudamani Prusti</strong></p>
            <p><span>Prepared by</span><strong>Ayush Roy &amp; Archi Srivastava</strong></p>
          </div>
        </div>
        <div className={styles.footerBottom}>
          <p className={styles.footerCompany}><span>COMPANY</span><strong>Yor Ayrin - iwnl Private Limited.</strong></p>
          <span>WITH EVIDENCE. WITH CARE.</span>
        </div>
      </footer>
    </div>
  );
}
