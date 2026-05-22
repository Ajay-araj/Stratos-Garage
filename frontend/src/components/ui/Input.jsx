import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const Input = React.forwardRef(({ className, label, error, ...props }, ref) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-heading tracking-wider uppercase text-gray-300 mb-2">
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={twMerge(
          clsx(
            "w-full bg-stratos-graphite border border-white/20 rounded-md px-4 py-2.5 text-white placeholder-gray-500",
            "focus:outline-none focus:border-white/50 focus:ring-1 focus:ring-white/50 transition-colors duration-200",
            error && "border-red-500 focus:border-red-500 focus:ring-red-500/50",
            className
          )
        )}
        {...props}
      />
      {error && (
        <p className="mt-1.5 text-sm text-red-500 font-body">{error}</p>
      )}
    </div>
  );
});

Input.displayName = 'Input';
export default Input;
