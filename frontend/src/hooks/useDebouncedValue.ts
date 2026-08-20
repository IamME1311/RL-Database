import { useEffect, useState } from 'react';

/**
 * Keeps the input responsive while throttling what the query layer sees.
 *
 * The text field itself holds undebounced state, so typing never lags; only the
 * value that feeds the query key (and the URL) is delayed.
 */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
