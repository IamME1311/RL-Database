# RL Database — React frontend

Internal search tool for the Ripple Links creator / brand / campaign / pitch database.
Replaces `frontend/streamlit_app.py`, which is kept for reference until this is live.

## Quick start

```bash
cd frontend-react
npm install
cp .env.example .env.local
npm run dev          # http://localhost:5173
```

It runs on fixture data out of the box (`VITE_USE_MOCKS=true`), because **most of the API
endpoints this app needs do not exist in the backend yet**. See
[`../PROPOSED_BACKEND_CHANGES.md`](../PROPOSED_BACKEND_CHANGES.md) for the contract to build,
then flip `VITE_USE_MOCKS=false` to point at the real thing.

In mock mode, any `@ripplelinks.com` address with a 4+ character password signs in.

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server, proxying `/api` → `http://localhost:8000` |
| `npm run build` | Typecheck (`tsc -b`) then production build to `dist/` |
| `npm run typecheck` | Types only |
| `npm run lint` | ESLint |
| `npm run preview` | Serve the built `dist/` |

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | API root. Keep relative in dev so requests stay same-origin. |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Where the dev server forwards `/api`. |
| `VITE_USE_MOCKS` | `true` | Serve `src/lib/mocks` fixtures instead of calling the backend. |

### Why the dev proxy matters

The session is an **httpOnly cookie**. If the SPA were served from `:5173` and the API from
`:8000`, those are cross-origin and the cookie would be subject to `SameSite` / third-party
cookie rules. `vite.config.ts` proxies `/api` to the backend so everything is same-origin,
which is also how it should be deployed — SPA and API behind one hostname. If you must split
hostnames, the backend needs `SameSite=None; Secure` plus CORS `allow_credentials` with an
explicit origin list.

## Layout

```
src/
├── types/api.ts          # the whole API contract — the source of truth for both sides
├── lib/
│   ├── api-client.ts     # fetch wrapper: credentials, CSRF header, abort, ApiError, 401 hook
│   ├── endpoints.ts      # one function per endpoint; routes to real API or mocks
│   ├── enums.ts          # mirror of backend/app/models/enums.py + parser.py raw vocabularies
│   ├── format.ts         # number/date/duration formatting, profile_url derivation
│   ├── query-client.ts   # TanStack defaults + query keys
│   └── mocks/            # fixture data and an in-memory implementation of the contract
├── hooks/                # useDebouncedValue, useUrlSearchState, useTheme
├── features/
│   ├── auth/             # provider, login, Google redirect, guards
│   ├── search/           # omnibox, scope tabs, global view, and one folder per entity
│   └── ingest/           # Apps Script trigger, JSON upload + validator, job history
└── components/           # DataTable, Pagination, facet controls, states, ui/ primitives
```

Each of the four scoped searches is the same pattern: a filter panel, a column config, and a
call to its `use*Search` hook. Only the filters and columns differ — the table, pagination and
URL-state plumbing are shared.

## How live search works

- **The URL is the state.** `q`, `page`, `size`, `sort` and every filter live in search params,
  so a result set is shareable by copying the address bar and back/forward works.
- **Typing is instant, fetching is debounced.** The input holds local state; a 250 ms debounce
  pushes the value into the URL with `replace` so one query doesn't create fifty history entries.
- **Requests cancel.** TanStack's `signal` is passed into `fetch`, so a superseded keystroke's
  request aborts rather than racing the current one.
- **No flicker.** `placeholderData: keepPreviousData` keeps previous rows visible (dimmed) while
  the next page or query resolves.
- Each scope's results are cached under their own query key, so switching tabs is instant.

## Notes on the data

A few schema details the UI has to work around, all documented at the call site:

- `Creator` has no `profile_url` column — `lib/format.ts` derives it from `platform` + `username`,
  and also accepts a server-computed one.
- `TierChoices.NA` is the empty string, which can't be a select value or URL param. The UI uses a
  `__na__` sentinel and converts at the API boundary.
- The tier value is `mid-tier` (hyphen). Every label map is keyed on the real DB value; the
  Streamlit app used `mid_tier` and rendered that tier as a raw string.
- `CampaignCreatorLink` only has `ig_*` and `yt_*` tracker columns, so LinkedIn / Facebook /
  "others" deliverables have nowhere of their own to store metrics.
- Creator emails and phones are masked until explicitly revealed.
- Creator search legitimately returns nothing today: the `pitch_creator` / `campaign_creator`
  ingest sources are declared in the backend but unimplemented, so `creator` has no data source.
