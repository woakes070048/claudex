import { forwardRef, type SelectHTMLAttributes } from 'react';
import { cn } from '@/utils/cn';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, hasError = false, disabled, children, ...props },
  ref,
) {
  return (
    <div className="relative inline-flex w-full">
      <select
        ref={ref}
        className={cn(
          'flex h-10 w-full appearance-none rounded-lg border border-border bg-surface-tertiary px-3 pr-9 text-sm text-text-primary transition-colors focus-visible:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 disabled:cursor-not-allowed disabled:bg-surface-secondary disabled:opacity-60 dark:border-border-dark dark:bg-surface-dark-tertiary dark:text-text-dark-primary dark:disabled:bg-surface-dark-tertiary',
          hasError &&
            'border-error-500 text-error-700 focus-visible:border-error-500 focus-visible:ring-error-500/40 dark:text-error-200',
          className,
        )}
        disabled={disabled}
        {...props}
      >
        {children}
      </select>
      <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-text-tertiary dark:text-text-dark-tertiary">
        <svg
          aria-hidden="true"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          viewBox="0 0 24 24"
        >
          <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </div>
  );
});

Select.displayName = 'Select';
