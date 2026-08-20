import { useEffect, useRef, useState } from 'react';

/**
 * Live countdown for a rate-limit cooldown.
 *
 * Pass the seconds from a 429's `Retry-After` (see `parseRetryAfter`) and this ticks
 * down to zero so the button can say "try again in 45s" instead of leaving a dead
 * error on screen with no indication of when it clears.
 *
 * Counts against a wall-clock deadline rather than decrementing a counter, so a
 * backgrounded tab (where timers get throttled) resumes with the correct remaining
 * time instead of a stale one.
 */
export function useCooldown(seconds: number | null | undefined) {
  const [remaining, setRemaining] = useState(0);
  const deadlineRef = useRef<number | null>(null);

  useEffect(() => {
    if (!seconds || seconds <= 0) {
      deadlineRef.current = null;
      setRemaining(0);
      return;
    }

    deadlineRef.current = Date.now() + seconds * 1000;
    setRemaining(seconds);

    const tick = () => {
      if (deadlineRef.current === null) return;
      const left = Math.ceil((deadlineRef.current - Date.now()) / 1000);
      setRemaining(left > 0 ? left : 0);
    };

    const timer = setInterval(tick, 500);
    return () => clearInterval(timer);
  }, [seconds]);

  return { remaining, isCoolingDown: remaining > 0 };
}
