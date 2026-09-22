import React, { lazy, Suspense } from 'react';

const BookScene = lazy(() => import('./BookScene'));

/**
 * Lazy boundary for the 3D hero centerpiece. Imported on demand from
 * EmptyHero so the WebGL bundle never blocks first paint.
 */
export default function HeroScene() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-xl h-56 mb-3 rounded-3xl skeleton" aria-hidden />
      }
    >
      <BookScene />
    </Suspense>
  );
}