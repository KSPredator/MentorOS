/**
 * Shared framer-motion variants — single source of motion language.
 * Keep durations tight (0.2–0.4s); this is a tool, not a slideshow.
 */

export const easeOut = [0.22, 1, 0.36, 1];

export const fadeInUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35, ease: easeOut },
};

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.25, ease: easeOut },
};

export const scaleIn = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0 },
  transition: { duration: 0.28, ease: easeOut },
};

export const stagger = {
  initial: {},
  animate: { transition: { staggerChildren: 0.06 } },
};

export const staggerItem = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: easeOut } },
};

export const routeTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
  transition: { duration: 0.2, ease: easeOut },
};

export const hoverTap = {
  whileHover: { scale: 1.02 },
  whileTap: { scale: 0.97 },
};

export const listItem = {
  initial: { opacity: 0, x: -8 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.25, ease: easeOut } },
  exit: { opacity: 0, x: 8, transition: { duration: 0.15 } },
};

export const popCenter = {
  initial: { opacity: 0, scale: 0.94 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.96 },
  transition: { duration: 0.2, ease: easeOut },
};
