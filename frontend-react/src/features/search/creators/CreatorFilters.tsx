import { FacetMultiSelect } from '@/components/FacetMultiSelect';
import { RangeFilter } from '@/components/RangeFilter';
import { Skeleton } from '@/components/ui/skeleton';
import { useUrlSearchState } from '@/hooks/useUrlSearchState';
import {
  PLATFORM_LABELS,
  TIER_HINTS,
  TIER_LABELS,
  fromWireTier,
  toWireTier,
} from '@/lib/enums';
import { formatNumber } from '@/lib/format';
import type { CreatorFacets, CreatorSearchRequest } from '@/types/api';
import { FilterCheckbox, FilterPanel, toOptions } from '../FilterPanel';

export function CreatorFilters({
  facets,
  request,
  isLoading,
  open,
}: {
  facets: CreatorFacets | undefined;
  request: CreatorSearchRequest;
  isLoading: boolean;
  open: boolean;
}) {
  const url = useUrlSearchState();
  const set = (updates: Parameters<typeof url.setParams>[0]) =>
    url.setParams(updates, { replace: true, resetPage: true });

  if (isLoading) {
    return (
      <FilterPanel open={open}>
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-9 w-full" />
          </div>
        ))}
      </FilterPanel>
    );
  }

  // Tier values round-trip through a sentinel because TierChoices.NA is "".
  const tierOptions = (facets?.tiers ?? []).map((tier) => ({
    value: fromWireTier(tier),
    label: TIER_LABELS[tier] ?? tier,
    hint: TIER_HINTS[tier],
  }));

  return (
    <FilterPanel
      open={open}
      footer={
        facets && (
          <p className="text-[11px] text-muted-foreground tnum">
            {formatNumber(facets.total_creators)} creators in the database
          </p>
        )
      }
    >
      <FacetMultiSelect
        label="Platform"
        options={toOptions(facets?.platforms, PLATFORM_LABELS)}
        selected={request.platforms}
        onChange={(values) => set({ platform: values })}
      />

      <FacetMultiSelect
        label="Tier"
        options={tierOptions}
        selected={request.tiers.map(fromWireTier)}
        onChange={(values) => set({ tier: values.map(toWireTier).map(fromWireTier) })}
      />

      <FacetMultiSelect
        label="Category"
        options={toOptions(facets?.categories)}
        selected={request.categories}
        onChange={(values) => set({ category: values })}
      />

      <FacetMultiSelect
        label="Language"
        options={toOptions(facets?.languages)}
        selected={request.languages}
        onChange={(values) => set({ language: values })}
      />

      <FacetMultiSelect
        label="City"
        options={toOptions(facets?.cities)}
        selected={request.cities}
        onChange={(values) => set({ city: values })}
      />

      <FacetMultiSelect
        label="Gender"
        options={toOptions(facets?.genders)}
        selected={request.genders}
        onChange={(values) => set({ gender: values })}
      />

      <RangeFilter
        label="Followers"
        min={request.min_followers}
        max={request.max_followers}
        onChange={(min, max) => set({ min_followers: min, max_followers: max })}
      />

      <RangeFilter
        label="Avg views"
        min={request.min_avg_views}
        max={request.max_avg_views}
        onChange={(min, max) => set({ min_views: min, max_views: max })}
      />

      <div className="space-y-2 pt-0.5">
        <FilterCheckbox
          id="has-email"
          label="Has email"
          checked={request.has_email}
          onChange={(checked) => set({ has_email: checked })}
        />
        <FilterCheckbox
          id="has-phone"
          label="Has phone"
          checked={request.has_phone}
          onChange={(checked) => set({ has_phone: checked })}
        />
      </div>
    </FilterPanel>
  );
}
