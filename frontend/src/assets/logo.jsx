import React from 'react';

export const Logo = ({ className = "h-10", variant = "full" }) => {
  if (variant === "icon") {
    return (
      <svg className={className} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 4L36 12V28L20 36L4 28V12L20 4Z" stroke="white" strokeWidth="2" fill="none"/>
        <path d="M20 8L30 13V27L20 32L10 27V13L20 8Z" stroke="white" strokeWidth="1.5" fill="none"/>
        <text x="20" y="24" textAnchor="middle" fill="white" fontFamily="Orbitron" fontSize="10" fontWeight="bold">SG</text>
      </svg>
    );
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg className="h-10 w-10" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Hexagon Badge */}
        <path 
          d="M24 2L44 14V34L24 46L4 34V14L24 2Z" 
          stroke="white" 
          strokeWidth="2"
          className="drop-shadow-[0_0_8px_rgba(255,255,255,0.3)]"
        />
        <path 
          d="M24 8L38 16V32L24 40L10 32V16L24 8Z" 
          stroke="white" 
          strokeWidth="1"
          opacity="0.5"
        />
        {/* S.G Typography */}
        <text 
          x="24" 
          y="29" 
          textAnchor="middle" 
          fill="white" 
          fontFamily="'Orbitron', sans-serif" 
          fontSize="14" 
          fontWeight="700"
          className="tracking-wider"
        >
          SG
        </text>
      </svg>
      
      <div className="flex flex-col">
        <span 
          className="text-xl font-bold tracking-[0.2em] leading-none"
          style={{ fontFamily: "'Orbitron', 'Rajdhani', sans-serif" }}
        >
          STRATOS
        </span>
        <span 
          className="text-xs tracking-[0.35em] leading-none text-gray-400"
          style={{ fontFamily: "'Rajdhani', sans-serif" }}
        >
          GARAGE
        </span>
      </div>
    </div>
  );
};

export default Logo;
