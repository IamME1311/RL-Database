import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * URL search params as the single source of truth for search state.
 *
 * Everything the user picks — query text, scope, filters, sort, page — lives in
 * the URL, so a result set is shareable by copying the address bar, and browser
 * back/forward moves through search history the way people expect.
 */
export function useUrlSearchState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const getString = useCallback(
    (key: string, fallback = ''): string => searchParams.get(key) ?? fallback,
    [searchParams],
  );

  const getNumber = useCallback(
    (key: string, fallback: number | null = null): number | null => {
      const raw = searchParams.get(key);
      if (raw === null || raw === '') return fallback;
      const parsed = Number(raw);
      return Number.isFinite(parsed) ? parsed : fallback;
    },
    [searchParams],
  );

  const getBool = useCallback(
    (key: string): boolean => searchParams.get(key) === '1',
    [searchParams],
  );

  /** Repeated params (`?city=Mumbai&city=Pune`) rather than a delimiter, so values may contain commas. */
  const getList = useCallback(
    (key: string): string[] => searchParams.getAll(key).filter(Boolean),
    [searchParams],
  );

  /**
   * `replace` avoids a history entry per keystroke. Callers pass replace=false for
   * deliberate navigations (changing scope, paging) that should be undoable.
   */
  const setParams = useCallback(
    (
      updates: Record<string, string | number | boolean | null | undefined | string[] | number[]>,
      options: { replace?: boolean; resetPage?: boolean } = {},
    ) => {
      const { replace = true, resetPage = false } = options;
      setSearchParams(
        (previous) => {
          const next = new URLSearchParams(previous);
          for (const [key, value] of Object.entries(updates)) {
            next.delete(key);
            if (value === null || value === undefined || value === '' || value === false) continue;
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item !== null && item !== undefined && item !== '') next.append(key, String(item));
              }
              continue;
            }
            next.set(key, value === true ? '1' : String(value));
          }
          if (resetPage) next.delete('page');
          return next;
        },
        { replace },
      );
    },
    [setSearchParams],
  );

  const clearAllExcept = useCallback(
    (keep: string[]) => {
      setSearchParams(
        (previous) => {
          const next = new URLSearchParams();
          for (const key of keep) {
            for (const value of previous.getAll(key)) next.append(key, value);
          }
          return next;
        },
        { replace: false },
      );
    },
    [setSearchParams],
  );

  return useMemo(
    () => ({ searchParams, getString, getNumber, getBool, getList, setParams, clearAllExcept }),
    [searchParams, getString, getNumber, getBool, getList, setParams, clearAllExcept],
  );
}
