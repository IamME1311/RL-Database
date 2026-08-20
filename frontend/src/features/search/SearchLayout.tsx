import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Globe } from 'lucide-react';
import { SCOPES, SCOPE_LABELS } from '@/lib/enums';
import { cn } from '@/lib/utils';
import { Omnibox } from './Omnibox';

/**
 * Shell for every search view. The omnibox lives here rather than inside each
 * scope so the query text survives a tab switch — the whole point of "search
 * globally, or narrow to one aspect" is that you keep the term and change lens.
 */
export function SearchLayout() {
  const location = useLocation();
  // Carry the current params across tabs; each scope reads only the ones it owns.
  const search = location.search;

  return (
    <div className="space-y-4">
      <Omnibox />

      <nav className="flex flex-wrap items-center gap-1 border-b border-border pb-px">
        <ScopeTab to={{ pathname: '/search', search }} end>
          <Globe className="size-3.5" />
          Everything
        </ScopeTab>
        {SCOPES.map((scope) => (
          <ScopeTab key={scope} to={{ pathname: `/search/${scope}`, search }}>
            {SCOPE_LABELS[scope]}
          </ScopeTab>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}

function ScopeTab({
  to,
  end,
  children,
}: {
  to: { pathname: string; search: string };
  end?: boolean;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'relative inline-flex items-center gap-1.5 rounded-t-md px-3 py-2 text-sm font-medium transition-colors',
          'after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:rounded-full',
          isActive
            ? 'text-foreground after:bg-primary'
            : 'text-muted-foreground hover:text-foreground after:bg-transparent',
        )
      }
    >
      {children}
    </NavLink>
  );
}
