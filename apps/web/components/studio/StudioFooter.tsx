import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import styles from './studio.module.css';

export function StudioFooter() {
  return <footer className={styles.footer}><Link href="/">Candidate<span>X</span></Link><p>Evidence informs. People decide.</p><Link href="/analyze">Start with evidence <ArrowUpRight size={12} aria-hidden="true" /></Link></footer>;
}
