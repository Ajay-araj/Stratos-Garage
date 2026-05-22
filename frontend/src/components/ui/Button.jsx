import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const Button = React.forwardRef(({ 
  className, 
  variant = 'primary', 
  size = 'md', 
  isLoading, 
  children, 
  ...props 
}, ref) => {
  const baseStyles = "inline-flex items-center justify-center font-heading tracking-widest uppercase transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-white text-black hover:bg-gray-200 hover:shadow-neon active:scale-95",
    outline: "border border-white/30 text-white hover:border-white hover:bg-white/5 active:scale-95",
    ghost: "text-white hover:bg-white/10 active:scale-95",
    danger: "bg-red-600 text-white hover:bg-red-700 hover:shadow-[0_0_15px_rgba(220,38,38,0.5)] active:scale-95"
  };

  const sizes = {
    sm: "px-4 py-1.5 text-xs font-semibold",
    md: "px-6 py-2.5 text-sm font-bold",
    lg: "px-8 py-3.5 text-base font-bold",
    icon: "p-2"
  };

  return (
    <button
      ref={ref}
      disabled={isLoading || props.disabled}
      className={twMerge(clsx(baseStyles, variants[variant], sizes[size], className))}
      {...props}
    >
      {isLoading ? (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      ) : null}
      {children}
    </button>
  );
});

Button.displayName = 'Button';
export default Button;
