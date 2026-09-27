import type { ReactNode } from 'react';
import styles from './studio.module.css';

export function StudioHeading({ eyebrow, title, description, children }: { eyebrow: string; title: ReactNode; description: string; children?: ReactNode }) {
  return <div className={styles.heading}>
    <div><p className={styles.eyebrow}><span />{eyebrow}</p><h1>{title}</h1><p className={styles.description}>{description}</p></div>
    {children && <div className={styles.headingActions}>{children}</div>}
  </div>;
}
