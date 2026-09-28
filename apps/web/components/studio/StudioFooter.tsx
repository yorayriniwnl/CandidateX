import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { AnalyzeLink } from '../navigation/AnalyzeLink';
import styles from './studio.module.css';

export function StudioFooter() {
  return <footer className={styles.footer}><Link href="/" scroll={true}>Candidate<span>X</span></Link><p>Evidence informs. People decide.</p><AnalyzeLink targetHref="/analyze">Start with evidence <ArrowUpRight size={12} aria-hidden="true" /></AnalyzeLink></footer>;
}
