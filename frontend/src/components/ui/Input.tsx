import React, { InputHTMLAttributes } from 'react';
import { cn } from '../../utils/helpers';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, rightIcon, ...props }, ref) => {
    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label className="text-sm font-medium text-text-primary">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            className={cn(
              "w-full bg-white border border-dark-border rounded-lg px-3.5 py-2 text-sm text-text-primary placeholder:text-text-muted",
              "focus:outline-none focus:border-secondary-blue focus:ring-2 focus:ring-secondary-blue/15 transition-all shadow-sm",
              "disabled:opacity-50 disabled:bg-slate-50 disabled:cursor-not-allowed",
              error && "border-status-error focus:border-status-error focus:ring-status-error/15 animate-shake",
              rightIcon && "pr-10",
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary">
              {rightIcon}
            </div>
          )}
        </div>
        {error && <span className="text-xs text-status-error">{error}</span>}
      </div>
    );
  }
);
Input.displayName = 'Input';
