import * as React from 'react';
import { cn } from '@/lib/utils';

export const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<'input'>>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        'flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-sm shadow-xs transition-colors',
        'placeholder:text-muted-foreground/70',
        'focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 outline-none',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'file:mr-3 file:h-7 file:rounded file:border-0 file:bg-secondary file:px-2 file:text-xs file:font-medium file:text-secondary-foreground',
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = 'Input';
