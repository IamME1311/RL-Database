import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useUrlSearchState } from '@/hooks/useUrlSearchState';
import { SCOPE_LABELS } from '@/lib/enums';
import { cn } from '@/lib/utils';
import { MIN_GLOBAL_QUERY_LENGTH, detailPath, useSuggestions } from './queries';

/**
 * The one search box, shared by the global view and every scoped tab.
 *
 * Typing writes to local state immediately so the field never lags, and a 250ms
 * debounce pushes the value into the URL. The URL write uses `replace` so a long
 * query doesn't leave one history entry per character.
 */
export function Omnibox({ placeholder }: { placeholder?: string }) {
  const url = useUrlSearchState();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const urlQuery = url.getString('q');
  const [text, setText] = useState(urlQuery);
  const debounced = useDebouncedValue(text, 250);

  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);

  // Keep in step when the URL changes from elsewhere (back button, a reset, a
  // link into a pre-filtered search) without stomping on active typing.
  useEffect(() => {
    setText((current) => (current === urlQuery ? current : urlQuery));
  }, [urlQuery]);

  // The debounced value is what the rest of the app reacts to. resetPage matters:
  // being left on page 7 of a new, shorter result set looks like a bug.
  useEffect(() => {
    if (debounced === urlQuery) return;
    url.setParams({ q: debounced || null }, { replace: true, resetPage: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  const suggestQuery = useSuggestions(debounced, open);
  const suggestions = suggestQuery.data?.suggestions ?? [];

  useEffect(() => setHighlighted(-1), [suggestions.length, debounced]);

  /** ⌘K / Ctrl-K from anywhere focuses the box — this is the app's main verb. */
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener('pointerdown', onPointerDown);
    return () => window.removeEventListener('pointerdown', onPointerDown);
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (event.key === 'ArrowDown' && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setHighlighted((i) => (i + 1) % suggestions.length);
      return;
    }
    if (event.key === 'ArrowUp' && suggestions.length) {
      event.preventDefault();
      setHighlighted((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
      return;
    }
    if (event.key === 'Enter') {
      // Enter on a highlighted suggestion jumps straight to that record; Enter on
      // free text just commits the query (which the debounce has usually done).
      if (highlighted >= 0 && suggestions[highlighted]) {
        const hit = suggestions[highlighted];
        setOpen(false);
        navigate(detailPath(hit.type, hit.id));
        return;
      }
      url.setParams({ q: text || null }, { replace: true, resetPage: true });
      setOpen(false);
    }
  };

  const clear = () => {
    setText('');
    url.setParams({ q: null }, { replace: true, resetPage: true });
    inputRef.current?.focus();
  };

  const showDropdown =
    open && debounced.trim().length >= MIN_GLOBAL_QUERY_LENGTH && suggestions.length > 0;

  return (
    <div ref={containerRef} className="relative w-full">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        ref={inputRef}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? 'Search creators, brands, campaigns, pitches…'}
        className="h-10 pl-9 pr-20"
        role="combobox"
        aria-expanded={showDropdown}
        aria-controls="omnibox-suggestions"
        aria-autocomplete="list"
      />

      <div className="absolute right-2.5 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
        {suggestQuery.isFetching && <Loader2 className="size-3.5 animate-spin text-muted-foreground" />}
        {text ? (
          <button
            type="button"
            onClick={clear}
            className="rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="size-4" />
          </button>
        ) : (
          <kbd className="hidden select-none rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline-block">
            ⌘K
          </kbd>
        )}
      </div>

      {showDropdown && (
        <ul
          id="omnibox-suggestions"
          role="listbox"
          className="absolute z-50 mt-1.5 w-full overflow-hidden rounded-lg border border-border bg-popover p-1 shadow-lg"
        >
          {suggestions.map((hit, index) => (
            <li key={`${hit.type}-${hit.id}`} role="option" aria-selected={index === highlighted}>
              <button
                type="button"
                onMouseEnter={() => setHighlighted(index)}
                onClick={() => {
                  setOpen(false);
                  navigate(detailPath(hit.type, hit.id));
                }}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors',
                  index === highlighted ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60',
                )}
              >
                <Badge variant="outline" className="shrink-0">
                  {SCOPE_LABELS[hit.type]}
                </Badge>
                <span className="min-w-0 flex-1 truncate text-sm">{hit.label}</span>
                {hit.sublabel && (
                  <span className="shrink-0 truncate text-[11px] text-muted-foreground">
                    {hit.sublabel}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
