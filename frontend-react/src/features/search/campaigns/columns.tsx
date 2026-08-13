import { Link } from 'react-router-dom';
import type { Column } from '@/components/DataTable';
import { ChipList, ExternalLink, StatusBadge } from '@/components/bits';
import { MONTH_LABELS } from '@/lib/enums';
import { formatDate, formatNumber } from '@/lib/format';
import type { CampaignRow } from '@/types/api';

export const campaignColumns: Column<CampaignRow>[] = [
  {
    id: 'code',
    header: 'Code',
    cell: (row) => (
      <Link
        to={`/campaigns/${row.id}`}
        onClick={(event) => event.stopPropagation()}
        className="font-mono text-xs text-primary hover:underline"
      >
        {row.campaign_code}
      </Link>
    ),
  },
  {
    id: 'name',
    header: 'Campaign',
    cell: (row) => <span className="font-medium">{row.campaign_name}</span>,
    className: 'max-w-64 truncate',
  },
  {
    id: 'brand',
    header: 'Brand',
    cell: (row) => (
      <Link
        to={`/brands/${encodeURIComponent(row.brand_name)}`}
        onClick={(event) => event.stopPropagation()}
        className="hover:underline"
      >
        {row.brand_name}
      </Link>
    ),
  },
  {
    id: 'period',
    header: 'Period',
    cell: (row) => `${MONTH_LABELS[row.month_name] ?? row.month_name} ${row.year}`,
  },
  { id: 'status', header: 'Status', cell: (row) => <StatusBadge status={row.status} /> },
  { id: 'report', header: 'Report', cell: (row) => <StatusBadge status={row.report_status} /> },
  { id: 'manager', header: 'Manager', cell: (row) => row.manager },
  {
    id: 'members',
    header: 'Team',
    cell: (row) => <ChipList items={row.member_names} max={2} />,
  },
  { id: 'creators', header: 'Creators', numeric: true, cell: (row) => formatNumber(row.creator_count) },
  { id: 'start', header: 'Start', cell: (row) => formatDate(row.start_date) },
  { id: 'end', header: 'End', cell: (row) => formatDate(row.end_date ?? row.expected_end_date) },
  {
    id: 'links',
    header: 'Links',
    cell: (row) => (
      <span className="flex items-center gap-2">
        <ExternalLink href={row.spreadsheet_link}>sheet</ExternalLink>
        <ExternalLink href={row.report_link}>report</ExternalLink>
      </span>
    ),
  },
];
