'use client';

import { useState, type KeyboardEvent } from 'react';
import { ArrowRight, ArrowUpRight, Braces, Check, FileText, GitBranch, MessageSquare, Quote } from 'lucide-react';
import Link from 'next/link';
import { AnalyzeLink } from '../navigation/AnalyzeLink';
import styles from './walkthrough.module.css';

const STEPS = [
  { label: 'Start with the claim', text: 'A résumé opens the story. It gives you something specific to explore.', icon: FileText },
  { label: 'Look at the work', text: 'Trace the statement to an artifact. See what it supports and what it leaves open.', icon: Braces },
  { label: 'Ask a better question', text: 'Take the open question into the interview. Give the candidate room to explain.', icon: MessageSquare },
];
const CODE = [
  'export async function requestWithRetry(task) {',
  '  for (let attempt = 0; attempt < 3; attempt++) {',
  '    try {',
  '      return await task();',
  '    } catch (error) {',
  '      if (attempt === 2) throw error;',
  '      await delay(250 * 2 ** attempt);',
  '    }',
  '  }',
  '}',
];

export function EvidenceWalkthrough() {
  const [active, setActive] = useState(0);
  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = (index + 1) % STEPS.length;
    else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = (index + STEPS.length - 1) % STEPS.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = STEPS.length - 1;
    else return;
    event.preventDefault();
    setActive(next);
    document.getElementById(`evidence-step-${next}`)?.focus();
  }

  return (
    <div className={styles.walkthrough}>
      <div className={styles.steps}>
        <div className={styles.tabList} role="tablist" aria-label="Follow an example claim" aria-orientation="vertical">
          {STEPS.map(({ label, text, icon: Icon }, index) => <button key={label} type="button" role="tab" id={`evidence-step-${index}`} aria-selected={active === index} aria-controls="evidence-example-panel" tabIndex={active === index ? 0 : -1} onClick={() => setActive(index)} onKeyDown={event => navigate(event, index)}><span className={styles.stepNumber}>0{index + 1}</span><span className={styles.stepCopy}><strong>{label}</strong><span>{text}</span></span><Icon size={17} strokeWidth={1.3} aria-hidden="true" /></button>)}
        </div>
        <AnalyzeLink targetHref="/analyze" className={styles.tryLink}>Follow your own evidence <ArrowUpRight size={14} aria-hidden="true" /></AnalyzeLink>
      </div>
      <div className={styles.example}>
        <div className={styles.exampleBar}><span className={styles.windowDots} aria-hidden="true"><i /><i /><i /></span><span>CANDIDATEX / EVIDENCE TRACE</span><span className={styles.exampleBadge}>Illustrative example</span></div>
        <div className={styles.trace} aria-hidden="true"><span data-active={active === 0}>CLAIM</span><i /><span data-active={active === 1}>ARTIFACT</span><i /><span data-active={active === 2}>QUESTION</span></div>
        <div className={styles.panel} role="tabpanel" id="evidence-example-panel" aria-labelledby={`evidence-step-${active}`} tabIndex={0}>
          <div key={active} className={styles.panelContent}>
            {active === 0 && <>
              <div className={styles.documentHeading}><span className={styles.documentIcon}><FileText size={19} strokeWidth={1.3} /></span><div><strong>Candidate résumé</strong><span>Experience / Backend engineering</span></div><span className={styles.sourceTag}>DECLARED</span></div>
              <div className={styles.claim}><Quote size={21} strokeWidth={1.1} aria-hidden="true" /><blockquote>Built a fault-tolerant<br /><span>payments API.</span></blockquote><div className={styles.claimUnderline} /><p>A compelling statement. A thread worth following.</p></div>
              <div className={styles.insight}><span className={styles.insightDot} /><div><strong>The claim tells us where to look.</strong><p>Explore the supplied repository for concrete examples of failure handling.</p></div></div>
            </>}
            {active === 1 && <>
              <div className={styles.documentHeading}><span className={styles.documentIcon}><GitBranch size={19} strokeWidth={1.3} /></span><div><strong>Supplied repository</strong><span>src / utils / retry.ts</span></div><span className={styles.sourceTag}>OBSERVED</span></div>
              <div className={styles.code} aria-label="Example retry function with three attempts and exponential backoff">{CODE.map((line, index) => <div key={index} data-highlight={index === 5 || index === 6}><span aria-hidden="true">{index + 12}</span><code>{line}</code></div>)}</div>
              <div className={styles.findings}><span><Check size={12} /> Retry handling observed</span><span><i /> Production behavior unknown</span></div>
            </>}
            {active === 2 && <>
              <div className={styles.documentHeading}><span className={styles.documentIcon}><MessageSquare size={19} strokeWidth={1.3} /></span><div><strong>Your interview brief</strong><span>Reliability / A question grounded in evidence</span></div><span className={styles.sourceTag}>EXPLORE</span></div>
              <div className={styles.question}><span>01 / OPEN THE CONVERSATION</span><blockquote>What happens when a payment succeeds, but the response times out?</blockquote><div className={styles.questionTags}><span>Failure modes</span><span>Tradeoffs</span><span>Ownership</span></div></div>
              <div className={styles.insight}><span className={styles.insightDot} /><div><strong>Why this question?</strong><p>The artifact shows retries. Ask how the candidate would prevent a duplicate payment.</p></div></div>
            </>}
          </div>
        </div>
        <div className={styles.exampleFooter}><span>One connected thread. Every step traceable.</span><button type="button" onClick={() => setActive((active + 1) % STEPS.length)} aria-label={active === 2 ? 'Restart example' : 'Next example step'}>{active === 2 ? 'Explore again' : 'Follow the thread'}<ArrowRight size={13} aria-hidden="true" /></button></div>
      </div>
    </div>
  );
}
