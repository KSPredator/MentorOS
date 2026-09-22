import React, { useId } from 'react';

/** Compact MentorOS mark: an open book whose center fold rises into a spark. */
export function LogoMark({ size = 32, className = '' }) {
  const gradientId = `mentoros-mark-${useId().replaceAll(':', '')}`;
  return (
    <span
      className={`inline-flex flex-shrink-0 items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label="MentorOS"
    >
      <svg
        viewBox="0 0 48 48"
        width={size}
        height={size}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradientId} x1="8" y1="8" x2="40" y2="42" gradientUnits="userSpaceOnUse">
            <stop stopColor="#38BDF8" />
            <stop offset="1" stopColor="#4F46E5" />
          </linearGradient>
        </defs>
        <path
          d="M8 17.5C15.2 14.7 20.9 16.2 24 20.1C27.1 16.2 32.8 14.7 40 17.5V36.2C33.4 33.9 28.1 35.1 24 39C19.9 35.1 14.6 33.9 8 36.2V17.5Z"
          fill={`url(#${gradientId})`}
          fillOpacity=".12"
          stroke={`url(#${gradientId})`}
          strokeWidth="2.4"
          strokeLinejoin="round"
        />
        <path d="M12.5 21.5C17.1 20.2 20.3 21.1 24 24.2V34.7C20.4 32.4 17.1 31.9 12.5 33.1V21.5Z" fill={`url(#${gradientId})`} fillOpacity=".2" />
        <path d="M35.5 21.5C30.9 20.2 27.7 21.1 24 24.2V34.7C27.6 32.4 30.9 31.9 35.5 33.1V21.5Z" fill={`url(#${gradientId})`} fillOpacity=".13" />
        <path d="M24 34V18.5" stroke={`url(#${gradientId})`} strokeWidth="2.4" strokeLinecap="round" />
        <path d="M24 6.5C24.8 10.5 26.4 12.1 30.5 13C26.4 13.8 24.8 15.4 24 19.5C23.2 15.4 21.6 13.8 17.5 13C21.6 12.1 23.2 10.5 24 6.5Z" fill={`url(#${gradientId})`} />
      </svg>
    </span>
  );
}

/** Shared icon + wordmark lockup used by the app navigation. */
export default function Logo({ size = 'md', showText = true, className = '' }) {
  const dimensions = { sm: 26, md: 32, lg: 42, xl: 54 };
  const iconSize = dimensions[size] || dimensions.md;

  return (
    <span className={`inline-flex items-center gap-2.5 select-none ${className}`} aria-label={showText ? undefined : 'MentorOS'}>
      <LogoMark size={iconSize} />
      {showText && (
        <span className="font-display font-extrabold leading-none tracking-tight text-[15px]">
          <span className="text-textMain">Mentor</span>
          <span className="ml-0.5 bg-gradient-to-r from-accent to-indigo-500 bg-clip-text text-transparent">OS</span>
        </span>
      )}
    </span>
  );
}
