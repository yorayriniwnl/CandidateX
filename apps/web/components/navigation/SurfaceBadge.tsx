import { STATUS_COPY, type SurfaceStatus } from './navigation';

type SurfaceBadgeProps = {
  status: SurfaceStatus;
};

export function SurfaceBadge({ status }: SurfaceBadgeProps) {
  const copy = STATUS_COPY[status];

  return (
    <span
      className={`surface-badge surface-badge--${status}`}
      title={copy.detail}
      aria-label={`${copy.label}: ${copy.detail}`}
    >
      <span className="surface-badge__dot" aria-hidden="true" />
      {copy.label}
    </span>
  );
}
