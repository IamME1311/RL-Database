import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * A styled native <select>. Deliberately native: these are short, single-choice
 * lists (sort order, page size) where the OS picker is faster and more accessible
 * than a custom popover. Multi-select facets use FacetMultiSelect instead.
 */
export const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<'select'>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          'h-9 w-full appearance-none rounded-md border border-input bg-card pl-3 pr-8 text-sm shadow-xs transition-colors',
          'focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 outline-none',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  ),
);
Select.displayName = 'Select';
