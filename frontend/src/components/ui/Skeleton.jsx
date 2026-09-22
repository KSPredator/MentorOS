import React from 'react';

/** Shimmer skeleton block. Pass `className` for sizing. */
export function Skeleton({ className = '' }) {
  return <div className={`skeleton rounded-xl ${className}`} aria-hidden />;
}

export function SkeletonThread() {
  return (
    <div className="space-y-6 p-8 max-w-3xl mx-auto w-full" aria-hidden>
      <div className="flex justify-end">
        <Skeleton className="h-14 w-[55%] rounded-2xl" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/5" />
          <Skeleton className="h-24 w-full mt-3" />
        </div>
      </div>
      <div className="flex justify-end">
        <Skeleton className="h-12 w-[40%] rounded-2xl" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonRows({ count = 4, className = '' }) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

export function SkeletonCards({ count = 4 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-28 w-full" />
      ))}
    </div>
  );
}
