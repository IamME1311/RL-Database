"""
Streamlit frontend for the Ripple Links creator database.
Talks ONLY to the FastAPI backend over HTTP — no direct DB access.

Run:
    API_BASE_URL=http://localhost:8000/api/v1 streamlit run streamlit_app.py
"""

import os

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Creator Search", page_icon="🔎", layout="wide")


# ---- thin API client -------------------------------------------------------


def api_get(path: str) -> dict:
    resp = httpx.get(f"{API_BASE_URL}{path}", timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, json: dict | None = None) -> dict:
    resp = httpx.post(f"{API_BASE_URL}{path}", json=json, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=600, show_spinner="Loading filters…")
def load_facets() -> dict:
    return api_get("/creators/facets")


@st.cache_data(ttl=60, show_spinner="Searching…")
def run_search(filters: dict) -> dict:
    return api_post("/creators/search", json=filters)


@st.cache_data(ttl=300)
def load_detail(creator_id: str) -> dict:
    return api_get(f"/creators/{creator_id}")


SORT_OPTIONS = {
    "Relevance": "relevance",
    "Followers (high → low)": "followers_desc",
    "Followers (low → high)": "followers_asc",
    "Avg. views (high → low)": "avg_views_desc",
    "Avg. views (low → high)": "avg_views_asc",
    "Name (A → Z)": "name_asc",
    "Name (Z → A)": "name_desc",
}

TIER_LABELS = {
    "nano": "Nano",
    "micro": "Micro",
    "mid_tier": "Mid tier",
    "macro": "Macro",
    "mega": "Mega",
    "celeb": "Celeb",
}


def humanise(value: int | None) -> str:
    if not value:
        return "0"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,}"


# ---- load facets -----------------------------------------------------------

try:
    F = load_facets()
except httpx.HTTPError as exc:
    st.error(f"Can't reach the API at `{API_BASE_URL}` — {exc}")
    st.stop()


# ---- sidebar: filters ------------------------------------------------------

st.sidebar.header("Filters")

platforms = st.sidebar.multiselect("Platform", F["platforms"], format_func=str.title)
tiers = st.sidebar.multiselect(
    "Tier", F["tiers"], format_func=lambda t: TIER_LABELS.get(t, t)
)
categories = st.sidebar.multiselect("Category", F["categories"])
languages = st.sidebar.multiselect("Language", F["languages"])
cities = st.sidebar.multiselect("City", F["cities"])
genders = st.sidebar.multiselect("Gender", F["genders"])

st.sidebar.markdown("**Followers**")
fc1, fc2 = st.sidebar.columns(2)
min_followers = fc1.number_input("Min", min_value=0, value=0, step=1000, key="min_f")
max_followers = fc2.number_input(
    "Max", min_value=0, value=0, step=1000, key="max_f", help="0 = no upper limit"
)

st.sidebar.markdown("**Avg. views**")
vc1, vc2 = st.sidebar.columns(2)
min_views = vc1.number_input("Min", min_value=0, value=0, step=1000, key="min_v")
max_views = vc2.number_input(
    "Max", min_value=0, value=0, step=1000, key="max_v", help="0 = no upper limit"
)

cc1, cc2 = st.sidebar.columns(2)
has_email = cc1.checkbox("Has email")
has_phone = cc2.checkbox("Has phone")

if st.sidebar.button("Reset filters", width="stretch"):
    st.session_state.clear()
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f'{F["total_creators"]:,} creators in the database')


# ---- main: search bar ------------------------------------------------------

st.title("🔎 Creator Search")

top = st.columns([3, 1.2, 1])
text = top[0].text_input(
    "Search name, handle, category, language, or city",
    placeholder="e.g. fitness mumbai, jhanviithakurrr…",
)
sort_label = top[1].selectbox("Sort by", list(SORT_OPTIONS))
page_size = top[2].selectbox("Per page", [25, 50, 100, 250, 500], index=1)

filters = {
    "text": text.strip() or None,
    "platforms": platforms,
    "tiers": tiers,
    "genders": genders,
    "categories": categories,
    "languages": languages,
    "cities": cities,
    "has_email": has_email,
    "has_phone": has_phone,
    "min_followers": min_followers or None,
    "max_followers": max_followers or None,
    "min_avg_views": min_views or None,
    "max_avg_views": max_views or None,
    "sort": SORT_OPTIONS[sort_label],
    "page_size": page_size,
}

# reset to page 1 whenever any filter changes
sig = str(filters)
if st.session_state.get("sig") != sig:
    st.session_state.sig = sig
    st.session_state.page = 1
filters["page"] = st.session_state.get("page", 1)


# ---- run + render ----------------------------------------------------------

try:
    result = run_search(filters)
except httpx.HTTPStatusError as exc:
    st.error(f"Search failed ({exc.response.status_code}): {exc.response.text}")
    st.stop()
except httpx.HTTPError as exc:
    st.error(f"Search failed — {exc}")
    st.stop()

total, pages, rows = result["total"], result["pages"], result["rows"]
st.caption(f'**{total:,}** creators match — page {result["page"]:,} of {pages:,}')

if not rows:
    st.info("No creators match these filters. Try widening the search.")
    st.stop()

df = pd.DataFrame(rows)

show = pd.DataFrame(
    {
        "Name": df["name"],
        "Handle": df["username"],
        "Platform": df["platform"].str.title(),
        "Tier": df["tier"].map(lambda t: TIER_LABELS.get(t, t or "—")),
        "Followers": df["followers"],
        "Avg views": df["avg_views"],
        "City": df["city"],
        "Gender": df["gender"],
        "Categories": df["categories_raw"],
        "Languages": df["languages_raw"],
        "Email": df["email"],
        "Phone": df["phone"],
        "Profile": df["profile_url"],
    }
)

st.dataframe(
    show,
    width="stretch",
    hide_index=True,
    column_config={
        "Followers": st.column_config.NumberColumn(format="%d"),
        "Avg views": st.column_config.NumberColumn(format="%d"),
        "Profile": st.column_config.LinkColumn(display_text="open ↗"),
    },
)

nav = st.columns([1, 1, 4, 2])
if nav[0].button("← Prev", disabled=filters["page"] <= 1, width="stretch"):
    st.session_state.page = filters["page"] - 1
    st.rerun()
if nav[1].button("Next →", disabled=filters["page"] >= pages, width="stretch"):
    st.session_state.page = filters["page"] + 1
    st.rerun()
nav[3].download_button(
    "⬇ Download this page (CSV)",
    data=show.to_csv(index=False).encode(),
    file_name=f'creators_page_{filters["page"]}.csv',
    mime="text/csv",
    width="stretch",
)


# ---- detail panel ----------------------------------------------------------

st.divider()

labels = {
    r["id"]: f'{r["name"] or "(no name)"}  ·  {r["username"] or "—"}  ·  '
    f'{humanise(r["followers"])} followers'
    for r in rows
}
pick = st.selectbox(
    "Inspect a creator", options=list(labels), format_func=lambda i: labels[i]
)

if pick:
    d = load_detail(pick)

    st.subheader(d.get("name") or "(no name)")

    m = st.columns(4)
    m[0].metric("Followers", humanise(d.get("followers")))
    m[1].metric("Avg views", humanise(d.get("avg_views")))
    m[2].metric("Tier", TIER_LABELS.get(d.get("tier"), "—"))
    engagement = (
        f'{(d["avg_views"] / d["followers"]) * 100:.1f}%'
        if d.get("avg_views") and d.get("followers")
        else "—"
    )
    m[3].metric("Views / follower", engagement)

    meta = [
        (d.get("platform") or "").title(),
        d.get("gender"),
        d.get("city"),
    ]
    st.write(" · ".join(x for x in meta if x))

    if d.get("profile_url"):
        st.link_button(f'@{d.get("username")}', d["profile_url"])

    left, right = st.columns(2)

    with left:
        st.markdown("**Contact**")
        emails = [d["email"]] if d.get("email") else []
        emails += d.get("additional_emails") or []
        phones = [str(d["phone"])] if d.get("phone") else []
        phones += [str(p) for p in (d.get("additional_phones") or [])]
        st.write("✉️ " + (", ".join(emails) if emails else "—"))
        st.write("📞 " + (", ".join(phones) if phones else "—"))

    with right:
        cats = d.get("categories") or (
            [d["categories_raw"]] if d.get("categories_raw") else []
        )
        langs = d.get("languages") or (
            [d["languages_raw"]] if d.get("languages_raw") else []
        )
        st.markdown("**Categories**")
        st.write(", ".join(cats) if cats else "—")
        st.markdown("**Languages**")
        st.write(", ".join(langs) if langs else "—")

    pitches = d.get("pitches") or []
    if pitches:
        st.markdown("**Pitches**")
        st.dataframe(
            pd.DataFrame(pitches)[
                ["pitch_code", "company_name", "campaign_name", "platform"]
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("Not attached to any pitch yet.")
