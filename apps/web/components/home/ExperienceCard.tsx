import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type ExperienceCardProps = {
  title: string;
  eyebrow: string;
  description: string;
  href: string;
  icon: LucideIcon;
  accent: 'violet' | 'cyan' | 'lime' | 'amber';
  tag: string;
  featured?: boolean;
};

export function ExperienceCard({
  title,
  eyebrow,
  description,
  href,
  icon: Icon,
  accent,
  tag,
  featured = false,
}: ExperienceCardProps) {
  return (
    <Link
      href={href}
      className={`experience-card experience-card--${accent}${featured ? ' experience-card--featured' : ''}`}
    >
      <div className="experience-card__topline">
        <span className="experience-card__icon" aria-hidden="true"><Icon size={19} /></span>
        <span className="experience-card__tag">{tag}</span>
      </div>
      <div className="experience-card__body">
        <span className="experience-card__eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <span className="experience-card__link">
        Open surface <ArrowUpRight size={16} aria-hidden="true" />
      </span>
    </Link>
  );
}
