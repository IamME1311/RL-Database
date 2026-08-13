# Proposed backend changes

This is the backend work needed to serve the new React frontend in `frontend-react/`.
Nothing in `backend/` has been modified — this document is the request, and
`frontend-react/src/types/api.ts` is the machine-readable version of every contract below.

The frontend currently runs against in-memory fixtures (`VITE_USE_MOCKS=true`) because
almost none of these endpoints exist yet. As each one lands you can flip that flag and the
corresponding screen starts working — no frontend changes required, as long as the shapes match.

## Priority order

Roughly the order that unblocks the most frontend at once.

| # | Change | Why now |
|---|---|---|
| 1 | [CORS middleware](#1-cors-middleware-blocks-everything) | Without it *nothing* works in a browser |
| 2 | [Auth](#2-auth) | Every other route should sit behind it |
| 3 | [Search endpoints](#4-search-endpoints) + [Postgres search setup](#5-postgres-search-setup) | The core feature |
| 4 | [Facets](#6-facets) | Filter panels are empty without them |
| 5 | [Detail endpoints](#7-detail-endpoints) | Row clicks 404 without them |
| 6 | [Brand directory](#8-brand-directory) | Brand scope needs it |
| 7 | [Redis caching](#9-redis-caching) | Redis is connected but caches nothing |
| 8 | [Ingest changes](#10-ingestion) | Ingest UI needs POST + upload + job records |
| 9 | [Alembic baseline](#11-alembic-has-zero-revisions) | Needed before any schema change ships |
| 10 | [Bugs found while reading](#12-bugs-found-while-reading-the-code) | Independent of the frontend |

Conventions assumed throughout: all routes under `/api/v1`, `snake_case` JSON keys matching the
SQLModel column names, dates as `YYYY-MM-DD`, datetimes as ISO-8601 with offset, and `Decimal`
serialised as a **string** (`"1.85"`) so no float rounding creeps into CPV or cost figures.

---

## 1. CORS middleware (blocks everything)

There is no `CORSMiddleware` and no middleware of any kind in `app/main.py`. This never mattered
because Streamlit is a server-side HTTP client, but a browser SPA is blocked outright.

```python
# app/core/config.py
BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]
FRONTEND_URL: str = "http://localhost:5173"   # used by the Google callback redirect

# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,   # explicit list, never ["*"]
    allow_credentials=True,                         # required: the session is a cookie
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-CSRF-Token"],
)
```

`allow_credentials=True` and `allow_origins=["*"]` are mutually exclusive per the CORS spec, so
the origin list has to be explicit.

**Deployment note:** the dev server proxies `/api` to `:8000` (see `frontend-react/vite.config.ts`)
so dev is same-origin and the cookie behaves exactly as it will in production. Please deploy the
SPA and the API behind **one hostname** (e.g. nginx serving `dist/` at `/` and proxying `/api`).
If they must be on different hostnames the cookie needs `SameSite=None; Secure`, which also means
HTTPS everywhere and makes CSRF protection non-optional.

---

## 2. Auth

Current state: `app/core/security.py` is **0 bytes**. `app/api/v1/auth.py` has three `pass`
stubs and its router is **not mounted** in `app/api/v1/__init__.py`. `pyjwt` and
`pwdlib[argon2,bcrypt]` are in `pyproject.toml` but never imported. `WorkEmail` and
`settings.ALLOWED_DOMAINS` exist in `app/models/auth.py` but are **never applied**, so nothing
currently enforces the `ripplelinks.com` restriction.

### 2.1 Session storage — Redis, not JWT

An opaque random session id in an httpOnly cookie, with the session body in Redis. This gives
real server-side logout and "sign out everywhere", which a stateless JWT cannot, and Redis is
already running and currently used for nothing but a health ping.

```python
# app/core/security.py  (currently empty)
import secrets
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()   # argon2

def hash_password(raw: str) -> str:
    return password_hash.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return password_hash.verify(raw, hashed)

def new_token() -> str:
    return secrets.token_urlsafe(32)


SESSION_TTL = 60 * 60 * 12          # 12 hours, refreshed on use
SESSION_PREFIX = "session:"

async def create_session(redis, user_id: int) -> str:
    sid = new_token()
    await redis.setex(f"{SESSION_PREFIX}{sid}", SESSION_TTL, str(user_id))
    return sid

async def read_session(redis, sid: str) -> int | None:
    user_id = await redis.get(f"{SESSION_PREFIX}{sid}")
    if user_id is None:
        return None
    await redis.expire(f"{SESSION_PREFIX}{sid}", SESSION_TTL)   # sliding expiry
    return int(user_id)

async def destroy_session(redis, sid: str) -> None:
    await redis.delete(f"{SESSION_PREFIX}{sid}")
```

Cookie settings: `httponly=True`, `secure=True` in production, `samesite="lax"`, `path="/"`.
`lax` is correct here — it still sends the cookie on the top-level redirect back from Google.

### 2.2 A `CurrentUser` dependency

Add alongside the existing `SessionDep` / `RedisDep` in `app/api/deps.py`, and apply it to
**every** route except health and the auth endpoints themselves:

```python
async def get_current_user(
    request: Request, session: SessionDep, redis: RedisDep
) -> User:
    sid = request.cookies.get("rl_session")
    if not sid:
        raise HTTPException(401, detail="Not authenticated")
    user_id = await read_session(redis, sid)
    if user_id is None:
        raise HTTPException(401, detail="Session expired")
    user = await session.get(User, user_id)
    if user is None or not user.is_verified:
        raise HTTPException(401, detail="Account unavailable")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]
```

The frontend treats **any** 401 as session loss and redirects to login, so please return 401
only for that — use 403 for "logged in but not allowed".

### 2.3 Enforce the domain restriction

`WorkEmail` is defined and unused. Apply it, and enforce it in both login paths:

```python
# app/models/auth.py
class User(SQLModel, table=True):
    email: WorkEmail = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    can_ingest: bool = Field(default=False, nullable=False)   # see 2.6
```

Note `ALLOWED_DOMAINS: set = {"ripplelinks.com"}` is typed as a bare `set`, so overriding it from
the environment needs a JSON value and yields untyped strings. `set[str]` would be safer. Also
normalise emails to lowercase on write, or `unique=True` won't stop
`Admin@ripplelinks.com` from coexisting with `admin@ripplelinks.com`.

### 2.4 Endpoints

Mount the router (`app/api/v1/__init__.py` currently includes only `health` and `ingest`):

```python
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
```

#### `GET /api/v1/auth/me`
The frontend calls this once on load to establish who you are; it's the whole auth bootstrap.

```json
{
  "id": 1,
  "name": "Ananya Sharma",
  "email": "ananya@ripplelinks.com",
  "is_verified": true,
  "auth_provider": "password",
  "permissions": { "can_ingest": false }
}
```
401 when there's no valid session. Do not return 200 with a null body — the frontend
distinguishes "no session" from "session exists" purely by the status code.

#### `POST /api/v1/auth/login`
Body `{"email": "...", "password": "..."}` → the same `SessionUser` object, plus
`Set-Cookie: rl_session=...` and the CSRF cookie.

| Case | Status | `X-Error-Code` |
|---|---|---|
| Wrong email or password | 401 | `invalid_credentials` |
| Email not on an allowed domain | 403 | `domain_not_allowed` |
| `is_verified == False` | 403 | `not_verified` |

The frontend reads the optional `X-Error-Code` response header to show a specific message
instead of a generic one; it falls back to `detail` if the header is absent. Please use the same
timing/response for "no such user" and "wrong password" so the endpoint doesn't enumerate accounts.

#### `POST /api/v1/auth/logout`
204, deletes the Redis session and clears both cookies. Should succeed even if the session is
already gone.

#### `GET /api/v1/auth/google/login?next=<path>`
307 redirect to Google's consent screen. Include `scope=openid email profile`, a random `state`
stored in Redis (short TTL) together with the validated `next`, and — worth doing —
`hd=ripplelinks.com` so Google itself nudges people to the right account.

**Validate `next` as a relative path** (must start with `/`, no `//` or scheme) before storing it,
or the parameter becomes an open redirect.

#### `GET /api/v1/auth/google/callback?code=...&state=...`
Exchange the code, verify the ID token, then:

1. Check `state` matches what's in Redis → else redirect with `auth_error=state_mismatch`.
2. Require `email_verified` **and** the `ripplelinks.com` domain. Check the `email` claim's
   domain, not only `hd` — `hd` is absent for non-Workspace accounts. On failure redirect with
   `auth_error=domain_not_allowed`.
3. Find or create the `User` (`auth_provider="google"`, no password hash). Whether a first-time
   Google user is auto-created or must be pre-provisioned is your call — the frontend handles
   both, and `not_verified` is the right error code if you require pre-provisioning.
4. Create the session, set the cookie, and **302 to `f"{settings.FRONTEND_URL}/auth/callback?next={next}"`**.

On any failure, redirect to `f"{settings.FRONTEND_URL}/login?auth_error=<code>"`. Error codes the
frontend already has messages for: `domain_not_allowed`, `google_denied`, `google_no_email`,
`state_mismatch`, `invalid_credentials`, `not_verified`, `unknown`.

The frontend's `/auth/callback` route just re-reads `/auth/me` and forwards to `next` — there is
no token exchange in the browser, and the client secret never leaves the backend.

You'll need a Google OAuth library (`authlib` or `google-auth`) and three settings:
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.

### 2.5 CSRF

Cookie auth needs it. Double-submit is enough here: on login, also set a **readable** (non-httpOnly)
`csrf_token` cookie; require the header `X-CSRF-Token` to match it on every non-GET request. The
frontend already reads that cookie and sends the header on every mutation
(`frontend-react/src/lib/api-client.ts`) — nothing more is needed on this side once the backend
sets and checks it.

### 2.6 The ingest permission

You mentioned wanting to configure this yourself. The frontend reads
`permissions.can_ingest` from `/auth/me`, hides the nav entry and guards the route when it's false,
and treats the backend's 403 as the real answer regardless. A single `can_ingest: bool` on `User`
is all the contract needs; if you'd rather have a `role` enum, keep deriving `can_ingest` in the
`/auth/me` response so the frontend doesn't need to know your role model.

**All `/ingest/*` routes must check it server-side.** Hiding a button is not access control.

---

## 3. What must be protected

`GET /api/v1/ingest/ingest_json/{type}` is currently **completely unauthenticated and mutates the
database** — and it's a `GET`, so a crawler, a prefetching browser, or an `<img>` tag on any page
could trigger a full ingest. This is the most urgent single fix in this document, independent of
the frontend. See [§10](#10-ingestion).

---

## 4. Search endpoints

None of these exist — there is no `creators.py` router and no search of any kind (no `tsvector`,
no `pg_trgm`, no `ILIKE`, no GIN indexes). Suggested new module: `app/api/v1/search.py`, mounted at
`/search`, plus `app/services/search.py` for the query building.

All four scoped searches share one response envelope so a single table component serves them all:

```json
{ "total": 240, "pages": 5, "page": 1, "page_size": 50, "rows": [ ... ], "took_ms": 23 }
```

`total` is the count **before** pagination. `page` should be the page actually served — if the
request asks for page 7 of a 3-page result, clamp and return `3` rather than an empty list, so the
UI can correct itself. `took_ms` is optional and only displayed.

### 4.1 `POST /api/v1/search/creators`

The one endpoint with a pre-existing spec: `frontend/streamlit_app.py` was written against it, and
the new frontend keeps the same request and sort vocabulary so that work isn't wasted.

```json
{
  "text": "fitness mumbai",
  "platforms": ["instagram"],
  "tiers": ["micro", "mid-tier"],
  "genders": ["Female"],
  "categories": ["Fitness"],
  "languages": ["Hindi"],
  "cities": ["Mumbai"],
  "has_email": true,
  "has_phone": false,
  "min_followers": 10000,
  "max_followers": null,
  "min_avg_views": null,
  "max_avg_views": null,
  "sort": "relevance",
  "page": 1,
  "page_size": 50
}
```

- Every list is AND-across-fields, OR-within-field (`platform IN (...) AND city IN (...)`).
- `null` means "no bound"; empty lists mean "no filter".
- `tiers` may contain `""` — that's `TierChoices.NA`, a real value, not a blank.
- `text` should be treated as **multiple tokens, all of which must match somewhere** across
  `name`, `username`, `categories_raw`, `languages_raw` and `city`. That's what makes
  `"fitness mumbai"` work, and it's the behaviour the placeholder text promises.
- `sort`: `relevance | followers_desc | followers_asc | avg_views_desc | avg_views_asc | name_asc | name_desc`.
  With `sort=relevance` and no `text`, fall back to `followers_desc` — "most relevant" with no
  query is meaningless, and an unordered page is unstable across pagination. **Always append a
  unique tiebreaker** (`, id`) to every sort, or rows can repeat or vanish between pages.

Row shape (`CreatorRow`):

```json
{
  "id": "uuid", "name": "…", "username": "…", "platform": "instagram",
  "tier": "mid-tier", "followers": 148000, "avg_views": 39000,
  "city": "Mumbai", "gender": "Female",
  "categories_raw": "Fitness, Lifestyle", "languages_raw": "Hindi, English",
  "email": "…", "phone": "…",
  "profile_url": "https://www.instagram.com/handle"
}
```

`profile_url` **is not a column on `Creator`** — the Streamlit app read a field that cannot exist.
Please compute it from `platform` + `username` in the response model:

```python
@computed_field
@property
def profile_url(self) -> str | None:
    handle = (self.username or "").lstrip("@")
    if not handle:
        return None
    return {
        PlatformChoices.INSTAGRAM: f"https://www.instagram.com/{handle}",
        PlatformChoices.YOUTUBE:   f"https://www.youtube.com/@{handle}",
        PlatformChoices.LINKEDIN:  f"https://www.linkedin.com/in/{handle}",
        PlatformChoices.FACEBOOK:  f"https://www.facebook.com/{handle}",
    }.get(self.platform)
```

The frontend derives the same value as a fallback, so the column works either way — but having it
server-side keeps the two from drifting.

**PII:** `email` and `phone` are personal data and are masked in the UI until someone clicks to
reveal. Two things worth considering: omit them entirely for roles that don't need them, and log
reveals. If you want the second, add `POST /api/v1/creators/{id}/contact` returning the unmasked
values and writing an audit row — tell me and I'll switch the reveal button to call it.

### 4.2 `POST /api/v1/search/campaigns`

```json
{
  "text": null,
  "statuses": ["wip"], "report_statuses": [],
  "months": ["august"], "years": [2026],
  "managers": ["Rohit Menon"], "brands": ["boAt"],
  "start_date_from": "2026-01-01", "start_date_to": null,
  "sort": "start_date_desc", "page": 1, "page_size": 50
}
```

`text` covers `campaign_code`, `campaign_name`, `brand_name`, `manager` and `member_names`
(the last is a `text[]`, so `EXISTS (SELECT 1 FROM unnest(member_names) m WHERE m ILIKE …)` or
`array_to_string(member_names, ' ') ILIKE …`).
Sorts: `relevance | start_date_desc | start_date_asc | code_asc | code_desc | creators_desc`.

Row = every `Campaign` column, plus `creator_count` (count of `campaigncreatorlink` rows).
Compute that as a `LEFT JOIN … GROUP BY` or a correlated subquery — not per row in Python.

### 4.3 `POST /api/v1/search/pitches`

```json
{
  "text": null,
  "org_types": ["Agency"], "requirements": ["list_and_plan"],
  "platforms": ["instagram"], "sales_leads": [], "list_leads": [], "companies": [],
  "created_from": null, "created_to": null,
  "converted": true,
  "sort": "created_desc", "page": 1, "page_size": 50
}
```

`text` covers `pitch_code`, `company_name`, `campaign_name`, `sales_lead`, `list_lead` and the
billing company's name. `platforms` filters the `ARRAY(SaEnum(PlatformChoices))` column — use the
overlap operator (`pitch.platform && ARRAY[...]::platformchoices[]`), which a GIN index can serve.
`converted` is tri-state: `true` / `false` / `null` (any), meaning "a `Campaign` row points at this
pitch" — i.e. `EXISTS (SELECT 1 FROM campaign WHERE campaign.pitch_id = pitch.id)`.

Row = every `Pitch` column, plus a nested `billing_company` (`{id, name, gstin}` or `null`),
`creator_count`, and `converted`.

### 4.4 `POST /api/v1/search/brands` — see [§8](#8-brand-directory)

### 4.5 `GET /api/v1/search?q=…&limit=5` — global

Runs all four searches and returns them **grouped**, not interleaved. Relevance isn't comparable
across a creator and a campaign, so a single merged ranking would be arbitrary.

```json
{
  "query": "boat",
  "took_ms": 41,
  "groups": {
    "creators":  { "total": 12, "items": [ /* ≤ limit CreatorRow */ ] },
    "brands":    { "total": 1,  "items": [ /* BrandRow */ ] },
    "campaigns": { "total": 7,  "items": [ /* CampaignRow */ ] },
    "pitches":   { "total": 4,  "items": [ /* PitchRow */ ] }
  }
}
```

`total` is the full match count per group (so the UI can offer "see all 12"), `items` is capped at
`limit`. Please run the four counts concurrently (`asyncio.gather`) — sequentially this is the
slowest endpoint in the app. The frontend only calls it with `q` of 2+ characters.

### 4.6 `GET /api/v1/search/suggest?q=…&limit=8` — typeahead

Fires on every debounced keystroke in the omnibox, so it must be **cheap**: prefix matches only,
a hard `LIMIT`, no counts, no joins beyond what's needed for the sublabel, and Redis-cached.

```json
{
  "query": "zer",
  "suggestions": [
    { "type": "creators",  "id": "uuid",   "label": "Zeenat R",        "sublabel": "@zeenatr · instagram" },
    { "type": "brands",    "id": "Zerodha","label": "Zerodha",         "sublabel": "7 campaigns · 4 pitches" },
    { "type": "campaigns", "id": "uuid",   "label": "Zerodha Reels",   "sublabel": "RL-C0223 · Zerodha" }
  ]
}
```

`id` is what the frontend puts in the URL: the UUID for creators/campaigns/pitches, and the
**brand name** for brands. `type` uses the plural scope names above. Interleave a few of each type
rather than returning eight creators.

---

## 5. Postgres search setup

There is no search infrastructure at all, and no index on most of the columns the filters target.

### 5.1 Indexes for the filters

`Creator` currently indexes nothing except the `username` unique constraint. The filters above hit
`name`, `city`, `followers`, `avg_views`, `tier`, `platform`, `gender`; `Campaign.brand_name` is
also unindexed.

```sql
CREATE INDEX ix_creator_followers   ON creator (followers DESC);
CREATE INDEX ix_creator_avg_views   ON creator (avg_views DESC);
CREATE INDEX ix_creator_city        ON creator (city);
CREATE INDEX ix_creator_tier        ON creator (tier);
CREATE INDEX ix_creator_platform    ON creator (platform);
CREATE INDEX ix_campaign_brand_name ON campaign (brand_name);
CREATE INDEX ix_campaign_start_date ON campaign (start_date DESC);
CREATE INDEX ix_pitch_created_at    ON pitch (created_at DESC);
CREATE INDEX ix_pitch_platform_gin  ON pitch USING GIN (platform);
```

### 5.2 Text search

Two options. I'd suggest **starting with trigram** and only moving to `tsvector` if it isn't enough:

**Trigram (recommended to start).** Handles the typo-ish, partial-handle matching this data needs
(`jhanviithakurrr`), needs no schema change, and supports both `ILIKE '%…%'` and fuzzy ranking.

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_creator_name_trgm     ON creator USING GIN (name gin_trgm_ops);
CREATE INDEX ix_creator_username_trgm ON creator USING GIN (username gin_trgm_ops);
CREATE INDEX ix_creator_cats_trgm     ON creator USING GIN (categories_raw gin_trgm_ops);
CREATE INDEX ix_creator_langs_trgm    ON creator USING GIN (languages_raw gin_trgm_ops);
CREATE INDEX ix_creator_city_trgm     ON creator USING GIN (city gin_trgm_ops);
-- and the equivalents on campaign.campaign_name / brand_name, pitch.company_name / campaign_name
```

Ranking for `sort=relevance` can then be roughly: exact `username` prefix > `name` prefix >
`name` contains > category/city contains, with `followers DESC` as the tiebreaker. That's what the
frontend's mock implements, so the two will feel consistent.

**`tsvector` (if you want proper full-text).** Add a generated column and a GIN index:

```sql
ALTER TABLE creator ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(username, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(categories_raw, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(languages_raw, '')), 'C') ||
    setweight(to_tsvector('simple', coalesce(city, '')), 'C')
  ) STORED;
CREATE INDEX ix_creator_search ON creator USING GIN (search_vector);
```

Use the `simple` dictionary, not `english` — handles and Indian names aren't English words and
stemming them does more harm than good. `websearch_to_tsquery` for the query side, `ts_rank_cd`
for relevance. Note `tsvector` won't match mid-word, so you'd still want trigram for partial
handles; that's why trigram first is the simpler path.

### 5.3 Pagination cost

`COUNT(*)` over a filtered join on every keystroke gets expensive as the table grows. Options, in
order of effort: cache the count in Redis keyed on the filter hash (the count changes only on
ingest); or return an estimate above some threshold. Not urgent at current data volumes, but the
frontend displays `total` and will happily show whatever you send.

---

## 6. Facets

`GET /api/v1/search/facets/{entity}` for `creators | brands | campaigns | pitches`. These populate
the filter panels — an empty response means empty dropdowns.

```jsonc
// creators
{
  "platforms": ["instagram", "youtube"],       // DISTINCT values actually present
  "tiers": ["nano", "micro", "mid-tier", ""],  // "" is TierChoices.NA — include it if present
  "categories": ["Fashion", "Fitness"],        // from the category table, or split categories_raw
  "languages": ["English", "Hindi"],
  "cities": ["Bengaluru", "Mumbai"],
  "genders": ["Female", "Male"],
  "total_creators": 240
}
```

```jsonc
// brands
{ "org_types": [...], "platforms": [...], "total_brands": 63 }

// campaigns
{ "statuses": [...], "report_statuses": [...], "months": [...], "years": [2026, 2025],
  "managers": [...], "brands": [...], "total_campaigns": 120 }

// pitches
{ "org_types": [...], "requirements": [...], "platforms": [...],
  "sales_leads": [...], "list_leads": [...], "companies": [...], "total_pitches": 90 }
```

Return only values **present in the data** (a filter that yields zero rows is just a dead end),
sorted alphabetically, except `years` newest-first. Enum values must be the raw DB values — the
frontend maps them to labels via `src/lib/enums.ts`. These are the best caching candidates in the
app: they change only when data is ingested.

---

## 7. Detail endpoints

### `GET /api/v1/creators/{id}`
`CreatorRow` plus:
```jsonc
{
  "additional_emails": [...], "additional_phones": [...],
  "categories": ["Fitness"],          // from the M2M, not the raw string
  "languages": ["Hindi"],
  "pitches":   [ { "pitch_id", "pitch_code", "company_name", "campaign_name",
                   "platform": [...], "final_cost", "brand_cost" } ],
  "campaigns": [ { "campaign_id", "campaign_code", "campaign_name", "brand_name",
                   "month_name", "year", "status", "is_dropped", "live_date",
                   "final_cost", "views", "cpv" } ]
}
```
`views` = whichever platform's view count applies (see the note in §7.1). `cpv` as a string.
`additional_phones` is typed `list[int]` on the model but stored as `ARRAY(String)` — please
serialise as strings; a leading `+` or `0` would be destroyed by an int round-trip.

### `GET /api/v1/campaigns/{id}`
`CampaignRow` plus `pitch` (`{id, pitch_code, company_name}` or `null`), a `creators` array of
`CampaignCreatorLink` rows joined to creator identity, and a server-computed `totals`:

```jsonc
"totals": {
  "creator_count": 34, "dropped_count": 2,
  "total_final_cost": 5653529, "total_brand_cost": 7066909,
  "total_views": 33446824, "avg_cpv": "1.69"
}
```

Computing the rollup server-side matters: with `is_dropped` rows in the list, the frontend
summing the array would silently include creators who never went live. **Exclude `is_dropped`
rows from the totals.**

`ig_avg_watch_time` / `ig_total_watch_time` / `yt_total_watch_time` are `timedelta`. Serialise as
**total seconds (number)** or an ISO-8601 duration — the frontend parses both, plus Postgres's
`HH:MM:SS`. Total seconds is simplest.

### `GET /api/v1/pitches/{id}`
`PitchRow` plus `campaign` (`{id, campaign_code, campaign_name}` or `null`), a `creators` array of
`PitchCreatorLink` rows joined to creator identity, and
`totals: {creator_count, total_final_cost, total_brand_cost}`.

### `GET /api/v1/brands/{name}` — see §8.

All four are `selectinload` territory. The campaign detail in particular is one campaign → ~34
link rows → each with a creator; done naively that's 35+ queries.

### 7.1 A schema gap worth knowing about

`CampaignCreatorLink` has `ig_*` and `yt_*` tracker columns only. `PlatformChoices` also includes
`linkedin`, `facebook` and `others`, and `Pitch.platform` can be set to them — but a LinkedIn
deliverable has **nowhere of its own to store views, likes or watch time**. The frontend currently
reads `yt_*` for anything that isn't Instagram, which is a guess. If those platforms are actually
used, the tracker columns need a rethink (a generic `platform_metrics` table keyed on platform
would scale better than a third set of prefixed columns). If they're never used in practice,
ignore this.

---

## 8. Brand directory

"Brand" is not a table, which is why this needs a decision rather than just an endpoint. The
concept appears three times:

| Where | Column | Notes |
|---|---|---|
| `company` | `name` | The billing entity, with GSTIN. Unique, indexed. |
| `pitch` | `company_name` | Denormalised string, indexed. |
| `campaign` | `brand_name` | Denormalised string, **not** indexed. |

Nothing guarantees these agree — `"boAt"`, `"Boat"` and `"boAt Lifestyle"` can all coexist across
the three, and there's no normalisation or foreign key tying `Campaign.brand_name` to anything.

**Proposal:** a `brand_directory` SQL view that unions the three sources, grouped on a normalised
name (`lower(trim(name))`), exposing the shape below. A plain view is fine to start; make it
`MATERIALIZED` and refresh after ingest if it gets slow.

```jsonc
{
  "brand": "boAt",               // display name; also the route param and the row's identity
  "company_id": 30,              // null when it doesn't resolve to a company row
  "company_name": "boAt Lifestyle Pvt Ltd",
  "gstin": "27AAAAA1234A1Z5",    // null or "" when not on file
  "pitch_count": 4,
  "campaign_count": 7,
  "creator_count": 61,           // distinct creators across those campaigns/pitches
  "org_types": ["Brand_Core"],   // distinct across its pitches
  "platforms": ["instagram", "youtube"],
  "latest_activity": "2026-08-01" // max(campaign.start_date, pitch.created_at)
}
```

`POST /api/v1/search/brands` filters this view — `text` over `brand`, `company_name` and `gstin`;
plus `org_types`, `platforms`, `has_company`, `has_gstin`, `min_campaigns`, `min_pitches`; sorts
`relevance | name_asc | name_desc | campaigns_desc | pitches_desc | recent_desc`.

`GET /api/v1/brands/{name}` returns the same row plus `total_brand_cost`, `campaigns[]`
(`CampaignRow`), `pitches[]` (`PitchRow`) and `top_creators[]` (`CreatorRow`, by spend or
frequency). Match the name case-insensitively on the normalised key.

**Longer term**, this is a data-model problem rather than a query problem: `Campaign.brand_name`
and `Pitch.company_name` should probably become FKs to `company`, with the strings kept only as
an import audit trail. That's a bigger change than this frontend needs — the view is enough for now.

---

## 9. Redis caching

Redis is connected (`app/core/redis_client.py`, pool of 20, `decode_responses=True`) and used by
exactly one health check. There are no `get`/`set`/`setex` calls anywhere in the backend.

Also worth tidying: two independent clients exist — `app.state.redis` created in the `lifespan`
(`app/main.py:15`) and a per-request one from `get_redis()`. They share the pool, but the lifespan
one is never read by any route, and `RedisDep` is commented out of `main.py:7`. Pick one.

Suggested keys and TTLs:

| Key | TTL | Notes |
|---|---|---|
| `session:{sid}` | 12 h, sliding | §2.1 |
| `oauth_state:{state}` | 5 min | Google `state` + validated `next` |
| `facets:{entity}` | 1 h | Best win here; invalidate explicitly after ingest |
| `search:{entity}:{sha256(canonical_request)}` | 60 s | Short TTL so ingest can't serve stale results for long |
| `suggest:{sha256(q)}` | 5 min | Fires per keystroke; the highest-volume endpoint |
| `count:{entity}:{filter_hash}` | 5 min | If `COUNT(*)` becomes the bottleneck |
| `brand_directory` | 15 min | Or refresh the materialized view instead |

Two things to get right: hash a **canonical** form of the request (sort the filter lists, drop
empty values) or logically identical searches will miss the cache; and **invalidate `facets:*` and
`search:*` at the end of every successful ingest**, since that's the only thing that changes the
underlying data.

Don't cache anything user-scoped under a shared key — with creator PII in the payloads, a cache
key that ignores the requesting user is how one role ends up seeing another's data.

---

## 10. Ingestion

### 10.1 Fix the existing route

`app/api/v1/ingest.py:21-22`:

```python
@router.get("/ingest_json/{type}")
async def ingest_json(session: SessionDep, ingest_type: IngestType):
```

The path declares `{type}` but the handler parameter is `ingest_type`, so FastAPI treats `type` as
an undeclared path placeholder and `ingest_type` as a **required query parameter**. The real call
shape today is `GET /api/v1/ingest/ingest_json/anything?ingest_type=pitch_master`, which is
presumably not the intent.

It should also be a `POST` — it mutates the database — and it must require auth plus `can_ingest`
(see §3; right now it's an unauthenticated `GET` that writes to the DB).

Also, `pitch_creator` and `campaign_creator` are in the `IngestType` enum but fall through to
`{"status": "Failed", "message": "Something went wrong"}` returned with **HTTP 200**. Either
implement them or return 501 — the frontend shows those two sources as "not implemented" based on
the `apps_script_supported` flag in §10.2, so a clear signal is all it needs.

### 10.2 `GET /api/v1/ingest/sources`

Drives the ingest page's cards.

```jsonc
{
  "sources": [
    {
      "source": "pitch_master",
      "label": "Pitch master",
      "apps_script_supported": true,
      "upload_supported": true,
      "row_count": 90,              // rows currently in the DB from this source
      "last_job": { /* IngestJob, or null */ }
    },
    { "source": "campaign_master",  "apps_script_supported": true,  "upload_supported": true,  … },
    { "source": "pitch_creator",    "apps_script_supported": false, "upload_supported": false, … },
    { "source": "campaign_creator", "apps_script_supported": false, "upload_supported": false, … }
  ]
}
```

### 10.3 `POST /api/v1/ingest/apps-script/{source}`

Replaces the `GET`. Returns an `IngestJob` (202 if you run it in the background, 200 if inline).
The pitch fetch has a 250 s timeout, which is a long time to hold an HTTP request open — a
background task plus polling is the better shape, and the frontend already polls
`/ingest/jobs/{job_id}` until the status is terminal.

### 10.4 `POST /api/v1/ingest/upload`

`multipart/form-data` with:

| Field | Type | Notes |
|---|---|---|
| `file` | `UploadFile` | JSON: either a bare array of rows, or `{"data": [...]}` |
| `source` | `str` | An `IngestType` value |
| `dry_run` | `bool` | When true, validate and report but **write nothing** |

Returns an `IngestJob`. Cap the accepted size (the frontend rejects >25 MB client-side, but that's
not a control) and reject a `source` whose parser doesn't exist with a 400 rather than silently
doing nothing.

`dry_run` needs to be genuinely side-effect-free — the frontend's flow is dry-run, show the user
what would change, then re-submit with `dry_run: false`. Easiest correct implementation is to run
the real path inside a transaction and roll back.

The frontend already validates the file **before** upload against the raw shapes in
`app/schemas/apps_script_response.py` (`PitchMasterRow`, `CampaignMasterRow`), and warns about
values that `app/services/parser.py` would silently coerce to `NA` — an `org_type` outside
`{brand - core, brand - other, agency, retainer account}`, a `requirement` outside its eight
strings, a `platform` outside `{instagram, yt, insta + yt, others, insta + others, linkedin,
yt & linkedin, ig & linkedin}` — and about duplicate business keys within one file. **This is a
convenience, not a guarantee. Validate server-side too.**

`GET /api/v1/ingest/schema/{source}` returning the expected field list would let the frontend stop
hard-coding those vocabularies in `src/lib/enums.ts`. Nice to have, not required.

### 10.5 Job records

```jsonc
{
  "job_id": "job_00001",
  "source": "pitch_master",
  "origin": "apps_script",          // or "upload"
  "status": "partial_success",      // queued | running | success | partial_success | failed
  "dry_run": false,
  "started_at": "2026-08-13T09:14:02Z",
  "finished_at": "2026-08-13T09:14:07Z",
  "started_by": "ananya@ripplelinks.com",
  "counts": { "received": 87, "inserted": 26, "updated": 0, "skipped": 61, "failed": 0 },
  "errors": [ { "row": 12, "field": "start_date", "message": "…", "code": "RL-C0231" } ],
  "message": "Ingested 26 pitch_master rows"
}
```

Plus `GET /api/v1/ingest/jobs/{job_id}` and `GET /api/v1/ingest/jobs?limit=20`. A small
`ingest_job` table is the natural home (it gives you the audit trail of who ingested what);
Redis with a TTL would work if you don't want the history. `row` is a 0-based index into the
submitted array — the frontend displays `row + 1`.

### 10.6 Ingest behaviour worth revisiting

Independent of the frontend, from reading `app/services/ingest.py`:

- **Existing rows are skipped, never updated.** Re-running ingest will never pick up an edit made
  in the spreadsheet — a correction to a campaign's status or dates can only ever land once. If
  that's deliberate, fine; if not, an upsert on `pitch_code` / `campaign_code` is what's wanted,
  and the `counts.updated` field above is there for it.
- **N+1 existence checks.** Both methods `SELECT` per row inside a loop to test existence, and the
  campaign path does a second per-row `SELECT` on `Pitch.pitch_code`. One `WHERE code IN (...)`
  up front, or `ON CONFLICT DO NOTHING`, collapses that to a single round trip.
- **`Parser.parse_pitch_master` stamps the current year** onto every `pitch_code`
  (`f"{r.pitch_code}-{date.today().year}"`, `parser.py:15`). Re-ingesting a 2025 sheet in 2026
  will mint `RL-P0101-2026` as a brand-new pitch rather than matching `RL-P0101-2025`.

---

## 11. Alembic has zero revisions

`alembic.ini` and `app/migrations/env.py` are configured (`target_metadata = SQLModel.metadata`,
`compare_type=True`) but there is **no `versions/` directory and no revision files**. The schema is
created by `SQLModel.metadata.create_all` in `init_db`, and the `lifespan` call to it is commented
out (`app/main.py:13`).

Several changes above alter the schema (`User.can_ingest`, indexes, the trigram extension, the
brand view, an `ingest_job` table). Please generate a baseline first:

```bash
cd backend
alembic revision --autogenerate -m "baseline: existing schema"
alembic upgrade head
```

Check the autogenerated file before applying — Alembic won't infer the `pg_trgm` extension, the
GSTIN `CheckConstraint`'s regex, or the generated `tsvector` column, and those need hand-editing.

---

## 12. Bugs found while reading the code

Unrelated to the frontend, but all real:

1. **`app/services/parser.py:79`** — `r.report_status = r.status.lower().strip()` assigns from
   `status`, not `report_status`. Every campaign's report status therefore mirrors its campaign
   status, and the sheet's real report status is discarded on every ingest.
   ```python
   r.report_status = r.report_status.lower().strip()   # was r.status
   ```
   Note this also means existing ingested data has wrong `report_status` values — a backfill may
   be needed once fixed. The frontend surfaces this field prominently in the campaigns table.

2. **`app/api/v1/db.py:11`** — `init_db(reset=True)` is called without `await`. `init_db` is
   `async`, so this creates a coroutine, never runs it, and the endpoint reports
   `{"status": "success", "message": "reset successful!"}` while resetting nothing. The route also
   isn't mounted. If you do mount it: it drops every table, so it must never be reachable in
   production, and it should not be a `GET`.

3. **`app/api/v1/ingest.py:21-22`** — the `{type}` vs `ingest_type` path/query mismatch (§10.1).

4. **`app/models/link_models.py:17,26,35`** — `CategoryCreatorLink.creator_id`,
   `LanguageCreatorLink.creator_id` and `PitchCreatorLink.creator_id` have `default_factory=uuid4`
   on a foreign-key primary key. Inserting a link without an explicit `creator_id` mints a random
   UUID pointing at no creator rather than failing. `CampaignCreatorLink.creator_id` (line 92) gets
   this right with `default=None` — the other three should match it.

5. **`app/models/pitch.py:58` / `app/models/campaign.py:31`** — `Pitch.campaign` and
   `Campaign.pitch` are both declared as scalars, a one-to-one that SQLAlchemy will warn about
   without `uselist=False` in `sa_relationship_kwargs`.

6. **`app/models/creator.py:61`** — `additional_phones: list[int]` over `Column(ARRAY(String))`.
   The annotation and the storage disagree; phone numbers aren't integers (a leading `+` or `0` is
   lost). `list[str]` matches the column.

7. **`app/models/language.py`** — `Language.name` is not unique, while `Category.name` is. Ingest
   will happily create duplicate `Hindi` rows, which then appear twice in the language facet.

8. **`app/models/auth.py:23`** — `User.email` is a plain `str`, so `WorkEmail` (and therefore
   `ALLOWED_DOMAINS`) is dead code. §2.3.

9. **Undeclared dependencies.** `app/models/creator.py` imports `pydantic_extra_types` and
   `app/services/apps_script_client.py` imports `httpx`, neither of which is in
   `pyproject.toml` — `httpx` arrives transitively via `fastapi[standard]`, which is fragile.
   `frontend/streamlit_app.py` also uses `pandas` and `python-dotenv`, both undeclared.

10. **`.env.example`** omits `REDIS_HOST`, `REDIS_PORT`, `ALLOWED_DOMAINS` and
    `MAX_API_CALL_TIMEOUT`, which `config.py` reads, and its last line is `DB_NAME` with no `=`.
    It'll also need the new `BACKEND_CORS_ORIGINS`, `FRONTEND_URL`, `SESSION_SECRET` and
    `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`.

11. **`MAX_API_CALL_TIMEOUT = 300` caps the pitch fetch's 250 s timeout** — fine today, but the
    two numbers are close enough that raising the fetch timeout without raising the cap would be
    silently ignored (`apps_script_client.py:22`).

---

## 13. Two frontend-side notes

Nothing to do here, just so you know what the frontend assumes:

- **The `mid-tier` / `mid_tier` mismatch is fixed on the frontend.** `TierChoices.MID_TIER` is
  `"mid-tier"` (hyphen), but `frontend/streamlit_app.py:67` keyed its label map on `mid_tier`, so
  that tier rendered as a raw string. The new frontend keys every label map on the actual DB value.
  Please keep sending raw enum values, not prettified ones.
- **`TierChoices.NA` is the empty string**, which can't be a `<select>` value or a URL parameter.
  The frontend uses a `__na__` sentinel internally and converts back to `""` at the API boundary,
  so the wire format stays exactly what the enum says. A future cleanup could change that member
  to `"NA"` for consistency with `PlatformChoices.NA` and `OrgTypeChoices.NA`, but it's a data
  migration, so the frontend accommodates it as-is.
