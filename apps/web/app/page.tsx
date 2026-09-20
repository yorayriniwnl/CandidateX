import { ArrowRight, BrainCircuit, FlaskConical, SearchCheck, UsersRound } from 'lucide-react';
import Link from 'next/link';
import { ExperienceCard } from '../components/home/ExperienceCard';
import { SignalConstellation } from '../components/home/SignalConstellation';
import { PlatformHeader } from '../components/navigation/PlatformHeader';
import styles from './home.module.css';

const EXPERIENCES = [
  {
    title: 'Live Evidence',
    eyebrow: 'For a real candidate',
    description: 'Upload a resume, review supplied public links, and follow the evidence into a focused technical interview.',
    href: '/analyze',
    icon: SearchCheck,
    accent: 'violet' as const,
    tag: 'Primary workflow',
    featured: true,
  },
  {
    title: 'Evaluation Workspace',
    eyebrow: 'For deep review',
    description: 'Browse candidate cohorts, run evaluations, inspect dossiers, compare profiles, and explore the methodology.',
    href: '/workspace',
    icon: BrainCircuit,
    accent: 'cyan' as const,
    tag: 'Operations',
  },
  {
    title: 'Hiring View',
    eyebrow: 'For fast triage',
    description: 'A lighter review surface for hiring teams to scan candidate status, interviews, and evidence alerts.',
    href: '/hr',
    icon: UsersRound,
    accent: 'lime' as const,
    tag: 'Sample surface',
  },
  {
    title: 'Research Lab',
    eyebrow: 'For understanding the math',
    description: 'Change synthetic evidence conditions and see how capability, coverage, contradictions, and probes move together.',
    href: '/research-demo',
    icon: FlaskConical,
    accent: 'amber' as const,
    tag: 'Synthetic only',
  },
];

export default function HomePage() {
  return (
    <div className={styles.home}>
      <PlatformHeader surface="home" />
      <main className={styles.homeMain}>
        <section className={styles.hero} aria-labelledby="home-title">
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Candidate capability intelligence / v1</p>
            <h1 id="home-title">
              Candidate intelligence,
              <span>with receipts.</span>
            </h1>
            <p className={styles.heroDescription}>
              Trace technical claims through public evidence, capability signals, and the questions that make a human interview sharper. CandidateX supports hiring judgment; it never makes the decision for you.
            </p>
            <div className={styles.heroActions}>
              <Link href="/analyze" className={styles.primaryAction}>
                Start with live evidence <ArrowRight size={17} aria-hidden="true" />
              </Link>
              <Link href="/research-demo" className={styles.secondaryAction}>
                Explore the method <ArrowUpRightIcon />
              </Link>
            </div>
            <div className={styles.heroMeta} aria-label="Product principles">
              <span className={styles.heroMetaItem}><strong>12</strong> capabilities</span>
              <span className={styles.heroMetaItem}><strong>6</strong> role lenses</span>
              <span className={styles.heroMetaItem}><strong>0</strong> autonomous decisions</span>
            </div>
          </div>
          <div className={styles.heroVisual}>
            <SignalConstellation />
            <p className={styles.visualCaption}>Claims → evidence → capability → interview</p>
          </div>
        </section>

        <section className={styles.modesSection} aria-labelledby="modes-title">
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.sectionEyebrow}>Choose your surface</p>
              <h2 id="modes-title">Four ways in.</h2>
            </div>
            <p>Same signal system. Different depth, audience, and evidence boundary.</p>
          </div>
          <div className={styles.experienceGrid} aria-label="CandidateX product surfaces">
            {EXPERIENCES.map((experience) => <ExperienceCard key={experience.href} {...experience} />)}
          </div>
        </section>

        <section className={styles.loopSection} aria-labelledby="loop-title">
          <p className={styles.sectionEyebrow}>The operating loop</p>
          <div className={styles.sectionHeading}>
            <h2 id="loop-title">Make the conversation count.</h2>
            <p>Move from a declaration to an interview you can defend.</p>
          </div>
          <div className={styles.loopGrid}>
            <LoopItem number="01" title="Bring context" description="Start with the resume, role, and sources the candidate actually supplied." />
            <LoopItem number="02" title="Trace the signal" description="Inspect artifacts, confidence, coverage, conflicts, and what remains unknown." />
            <LoopItem number="03" title="Prepare the conversation" description="Turn uncertainty into evidence-linked questions for a human interviewer." />
          </div>
        </section>

        <section className={styles.trustStrip} aria-label="CandidateX guardrails">
          <div className={styles.trustItem}><strong>Human decision support</strong><span>Evidence and probes help an interviewer reason. The system does not rank people autonomously.</span></div>
          <div className={styles.trustItem}><strong>Missing stays unknown</strong><span>Unobserved capability is not silently turned into a zero or a false negative.</span></div>
          <div className={styles.trustItem}><strong>Static analysis only</strong><span>Candidate code is inspected without executing untrusted repositories or test suites.</span></div>
        </section>

        <footer className={styles.footer}>
          <span>CandidateX · Research-informed technical interview preparation.</span>
          <nav className={styles.footerNav} aria-label="Footer navigation">
            <Link href="/analyze">Live Evidence</Link>
            <Link href="/workspace">Workspace</Link>
            <Link href="/research-demo">Research Lab</Link>
          </nav>
        </footer>
      </main>
    </div>
  );
}

function LoopItem({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <article className={styles.loopItem}>
      <span className={styles.loopNumber}>{number}</span>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  );
}

function ArrowUpRightIcon() {
  return <ArrowRight size={17} aria-hidden="true" />;
}
