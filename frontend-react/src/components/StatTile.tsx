import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function StatTile({
  label,
  value,
  hint,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('rounded-lg border border-border bg-card px-3 py-2.5', className)}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tnum">{value}</p>
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

/**
 * `cols` sets the widest breakpoint's column count so a row of five tiles doesn't
 * wrap one tile onto a lonely second line.
 */
export function StatRow({
  children,
  cols = 4,
  className,
}: {
  children: ReactNode;
  cols?: 4 | 5;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-2 sm:grid-cols-3',
        cols === 5 ? 'lg:grid-cols-5' : 'lg:grid-cols-4',
        className,
      )}
    >
      {children}
    </div>
  );
}
