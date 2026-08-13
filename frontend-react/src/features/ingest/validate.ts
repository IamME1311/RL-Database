/**
 * Client-side validation of an uploaded JSON export, before anything is sent.
 *
 * The shapes below mirror backend/app/schemas/apps_script_response.py
 * (PitchMasterRow, CampaignMasterRow) — the RAW sheet rows, all strings — not the
 * normalised enums in schemas/ingest.py. backend/app/services/parser.py does the
 * normalisation, and anything it doesn't recognise is silently coerced to NA. That
 * data loss is invisible today, so this validator reports it as a warning: the
 * upload is still valid, but the user gets to see what will be flattened first.
 */
import {
  RAW_ORG_TYPE_VALUES,
  RAW_PLATFORM_VALUES,
  RAW_REQUIREMENT_VALUES,
  isKnownRawValue,
} from '@/lib/enums';
import type { IngestSource } from '@/types/api';

export type FieldKind = 'string' | 'number' | 'iso_date' | 'string_array';

interface FieldSpec {
  name: string;
  kind: FieldKind;
  required: boolean;
  /** Raw vocabulary parser.py recognises; anything else becomes NA. */
  vocabulary?: readonly string[];
}

const PITCH_MASTER_FIELDS: FieldSpec[] = [
  { name: 'pitch_code', kind: 'string', required: true },
  { name: 'org_type', kind: 'string', required: true, vocabulary: RAW_ORG_TYPE_VALUES },
  { name: 'company_name', kind: 'string', required: true },
  { name: 'campaign_name', kind: 'string', required: true },
  { name: 'requirement', kind: 'string', required: true, vocabulary: RAW_REQUIREMENT_VALUES },
  { name: 'platform', kind: 'string', required: true, vocabulary: RAW_PLATFORM_VALUES },
  { name: 'sales_lead', kind: 'string', required: true },
  { name: 'list_lead', kind: 'string', required: true },
  { name: 'spreadsheet_link', kind: 'string', required: true },
];

const CAMPAIGN_MASTER_FIELDS: FieldSpec[] = [
  { name: 'campaign_code', kind: 'string', required: true },
  { name: 'month_name', kind: 'string', required: true },
  { name: 'year', kind: 'number', required: true },
  { name: 'brand_name', kind: 'string', required: true },
  { name: 'campaign_name', kind: 'string', required: true },
  { name: 'manager', kind: 'string', required: true },
  { name: 'member_names', kind: 'string_array', required: false },
  { name: 'spreadsheet_link', kind: 'string', required: true },
  { name: 'report_link', kind: 'string', required: true },
  { name: 'status', kind: 'string', required: true },
  { name: 'expected_end_date', kind: 'iso_date', required: true },
  { name: 'start_date', kind: 'iso_date', required: true },
  { name: 'end_date', kind: 'iso_date', required: false },
  { name: 'report_status', kind: 'string', required: false },
  { name: 'report_completion_date', kind: 'iso_date', required: false },
  { name: 'pitch_code', kind: 'string', required: true },
];

export const SOURCE_FIELDS: Partial<Record<IngestSource, FieldSpec[]>> = {
  pitch_master: PITCH_MASTER_FIELDS,
  campaign_master: CAMPAIGN_MASTER_FIELDS,
};

export interface ValidationIssue {
  row: number;
  field: string | null;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationReport {
  ok: boolean;
  rows: unknown[];
  rowCount: number;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  /** Keys present in the file that the backend schema doesn't declare. */
  unknownFields: string[];
}

/**
 * `datetime.fromisoformat` in parser.py accepts YYYY-MM-DD and full ISO datetimes
 * but raises on anything else — including the DD/MM/YYYY that spreadsheets love —
 * so check the same shape here rather than trusting Date.parse, which is lenient.
 */
function isIsoDateLike(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}([T ].*)?$/.test(value.trim())) return false;
  return !Number.isNaN(new Date(value.trim()).getTime());
}

function describeType(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
}

export function validateIngestFile(source: IngestSource, parsed: unknown): ValidationReport {
  const errors: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];
  const fields = SOURCE_FIELDS[source];

  if (!fields) {
    return {
      ok: false,
      rows: [],
      rowCount: 0,
      unknownFields: [],
      warnings,
      errors: [
        {
          row: -1,
          field: null,
          message: `Uploads for “${source}” are not supported — the backend has no parser for this source yet.`,
          severity: 'error',
        },
      ],
    };
  }

  // Accept both a bare array and the Apps Script envelope, since people export both.
  let rows: unknown[];
  if (Array.isArray(parsed)) {
    rows = parsed;
  } else if (parsed && typeof parsed === 'object' && Array.isArray((parsed as { data?: unknown }).data)) {
    rows = (parsed as { data: unknown[] }).data;
  } else {
    return {
      ok: false,
      rows: [],
      rowCount: 0,
      unknownFields: [],
      warnings,
      errors: [
        {
          row: -1,
          field: null,
          message:
            'Expected a JSON array of rows, or an object with a "data" array (the Apps Script envelope).',
          severity: 'error',
        },
      ],
    };
  }

  if (rows.length === 0) {
    errors.push({ row: -1, field: null, message: 'The file contains no rows.', severity: 'error' });
  }

  const known = new Set(fields.map((field) => field.name));
  const unknownFields = new Set<string>();
  const seenCodes = new Map<string, number>();
  const codeField = source === 'pitch_master' ? 'pitch_code' : 'campaign_code';

  rows.forEach((row, index) => {
    if (!row || typeof row !== 'object' || Array.isArray(row)) {
      errors.push({
        row: index,
        field: null,
        message: `Expected an object, got ${describeType(row)}.`,
        severity: 'error',
      });
      return;
    }

    const record = row as Record<string, unknown>;

    for (const key of Object.keys(record)) {
      if (!known.has(key)) unknownFields.add(key);
    }

    for (const field of fields) {
      const value = record[field.name];
      const missing = value === undefined || value === null || value === '';

      if (missing) {
        if (field.required) {
          errors.push({
            row: index,
            field: field.name,
            message: `Missing required field “${field.name}”.`,
            severity: 'error',
          });
        }
        continue;
      }

      switch (field.kind) {
        case 'number':
          if (typeof value !== 'number' || !Number.isFinite(value)) {
            errors.push({
              row: index,
              field: field.name,
              message: `“${field.name}” must be a number, got ${describeType(value)}.`,
              severity: 'error',
            });
          }
          break;
        case 'string_array':
          if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
            errors.push({
              row: index,
              field: field.name,
              message: `“${field.name}” must be an array of strings.`,
              severity: 'error',
            });
          }
          break;
        case 'iso_date':
          if (typeof value !== 'string' || !isIsoDateLike(value)) {
            errors.push({
              row: index,
              field: field.name,
              message: `“${field.name}” must be an ISO date (YYYY-MM-DD). Got “${String(value)}”.`,
              severity: 'error',
            });
          }
          break;
        case 'string':
          if (typeof value !== 'string') {
            errors.push({
              row: index,
              field: field.name,
              message: `“${field.name}” must be a string, got ${describeType(value)}.`,
              severity: 'error',
            });
          } else if (field.vocabulary && !isKnownRawValue(value, field.vocabulary)) {
            warnings.push({
              row: index,
              field: field.name,
              message: `“${value}” is not a value the backend parser recognises — it will be stored as NA. Expected one of: ${field.vocabulary.join(', ')}.`,
              severity: 'warning',
            });
          }
          break;
      }
    }

    // Duplicate business keys inside one file: the backend skips rows whose code
    // already exists, so a duplicate here means one of the two is silently dropped.
    const code = record[codeField];
    if (typeof code === 'string' && code) {
      const firstSeen = seenCodes.get(code);
      if (firstSeen !== undefined) {
        warnings.push({
          row: index,
          field: codeField,
          message: `Duplicate ${codeField} “${code}” — also on row ${firstSeen + 1}. Only one will be inserted.`,
          severity: 'warning',
        });
      } else {
        seenCodes.set(code, index);
      }
    }
  });

  return {
    ok: errors.length === 0 && rows.length > 0,
    rows,
    rowCount: rows.length,
    errors,
    warnings,
    unknownFields: [...unknownFields],
  };
}

/** Parse then validate, turning a syntax error into a reportable issue. */
export function parseAndValidate(source: IngestSource, text: string): ValidationReport {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    return {
      ok: false,
      rows: [],
      rowCount: 0,
      unknownFields: [],
      warnings: [],
      errors: [
        {
          row: -1,
          field: null,
          message: `The file is not valid JSON: ${error instanceof Error ? error.message : String(error)}`,
          severity: 'error',
        },
      ],
    };
  }
  return validateIngestFile(source, parsed);
}
