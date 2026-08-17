import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/DataTable';
import { Pagination } from '@/components/Pagination';
import { EmptyState, ErrorState } from '@/components/states';
import { USE_MOCKS } from '@/lib/api-client';
import { downloadCsv, toCsv } from '@/lib/csv';
import { useUrlSearchState } from '@/hooks/useUrlSearchState';
import { CREATOR_SORTS, SCOPE_FILTER_KEYS, countActiveFilters, useCreatorRequest } from '../request-state';
import { ResultsHeader } from '../ResultsHeader';
import { useCreatorFacets, useCreatorSearch } from '../queries';
import { CreatorFilters } from './CreatorFilters';
import { creatorColumns } from './columns';

const CSV_COLUMNS = [
  { key: 'name' as const, header: 'Name' },
  { key: 'username' as const, header: 'Handle' },
  { key: 'platform' as const, header: 'Platform' },
  { key: 'tier' as const, header: 'Tier' },
  { key: 'followers' as const, header: 'Followers' },
  { key: 'avg_views' as const, header: 'Avg views' },
  { key: 'city' as const, header: 'City' },
  { key: 'gender' as const, header: 'Gender' },
  { key: 'categories_raw' as const, header: 'Categories' },
  { key: 'languages_raw' as const, header: 'Languages' },
  { key: 'email' as const, header: 'Email' },
  { key: 'phone' as const, header: 'Phone' },
];

export function CreatorSearchPage() {
  const url = useUrlSearchState();
  const navigate = useNavigate();
  const request = useCreatorRequest();
  const [filtersOpen, setFiltersOpen] = useState(false);

  const facetsQuery = useCreatorFacets();
  const searchQuery = useCreatorSearch(request);

  const result = searchQuery.data;
  const activeFilterCount = countActiveFilters(request);

  const resetFilters = () => {
    url.setParams(
      Object.fromEntries(SCOPE_FILTER_KEYS.creators.map((key) => [key, null])),
      { replace: false, resetPage: true },
    );
  };

  const exportCsv = () => {
    if (!result?.rows.length) return;
    downloadCsv(`creators_page_${result.page}.csv`, toCsv(result.rows, CSV_COLUMNS));
  };

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <CreatorFilters
        facets={facetsQuery.data}
        request={request}
        isLoading={facetsQuery.isPending}
        open={filtersOpen}
      />

      <div className="min-w-0 flex-1 space-y-3">
        <ResultsHeader
          total={result?.total}
          tookMs={result?.took_ms}
          isFetching={searchQuery.isFetching}
          entityLabel="creator"
          sort={request.sort}
          sortOptions={CREATOR_SORTS}
          onSortChange={(sort) => url.setParams({ sort }, { replace: true, resetPage: true })}
          activeFilterCount={activeFilterCount}
          onResetFilters={resetFilters}
          onToggleFilters={() => setFiltersOpen((open) => !open)}
        />

        {searchQuery.isError ? (
          <ErrorState error={searchQuery.error} onRetry={() => searchQuery.refetch()} />
        ) : (
          <>
            <DataTable
              columns={creatorColumns}
              rows={result?.rows ?? []}
              rowKey={(row) => row.id}
              onRowClick={(row) => navigate(`/creators/${row.id}`)}
              isLoading={searchQuery.isPending}
              isFetching={searchQuery.isFetching && !searchQuery.isPending}
              emptyState={<CreatorEmptyState hasQuery={Boolean(request.text) || activeFilterCount > 0} />}
            />

            <div className="flex flex-wrap items-center justify-between gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={exportCsv}
                disabled={!result?.rows.length}
              >
                <Download />
                Export page as CSV
              </Button>

              <Pagination
                page={result?.page ?? 1}
                pages={result?.pages ?? 1}
                pageSize={request.page_size}
                total={result?.total ?? 0}
                disabled={searchQuery.isFetching}
                onPageChange={(page) => url.setParams({ page }, { replace: false })}
                onPageSizeChange={(size) => url.setParams({ size }, { replace: true, resetPage: true })}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * When creator search comes back empty with no filters applied, the likely cause
 * isn't the query — it's that nothing has ever populated the table. The
 * pitch_creator / campaign_creator ingest types are declared in the backend's
 * IngestType enum but have no client, parser or ingest method, so `creator` has no
 * data source at all. Saying so beats a bare "no results" that reads as a bug.
 */
function CreatorEmptyState({ hasQuery }: { hasQuery: boolean }) {
  if (hasQuery) {
    return (
      <EmptyState
        icon={<Users className="size-7" />}
        title="No creators match"
        description="Try fewer filters, or a shorter search term. Text search covers name, handle, categories, languages and city."
      />
    );
  }

  return (
    <EmptyState
      icon={<Users className="size-7" />}
      title="No creators in the database yet"
      description={
        USE_MOCKS ? (
          'Fixture data should have loaded here — check the mock handlers.'
        ) : (
          <>
            Creator rows arrive from the <code className="font-mono">pitch_creator</code> and{' '}
            <code className="font-mono">campaign_creator</code> ingest sources, which the backend
            declares but has not implemented yet. Until one of those runs, this table stays empty —
            see <code className="font-mono">PROPOSED_BACKEND_CHANGES.md</code>.
          </>
        )
      }
    />
  );
}
