import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { DataTable } from '@/components/DataTable';
import { ErrorState, LoadingState } from '@/components/states';
import { StatRow, StatTile } from '@/components/StatTile';
import {
  DefinitionItem,
  DefinitionList,
  OrgTypeBadge,
  PlatformBadges,
  SectionTitle,
} from '@/components/bits';
import { formatCurrency, formatDate, formatNumber } from '@/lib/format';
import { campaignColumns } from '../campaigns/columns';
import { pitchColumns } from '../pitches/columns';
import { creatorColumns } from '../creators/columns';
import { useBrandDetail } from '../queries';

export function BrandDetailPage() {
  const { brandName } = useParams<{ brandName: string }>();
  const navigate = useNavigate();
  const decoded = brandName ? decodeURIComponent(brandName) : undefined;
  const { data, isPending, isError, error, refetch } = useBrandDetail(decoded);

  if (isPending) return <LoadingState label="Loading brand…" />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div className="space-y-5">
      <div className="min-w-0">
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-1 h-7 px-2 text-xs">
          <Link to="/search/brands">
            <ArrowLeft className="size-3" />
            Back to brands
          </Link>
        </Button>
        <h1 className="truncate text-xl font-semibold">{data.brand}</h1>
        <p className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          {data.company_name ?? 'No billing company linked'}
          {data.org_types.map((orgType) => (
            <OrgTypeBadge key={orgType} orgType={orgType} />
          ))}
        </p>
      </div>

      <StatRow>
        <StatTile label="Campaigns" value={formatNumber(data.campaign_count)} />
        <StatTile label="Pitches" value={formatNumber(data.pitch_count)} />
        <StatTile label="Creators engaged" value={formatNumber(data.creator_count)} />
        <StatTile
          label="Total brand cost"
          value={formatCurrency(data.total_brand_cost)}
          hint="Across all campaigns"
        />
      </StatRow>

      <Card>
        <CardContent className="pt-4">
          <DefinitionList>
            <DefinitionItem label="Billing company">
              {data.company_name ?? <span className="text-muted-foreground">not linked</span>}
            </DefinitionItem>
            <DefinitionItem label="GSTIN">
              {data.gstin ? (
                <span className="font-mono text-xs">{data.gstin}</span>
              ) : (
                <span className="text-muted-foreground">not on file</span>
              )}
            </DefinitionItem>
            <DefinitionItem label="Platforms">
              <PlatformBadges platforms={data.platforms} />
            </DefinitionItem>
            <DefinitionItem label="Last activity">{formatDate(data.latest_activity)}</DefinitionItem>
          </DefinitionList>
        </CardContent>
      </Card>

      <section>
        <SectionTitle count={data.campaigns.length}>Campaigns</SectionTitle>
        <DataTable
          columns={campaignColumns}
          rows={data.campaigns}
          rowKey={(row) => row.id}
          onRowClick={(row) => navigate(`/campaigns/${row.id}`)}
          maxHeightClass="max-h-96"
          emptyState={
            <p className="px-4 py-8 text-center text-xs text-muted-foreground">
              No campaigns for this brand yet.
            </p>
          }
        />
      </section>

      <section>
        <SectionTitle count={data.pitches.length}>Pitches</SectionTitle>
        <DataTable
          columns={pitchColumns}
          rows={data.pitches}
          rowKey={(row) => row.id}
          onRowClick={(row) => navigate(`/pitches/${row.id}`)}
          maxHeightClass="max-h-96"
          emptyState={
            <p className="px-4 py-8 text-center text-xs text-muted-foreground">
              No pitches for this brand yet.
            </p>
          }
        />
      </section>

      {data.top_creators.length > 0 && (
        <section>
          <SectionTitle count={data.top_creators.length}>Most-used creators</SectionTitle>
          <DataTable
            columns={creatorColumns}
            rows={data.top_creators}
            rowKey={(row) => row.id}
            onRowClick={(row) => navigate(`/creators/${row.id}`)}
            maxHeightClass="max-h-96"
          />
        </section>
      )}
    </div>
  );
}
