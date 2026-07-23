import React, { ButtonHTMLAttributes } from 'react';
import { cn } from '../../utils/helpers';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'gold';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, leftIcon, rightIcon, fullWidth, children, disabled, ...props }, ref) => {
    
    const variants = {
      primary: "bg-gradient-to-r from-primary-blue to-secondary-blue text-white hover:scale-[1.02] shadow-lg shadow-primary-blue/20",
      secondary: "bg-dark-card border border-dark-border text-text-primary hover:bg-dark-border",
      ghost: "bg-transparent text-text-secondary hover:text-text-primary hover:bg-white/5",
      danger: "bg-status-error/10 text-status-error hover:bg-status-error/20 border border-status-error/20",
      gold: "bg-gradient-to-r from-gold-accent to-gold-light text-dark-bg font-semibold hover:scale-[1.02] shadow-lg shadow-gold-accent/20"
    };

    const sizes = {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2 text-sm",
      lg: "px-6 py-3 text-base"
    };

    return (
      <button
        ref={ref}
        disabled={loading || disabled}
        className={cn(
          "inline-flex items-center justify-center rounded-md font-medium transition-all duration-200",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
          variants[variant],
          sizes[size],
          fullWidth && "w-full",
          className
        )}
        {...props}
      >
        {loading && (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        )}
        {!loading && leftIcon && <span className="mr-2">{leftIcon}</span>}
        {children}
        {!loading && rightIcon && <span className="ml-2">{rightIcon}</span>}
      </button>
    );
  }
);
Button.displayName = 'Button';
