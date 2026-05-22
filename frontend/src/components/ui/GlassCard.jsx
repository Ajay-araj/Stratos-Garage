import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const GlassCard = React.forwardRef(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={twMerge(
        clsx(
          "bg-stratos-dark/60 backdrop-blur-md border border-white/10 shadow-glass rounded-xl overflow-hidden",
          className
        )
      )}
      {...props}
    >
      {children}
    </div>
  );
});

GlassCard.displayName = 'GlassCard';
export default GlassCard;
