"""
India KRM District Dashboard  —  v2
=====================================
• Login system
• India map with district population
• KRM territory overlay
• Active vs No-Presence slicer
• No West Bengal
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import hashlib
import os
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be very first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HMB PRESENCE MAP",
    page_icon="HMB",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}

/* KPI card */
.kpi-box {
    background:#fff; border-radius:12px; padding:16px 18px;
    border-top:4px solid var(--c,#4285F4);
    box-shadow:0 2px 10px rgba(0,0,0,.08); text-align:center;
}
.kpi-val   { font-size:26px; font-weight:800; color:#1a1a2e; line-height:1.1; }
.kpi-label { font-size:11px; color:#888; text-transform:uppercase; letter-spacing:.6px; margin-top:3px; }

/* Top banner */
.top-banner {
    background: linear-gradient(135deg,#0f3460 0%,#16213e 60%,#1a1a2e 100%);
    border-radius:14px; padding:18px 26px; margin-bottom:16px;
}
.banner-title { color:#fff; font-size:22px; font-weight:800; letter-spacing:.4px; }
.banner-sub   { color:#90cdf4; font-size:12px; margin-top:4px; }

/* Section header */
.sec { font-size:14px; font-weight:700; color:#1a1a2e;
       border-left:4px solid #4285F4; padding-left:9px; margin:12px 0 8px; }

/* Status pill */
.pill-active     { background:#e6f4ea; color:#137333; border-radius:20px;
                   padding:2px 10px; font-size:11px; font-weight:700; }
.pill-nopresence { background:#fce8e6; color:#c5221f; border-radius:20px;
                   padding:2px 10px; font-size:11px; font-weight:700; }
.pill-unassigned { background:#f1f3f4; color:#5f6368; border-radius:20px;
                   padding:2px 10px; font-size:11px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# AUTH  (persistent, admin-managed accounts stored in users.json)
# ─────────────────────────────────────────────────────────────────────────────
import json

USERS_FILE = "users.json"

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    """Load accounts from users.json. On first run (file missing/empty),
    seed a single admin account: sudipta / sudipta@5566."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                data = json.load(f)
            if data:
                return data
        except Exception:
            pass
    default = {"sudipta": {"password_hash": _hash("sudipta@5566"), "role": "admin"}}
    save_users(default)
    return default

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def check_password(u, p):
    users = load_users()
    rec = users.get(u.strip().lower())
    return rec is not None and rec.get("password_hash") == _hash(p)

def get_role(u):
    users = load_users()
    rec = users.get(u.strip().lower())
    return rec.get("role") if rec else None

def login_page():
    _, col, _ = st.columns([1, 1.05, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;margin-bottom:24px;'>
          <div style='font-size:60px;'>🇮🇳</div>
          <div style='font-size:22px;font-weight:800;color:#1a1a2e;margin-top:6px;'>HMB PRESENCE MAP</div>
          <div style='font-size:13px;color:#888;margin-top:4px;'>District Population · KRM Territory · Presence Tracker</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🔐  Sign In", use_container_width=True):
                if check_password(username, password):
                    st.session_state.update({
                        "auth": True,
                        "user": username.strip().lower(),
                        "role": get_role(username),
                        "login_time": datetime.now().strftime("%d %b %Y %H:%M")
                    })
                    st.rerun()
                else:
                    st.error("❌ Wrong username or password")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
KRM_COLORS = {
    "KAUSHIK CHAKRABORTY": "#4285F4",
    "PUSPAK MAJUMDER":     "#EA4335",
    "DEEPAK KUMAR":        "#FBBC04",
    "ARUN KUMAR BHANDARY": "#34A853",
    "NIKET RANJAN":        "#FF6D00",
    "PRAKASH CHAND RAJPUT":"#9C27B0",
    "BHASKAR JYOTI":       "#00BCD4",
    "UNASSIGNED":          "#E8BC75",
}

# Census state name → readable label
STATE_LABELS = {
    "UTTAR PRADESH":    "Uttar Pradesh",
    "BIHAR":            "Bihar",
    "JHARKHAND":        "Jharkhand",
    "ASSAM":            "Assam",
    "TRIPURA":          "Tripura",
    "ARUNACHAL PRADESH":"Arunachal Pradesh",
    "ORISSA":           "Odisha",
}

# State centroids  (lat, lon)
STATE_CENTROIDS = {
    "UTTAR PRADESH":    (26.8, 80.9),
    "BIHAR":            (25.1, 85.3),
    "JHARKHAND":        (23.6, 85.3),
    "ASSAM":            (26.2, 92.9),
    "TRIPURA":          (23.7, 91.7),
    "ARUNACHAL PRADESH":(28.2, 94.7),
    "ORISSA":           (20.5, 84.7),
}

# District-level coordinates (major ones; rest get jittered from state centroid)
DISTRICT_COORDS = {
    # UP
    "LUCKNOW":   (26.85, 80.95), "AGRA":     (27.18, 78.01),
    "VARANASI":  (25.32, 83.00), "ALLAHABAD":(25.44, 81.85),
    "GORAKHPUR": (26.76, 83.37), "MEERUT":   (28.98, 77.71),
    "KANPUR NAGAR":(26.47,80.33),"JAUNPUR":  (25.73, 82.68),
    "GHAZIPUR":  (25.58, 83.57), "FATEHPUR": (25.93, 80.81),
    # Bihar
    "PATNA":     (25.59, 85.14), "GAYA":     (24.79, 85.00),
    "MUZAFFARPUR":(26.12,85.39), "BHAGALPUR":(25.25, 87.01),
    "SAHARSA":   (25.88, 86.60), "JEHANABAD":(25.21, 84.99),
    "KHAGARIA":  (25.50, 86.47), "MUNGER":   (25.37, 86.47),
    "LAKHISARAI":(25.16, 86.09), "ARARIA":   (26.15, 87.47),
    "SUPAUL":    (26.12, 86.60), "VAISHALI": (25.69, 85.20),
    "MOTIHARI":  (26.65, 84.91), "ROHTAS":   (24.97, 83.91),
    # Jharkhand
    "RANCHI":    (23.36, 85.33), "DHANBAD":  (23.80, 86.43),
    "BOKARO":    (23.79, 85.97), "HAZARIBAGH":(23.99,85.36),
    "DEOGHAR":   (24.48, 86.70), "GIRIDIH":  (24.19, 86.30),
    "DUMKA":     (24.27, 87.25), "GODDA":    (24.83, 87.21),
    "KODARMA":   (24.47, 85.59), "RAMGARH":  (23.63, 85.52),
    "CHATRA":    (24.21, 84.87), "JAMTARA":  (23.96, 86.80),
    "KHUNTI":    (23.07, 85.28), "SAHIBGANJ":(25.24, 87.64),
    "PURBI SINGHBHUM":(22.80,86.18),
    "GARHWA":    (24.16, 83.81),
    # Assam
    "KAMRUP METROPOLITAN":(26.14,91.74), "KAMRUP":(26.07,91.35),
    "DIBRUGARH": (27.48, 94.91), "JORHAT":   (26.75, 94.20),
    "SONITPUR":  (26.63, 92.80), "CACHAR":   (24.80, 92.86),
    "KARIMGANJ": (24.87, 92.35), "GOALPARA": (26.17, 90.62),
    "BONGAIGAON":(26.48, 90.56), "MORIGAON": (26.25, 92.34),
    "DARRANG":   (26.50, 91.90),
    # Tripura
    "WEST TRIPURA":  (23.84, 91.28), "SOUTH TRIPURA":(23.27,91.66),
    "NORTH TRIPURA": (24.42, 92.01), "DHALAI":       (24.00, 91.89),
    # Arunachal Pradesh
    "PAPUM PARE":(27.10, 93.62), "TAWANG":(27.59, 91.87),
    "EAST SIANG":(28.22, 95.32),"WEST SIANG":(28.16,94.80),
    # Odisha
    "JAJPUR":    (20.85, 86.33), "BALASORE":  (21.49, 86.93),
    "CUTTACK":   (20.46, 85.88), "KHORDHA":   (20.17, 85.67),
    "PURI":      (19.81, 85.83),
}

def jitter(name, base, spread):
    h = int(hashlib.md5(str(name).encode()).hexdigest()[:4], 16)
    return base + (h / 65535 - 0.5) * spread

def get_coords(district, state):
    if district in DISTRICT_COORDS:
        return DISTRICT_COORDS[district]
    lat0, lon0 = STATE_CENTROIDS.get(state, (22.5, 78.9))
    return jitter(district, lat0, 1.4), jitter(district, lon0, 1.8)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────

# District name aliases: active-file name → census name
DIST_ALIAS = {
    # Jharkhand
    "KODERMA":              "KODERMA",
    "EAST SINGHBHUM":       "PURBI SINGHBHUM",
    "JABRA":                "GARHWA",
    "SARAIKELA KHARSAWAN":  "SARAIKELA-KHARSAWAN",
    "SERAIKELA KHARSAWAN":  "SARAIKELA-KHARSAWAN",
    "LOHARDAGGA":           "LOHARDAGA",
    # GODDA is a genuine Jharkhand census district — it was previously (and
    # wrongly) skipped here, which made it show as NO PRESENCE despite being
    # in the active list. It now maps to itself (no alias needed) so it's
    # left out of this dict entirely.
    # Assam sub-areas → parent census district
    "LAHARIGHAT":       "MORIGAON",
    "BISWANATH .C":     "SONITPUR",
    "BISWANATH":        "SONITPUR",
    "DHEKIAJHULI":      "SONITPUR",
    "SILCHAR":          "CACHAR",
    "MARIGAON":         "MORIGAON",
    "KAMRUP METRO":     "KAMRUP METROPOLITAN",
    # Arunachal
    "ITANAGAR":         "PAPUM PARE",
    "HOLLONGI":         "PAPUM PARE",
    # UP
    "BHADOHI":          "SANT RAVIDAS NAGAR (BHADOHI)",
    "BARABANKI":        "BARA BANKI",
    "KANPUR":           "KANPUR NAGAR",
    # Bihar — East Champaran district's census name is "Purba Champaran";
    # Motihari is that district's headquarters town.
    "PURBI CHAMPARAN":  "PURBA CHAMPARAN",
    "EAST CHAMPARAN":   "PURBA CHAMPARAN",
    "MOTIHARI":         "PURBA CHAMPARAN",
    # Odisha — city/town names and misspellings mapped to their census district
    "JAGATSINGHPUR":    "JAGATSINGHAPUR",
    "BHUBANESWAR":      "KHORDHA",
    "BHUBNESWAR":       "KHORDHA",
    "KHURDHA":          "KHORDHA",
    "BALESWAR":         "BALASORE",
    "BALESHWAR":        "BALASORE",
    "BERHAMPUR":        "GANJAM",
    "KUAKHIA":          "JAJPUR",
    # Tripura local areas → no census district (treated as local presence)
    "INDRA NAGAR":      "_CUSTOM_",
    "SIDDHI ASHRAM":    "_CUSTOM_",
    "SABROOM":          "_CUSTOM_",
}

# Entries in the active-district file that could not be confidently matched
# to a census district (state looks wrong or name is ambiguous) — flagged
# here rather than guessed, so they still show as NO PRESENCE until verified:
#   ODISHA | KESHPUR — "Keshpur" is a real place, but it's in West Bengal
#   (Paschim Medinipur), not Odisha, so it wasn't auto-mapped.

# State name aliases in active file → census state name
STATE_ALIAS = {
    "UTTARPRADESH": "UTTAR PRADESH",
    "ODISHA":       "ORISSA",
}

# States to include (NO West Bengal)
INCLUDE_STATES = {
    "UTTAR PRADESH", "BIHAR", "JHARKHAND", "ASSAM",
    "TRIPURA", "ARUNACHAL PRADESH", "ORISSA",
}

# Extra columns present in the census workbook (beyond the core 5) that we
# now surface in the dashboard instead of silently dropping.
EXTRA_COLS = {
    "JN. KRO":               "jn_kro",
    "Responsible":           "responsible",
    "Total Sale":            "total_sale",
    "last 6 month avg.":     "avg_6month",
    "June Sale":             "june_sale",
    "GG TOTAL SALE":         "gg_total_sale",
    "GG AVERAGE OF 6 MONTH": "gg_avg_6month",
    "IG TOTAL SALE":         "ig_total_sale",
    "IG AVERAGE OF 6 MONTH": "ig_avg_6month",
}
EXTRA_NUMERIC = {
    "total_sale", "avg_6month", "june_sale",
    "gg_total_sale", "gg_avg_6month", "ig_total_sale", "ig_avg_6month",
}

CUSTOM_COLUMNS_FILE = "custom_columns.csv"
CUSTOM_META_FILE    = "custom_columns_meta.json"

def load_custom_columns():
    """Admin-added custom columns, keyed by census 'District code'.
    Everything is stored/read as string to avoid CSV NaN/empty-string dtype
    surprises; numeric conversion (for 'Number' type columns) happens on use."""
    if os.path.exists(CUSTOM_COLUMNS_FILE):
        try:
            cdf = pd.read_csv(CUSTOM_COLUMNS_FILE, dtype=str, keep_default_na=False)
            if "dist_code" in cdf.columns:
                cdf["dist_code"] = pd.to_numeric(cdf["dist_code"], errors="coerce")
                return cdf
        except Exception:
            pass
    return pd.DataFrame({"dist_code": pd.Series(dtype="int")})

def save_custom_columns(cdf):
    cdf.to_csv(CUSTOM_COLUMNS_FILE, index=False)

def custom_column_names():
    cdf = load_custom_columns()
    return [c for c in cdf.columns if c != "dist_code"]

def load_custom_meta():
    import json
    if os.path.exists(CUSTOM_META_FILE):
        try:
            with open(CUSTOM_META_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_custom_meta(meta):
    import json
    with open(CUSTOM_META_FILE, "w") as f:
        json.dump(meta, f)

@st.cache_data(ttl=60, show_spinner="Loading data…")
def load_all():
    # ── Census ────────────────────────────────────────────────
    raw_full = pd.read_excel("india-districts-census-2011.xlsx")

    raw = raw_full.iloc[:, :5].copy()
    raw.columns = ["dist_code", "state", "district", "population", "krm"]
    raw["state"]      = raw["state"].str.strip().str.upper()
    raw["district"]   = raw["district"].str.strip().str.upper()
    raw["population"] = pd.to_numeric(raw["population"], errors="coerce").fillna(0).astype(int)
    raw["krm"]        = raw["krm"].fillna("UNASSIGNED").str.strip().str.upper()

    # ── Extra KRO / sales columns from the same workbook ────────
    for src_col, dest_col in EXTRA_COLS.items():
        if src_col in raw_full.columns:
            raw[dest_col] = raw_full[src_col]
        else:
            raw[dest_col] = pd.NA
    for col in EXTRA_NUMERIC:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    for col in ["jn_kro", "responsible"]:
        raw[col] = raw[col].astype(object).where(raw[col].notna(), None)
        raw[col] = raw[col].apply(lambda v: str(v).strip() if v is not None else None)

    # Remove West Bengal; keep only included states
    census = raw[raw["state"].isin(INCLUDE_STATES)].copy()

    # ── Admin-added custom columns ───────────────────────────
    custom_df = load_custom_columns()
    custom_meta = load_custom_meta()
    if not custom_df.empty and len(custom_df.columns) > 1:
        census = census.merge(custom_df, on="dist_code", how="left")
        for col in custom_column_names():
            if col not in census.columns:
                continue
            census[col] = census[col].where(census[col].notna(), "")
            if custom_meta.get(col) == "number":
                census[col] = pd.to_numeric(census[col], errors="coerce")

    # ── Active districts ─────────────────────────────────────
    act_raw = pd.read_excel("activedistrict.xlsx", header=None)
    act_raw.columns = ["a", "b", "state", "district"]
    act_raw = act_raw.dropna(subset=["state", "district"])
    act_raw = act_raw[act_raw["state"].astype(str).str.strip() != "STATE"]
    act_raw["state"]    = act_raw["state"].str.strip().str.upper()
    act_raw["district"] = act_raw["district"].str.strip().str.upper()

    # Normalize state names
    act_raw["state"] = act_raw["state"].map(lambda s: STATE_ALIAS.get(s, s))

    # Normalize district names via alias map
    act_raw["district_norm"] = act_raw["district"].map(
        lambda d: DIST_ALIAS.get(d, d)
    )
    # Drop custom/skip entries for census matching
    active_set = set(
        act_raw[~act_raw["district_norm"].isin(["_CUSTOM_", "_SKIP_"])]
        .apply(lambda r: (r["state"], r["district_norm"]), axis=1)
        .tolist()
    )

    # ── Tag each census district ─────────────────────────────
    def get_status(row):
        return "ACTIVE" if (row["state"], row["district"]) in active_set else "NO PRESENCE"

    census["status"] = census.apply(get_status, axis=1)

    # ── Coordinates ──────────────────────────────────────────
    census["lat"] = census.apply(lambda r: get_coords(r["district"], r["state"])[0], axis=1)
    census["lon"] = census.apply(lambda r: get_coords(r["district"], r["state"])[1], axis=1)

    # ── Display helpers ──────────────────────────────────────
    census["state_label"]    = census["state"].map(lambda s: STATE_LABELS.get(s, s.title()))
    census["district_title"] = census["district"].str.title()
    census["pop_fmt"]        = census["population"].apply(lambda x: f"{x:,}")
    census["pop_lakh"]       = (census["population"] / 1e5).round(2)

    for col in EXTRA_NUMERIC:
        census[col] = pd.to_numeric(census[col], errors="coerce")
    for col in ["jn_kro", "responsible"]:
        census[col] = census[col].fillna("").astype(str).str.strip()

    return census

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def dashboard():
    df = load_all()

    # ── Sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user'].title()}")
        st.caption(f"Logged in: {st.session_state.get('login_time','')}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown("---")

        st.markdown("### 🔍 Slicers")

        # ── Presence slicer (key feature) ──
        presence_opts = ["All", "ACTIVE", "NO PRESENCE"]
        presence_icons = {"All": "🌐 All Districts",
                          "ACTIVE": "✅ Active Only",
                          "NO PRESENCE": "🔴 No Presence Only"}
        sel_presence = st.radio(
            "📍 Presence Status",
            presence_opts,
            format_func=lambda x: presence_icons[x],
        )

        # State slicer
        state_labels_sorted = sorted(df["state_label"].unique())
        sel_state = st.selectbox("🏛 State", ["All States"] + state_labels_sorted)

        # KRM slicer
        krm_opts = sorted([k for k in df["krm"].unique() if k != "UNASSIGNED"])
        sel_krm  = st.selectbox("👤 KRM (Sales Head)", ["All KRMs"] + krm_opts)

        # District slicer (dynamic based on above)
        dist_pool = df.copy()
        if sel_state    != "All States": dist_pool = dist_pool[dist_pool["state_label"] == sel_state]
        if sel_krm      != "All KRMs":  dist_pool = dist_pool[dist_pool["krm"]         == sel_krm]
        if sel_presence != "All":        dist_pool = dist_pool[dist_pool["status"]      == sel_presence]
        dist_list = ["All Districts"] + sorted(dist_pool["district_title"].unique())
        sel_district = st.selectbox("🏙 District", dist_list)

        st.markdown("---")
        st.markdown("### ⚙️ Map")
        map_color_by = st.radio("Color map by", ["Presence Status", "KRM Territory", "Population"])
        map_style    = st.selectbox("Base map", ["carto-positron", "open-street-map", "carto-darkmatter"])
        show_labels  = st.toggle("District labels on map", value=False)

        st.markdown("---")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── Apply filters ─────────────────────────────────────────
    flt = df.copy()
    if sel_presence != "All":        flt = flt[flt["status"]      == sel_presence]
    if sel_state    != "All States": flt = flt[flt["state_label"] == sel_state]
    if sel_krm      != "All KRMs":  flt = flt[flt["krm"]         == sel_krm]
    if sel_district != "All Districts": flt = flt[flt["district_title"] == sel_district]

    # ── Banner ────────────────────────────────────────────────
    st.markdown(f"""
    <div class="top-banner">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div class="banner-title">HMB PRESENCE MAP</div>
          <div class="banner-sub">
            Census 2011 &nbsp;·&nbsp; {sel_state} &nbsp;·&nbsp;
            {sel_krm} &nbsp;·&nbsp;
            <b style="color:#ffd54f">{presence_icons[sel_presence]}</b>
          </div>
        </div>
        <div style="text-align:right;color:#90cdf4;font-size:12px;line-height:1.8;">
          {flt['state_label'].nunique()} States &nbsp;|&nbsp;
          {len(flt)} Districts &nbsp;|&nbsp;
          Pop: <b style="color:#fff">{flt['population'].sum()/1e7:.2f} Cr</b>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────
    total      = len(flt)
    active_n   = len(flt[flt["status"] == "ACTIVE"])
    nopres_n   = len(flt[flt["status"] == "NO PRESENCE"])
    pct_active = f"{active_n/total*100:.1f}%" if total else "0%"
    pop_total  = flt["population"].sum()

    k1, k2, k3, k4, k5 = st.columns(5)
    kpis = [
        (str(total),          "Total Districts",      "#4285F4"),
        (str(active_n),       "✅ Active Districts",  "#34A853"),
        (str(nopres_n),       "🔴 No Presence",       "#EA4335"),
        (pct_active,          "Active Coverage %",    "#FBBC04"),
        (f"{pop_total/1e7:.2f} Cr", "Total Population", "#9C27B0"),
    ]
    for col, (val, lbl, color) in zip([k1, k2, k3, k4, k5], kpis):
        col.markdown(
            f'<div class="kpi-box" style="--c:{color};">'
            f'<div class="kpi-val">{val}</div>'
            f'<div class="kpi-label">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════
    # TABS
    # ═════════════════════════════════════════════════════════
    is_admin = st.session_state.get("role") == "admin"

    tab_names = [
        "🗺️ India Map",
        "⚠️ Sale, No Responsible",
        "📍 Presence Analysis",
        "👤 KRM View",
        "🏛 State Summary",
        "💰 Sales & KRO",
        "📋 Data Table",
    ]
    if is_admin:
        tab_names.append("🛠 Admin")

    tabs = st.tabs(tab_names)
    tab_map, tab_gap, tab_presence, tab_krm, tab_state, tab_sales, tab_table = tabs[:7]
    tab_admin = tabs[7] if is_admin else None

    # ═════════════════════════════════════════════════════════
    # TAB 1  — MAP
    # ═════════════════════════════════════════════════════════
    with tab_map:
        col_map, col_side = st.columns([3, 1])

        flt = flt.copy()
        flt["responsible_disp"] = flt["responsible"].replace("", "—").fillna("—")
        flt["jn_kro_disp"]      = flt["jn_kro"].replace("", "—").fillna("—")

        with col_map:
            st.markdown('<div class="sec">📍 District Map</div>', unsafe_allow_html=True)

            fig = go.Figure()

            if map_color_by == "Presence Status":
                for status, color, symbol_size in [
                    ("ACTIVE",      "#12EC4C", 11),
                    ("NO PRESENCE", "#DB1402", 11),
                ]:
                    grp = flt[flt["status"] == status]
                    if grp.empty:
                        continue
                    fig.add_trace(go.Scattermapbox(
                        lat=grp["lat"], lon=grp["lon"],
                        mode="markers+text" if show_labels else "markers",
                        marker=dict(size=symbol_size, color=color, opacity=0.85),
                        text=grp["district_title"] if show_labels else None,
                        textposition="top center",
                        textfont=dict(size=8, color="#222"),
                        name=status,
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "State: %{customdata[1]}<br>"
                            "KRM: %{customdata[2]}<br>"
                            "Responsible: %{customdata[5]}<br>"
                            "JN. KRO: %{customdata[6]}<br>"
                            "Population: %{customdata[3]}<br>"
                            "Status: <b>%{customdata[4]}</b>"
                            "<extra></extra>"
                        ),
                        customdata=grp[["district_title","state_label","krm","pop_fmt","status",
                                         "responsible_disp","jn_kro_disp"]].values,
                    ))

            elif map_color_by == "KRM Territory":
                for krm_name, grp in flt.groupby("krm"):
                    color = KRM_COLORS.get(krm_name, "#B0BEC5")
                    fig.add_trace(go.Scattermapbox(
                        lat=grp["lat"], lon=grp["lon"],
                        mode="markers+text" if show_labels else "markers",
                        marker=dict(size=10, color=color, opacity=0.85),
                        text=grp["district_title"] if show_labels else None,
                        textposition="top center",
                        textfont=dict(size=8, color="#222"),
                        name=krm_name,
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "State: %{customdata[1]}<br>"
                            "KRM: <b>%{customdata[2]}</b><br>"
                            "Responsible: %{customdata[5]}<br>"
                            "JN. KRO: %{customdata[6]}<br>"
                            "Population: %{customdata[3]}<br>"
                            "Status: %{customdata[4]}"
                            "<extra></extra>"
                        ),
                        customdata=grp[["district_title","state_label","krm","pop_fmt","status",
                                         "responsible_disp","jn_kro_disp"]].values,
                    ))

            else:  # Population
                import plotly.colors as pc
                smax = flt["population"].max() if not flt.empty else 1
                norm_c = pc.sample_colorscale(
                    pc.sequential.YlOrRd,
                    (flt["population"] / (smax or 1)).fillna(0).clip(0, 1).tolist()
                )
                sizes = (flt["population"] / (smax or 1) * 16 + 5).clip(5, 21)
                fig.add_trace(go.Scattermapbox(
                    lat=flt["lat"], lon=flt["lon"],
                    mode="markers+text" if show_labels else "markers",
                    marker=dict(size=sizes.tolist(), color=norm_c, opacity=0.85),
                    text=flt["district_title"] if show_labels else None,
                    textposition="top center",
                    textfont=dict(size=8, color="#222"),
                    name="Population",
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "State: %{customdata[1]}<br>"
                        "KRM: %{customdata[2]}<br>"
                        "Responsible: %{customdata[5]}<br>"
                        "JN. KRO: %{customdata[6]}<br>"
                        "Population: %{customdata[3]}<br>"
                        "Status: %{customdata[4]}"
                        "<extra></extra>"
                    ),
                    customdata=flt[["district_title","state_label","krm","pop_fmt","status",
                                     "responsible_disp","jn_kro_disp"]].values,
                ))

            # Auto zoom
            zoom, clat, clon = 4.5, 24.0, 85.0
            if sel_state != "All States":
                s_key = [k for k, v in STATE_LABELS.items() if v == sel_state]
                if s_key and s_key[0] in STATE_CENTROIDS:
                    clat, clon = STATE_CENTROIDS[s_key[0]]
                    zoom = 6.5
            if sel_district != "All Districts" and not flt.empty:
                clat = float(flt["lat"].mean())
                clon = float(flt["lon"].mean())
                zoom = 9.0

            fig.update_layout(
                mapbox=dict(style=map_style, zoom=zoom,
                            center=dict(lat=clat, lon=clon)),
                legend=dict(
                    title="Legend", bgcolor="rgba(255,255,255,0.92)",
                    bordercolor="#ddd", borderwidth=1, font=dict(size=11),
                    x=0.01, y=0.99,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=570,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🟢 Green = Active presence  ·  🔴 Red = No presence  ·  Hover for district details")

        with col_side:
            st.markdown('<div class="sec">📊 Quick Stats</div>', unsafe_allow_html=True)

            # Presence breakdown per state
            state_pres = (
                flt.groupby(["state_label", "status"])
                .size().unstack(fill_value=0).reset_index()
            )
            for col_name in ["ACTIVE", "NO PRESENCE"]:
                if col_name not in state_pres.columns:
                    state_pres[col_name] = 0

            for _, row in state_pres.iterrows():
                a  = int(row.get("ACTIVE", 0))
                np = int(row.get("NO PRESENCE", 0))
                tot = a + np
                pct = int(a / tot * 100) if tot else 0
                bar_color = "#34A853" if pct >= 50 else "#EA4335"
                st.markdown(f"""
                <div style="background:#fff;border-radius:10px;padding:10px 13px;
                            margin-bottom:9px;box-shadow:0 1px 5px rgba(0,0,0,.07);">
                  <div style="font-weight:700;font-size:12px;color:#1a1a2e;">{row['state_label']}</div>
                  <div style="display:flex;justify-content:space-between;
                              font-size:11px;color:#666;margin:4px 0;">
                    <span>✅ {a} active</span><span>🔴 {np} absent</span>
                  </div>
                  <div style="background:#f0f0f0;border-radius:6px;height:6px;margin-top:4px;">
                    <div style="background:{bar_color};width:{pct}%;height:6px;border-radius:6px;"></div>
                  </div>
                  <div style="font-size:10px;color:#888;margin-top:2px;">{pct}% covered</div>
                </div>
                """, unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════
    # TAB — SALE HAPPENED, NO RESPONSIBLE ASSIGNED
    # ═════════════════════════════════════════════════════════
    with tab_gap:
        st.markdown('<div class="sec">⚠️ Districts with Sales but No Responsible Assigned</div>',
                    unsafe_allow_html=True)
        st.caption("Districts where at least one sale figure (Total Sale, June Sale, or GG/IG sale) "
                   "is recorded in the census workbook, but the \"Responsible\" column is blank.")

        sale_cols = ["total_sale", "june_sale", "avg_6month",
                     "gg_total_sale", "gg_avg_6month", "ig_total_sale", "ig_avg_6month"]
        has_sale = df[sale_cols].gt(0).any(axis=1)
        no_responsible = df["responsible"].astype(str).str.strip() == ""

        gap_df = df[has_sale & no_responsible].copy()

        g1, g2 = st.columns(2)
        g1.metric("Districts Affected", len(gap_df))
        g2.metric("Total Sale at Risk", f"{gap_df['total_sale'].sum():,.0f}")

        if gap_df.empty:
            st.success("✅ No gaps found — every district with recorded sales has a Responsible assigned.")
        else:
            gap_state = st.selectbox(
                "Filter by state",
                ["All States"] + sorted(gap_df["state_label"].unique()),
                key="gap_state",
            )
            gap_view = gap_df if gap_state == "All States" else gap_df[gap_df["state_label"] == gap_state]

            gap_display = gap_view[[
                "state_label", "district_title", "krm", "jn_kro",
                "total_sale", "june_sale", "gg_total_sale", "ig_total_sale",
            ]].rename(columns={
                "state_label": "State", "district_title": "District", "krm": "KRM",
                "jn_kro": "JN. KRO", "total_sale": "Total Sale", "june_sale": "June Sale",
                "gg_total_sale": "GG Total Sale", "ig_total_sale": "IG Total Sale",
            }).sort_values("Total Sale", ascending=False, na_position="last").reset_index(drop=True)

            st.caption(f"🔴 **{len(gap_display)} districts** with sales but no Responsible")
            st.dataframe(gap_display, use_container_width=True, height=420)

            st.download_button(
                "⬇️ Download List",
                data=gap_display.to_csv(index=False),
                file_name="sales_no_responsible.csv",
                mime="text/csv",
            )

    # ═════════════════════════════════════════════════════════
    # TAB 2  — PRESENCE ANALYSIS
    # ═════════════════════════════════════════════════════════
    with tab_presence:
        st.markdown('<div class="sec">📍 Active vs No-Presence — District Breakdown</div>',
                    unsafe_allow_html=True)

        p1, p2 = st.columns(2)

        with p1:
            # Stacked bar: active vs no-presence per state
            pres_df = (
                df[df["state"].isin(INCLUDE_STATES)]  # use full df (not filtered) for overview
                .groupby(["state_label", "status"])
                .size().reset_index(name="count")
            )
            fig_pres = px.bar(
                pres_df, x="count", y="state_label", color="status",
                orientation="h",
                color_discrete_map={"ACTIVE": "#34A853", "NO PRESENCE": "#EA4335"},
                barmode="stack",
                title="All States — Active vs No-Presence Districts",
                labels={"state_label": "State", "count": "Districts", "status": "Status"},
                height=380,
                text="count",
            )
            fig_pres.update_traces(textposition="inside", insidetextanchor="middle")
            fig_pres.update_layout(
                legend=dict(orientation="h", y=1.08, x=0, title=""),
                margin=dict(l=5, r=10, t=50, b=5),
                yaxis=dict(categoryorder="total ascending"),
            )
            st.plotly_chart(fig_pres, use_container_width=True)

        with p2:
            # Coverage % per state
            cov = (
                df[df["state"].isin(INCLUDE_STATES)]
                .groupby("state_label")
                .apply(lambda g: round(len(g[g["status"]=="ACTIVE"]) / len(g) * 100, 1))
                .reset_index(name="Coverage %")
                .sort_values("Coverage %")
            )
            colors = ["#34A853" if v >= 50 else "#EA4335" for v in cov["Coverage %"]]
            fig_cov = go.Figure(go.Bar(
                x=cov["Coverage %"], y=cov["state_label"],
                orientation="h",
                marker_color=colors,
                text=cov["Coverage %"].map(lambda v: f"{v}%"),
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Coverage: %{x}%<extra></extra>",
            ))
            fig_cov.add_vline(x=50, line_dash="dash", line_color="#888",
                              annotation_text="50%", annotation_position="top")
            fig_cov.update_layout(
                title="KRM District Coverage % by State",
                xaxis=dict(range=[0, 110], title="Coverage %"),
                height=380,
                margin=dict(l=5, r=60, t=50, b=5),
                showlegend=False,
            )
            st.plotly_chart(fig_cov, use_container_width=True)

        # ── No Presence district list (KEY SLICER) ──────────────
        st.markdown('<div class="sec">🔴 No-Presence Districts — Detailed View</div>',
                    unsafe_allow_html=True)

        no_pres_full = df[df["status"] == "NO PRESENCE"].copy()

        np1, np2, np3 = st.columns(3)
        np_state = np1.selectbox("Filter State",
                                  ["All"] + sorted(no_pres_full["state_label"].unique()),
                                  key="np_state")
        np_krm   = np2.selectbox("Filter KRM",
                                  ["All"] + sorted([k for k in no_pres_full["krm"].unique()
                                                    if k != "UNASSIGNED"]),
                                  key="np_krm")
        np_search = np3.text_input("Search district", placeholder="Type to filter…", key="np_search")

        no_pres_flt = no_pres_full.copy()
        if np_state  != "All": no_pres_flt = no_pres_flt[no_pres_flt["state_label"] == np_state]
        if np_krm    != "All": no_pres_flt = no_pres_flt[no_pres_flt["krm"]         == np_krm]
        if np_search:
            no_pres_flt = no_pres_flt[
                no_pres_flt["district_title"].str.contains(np_search, case=False, na=False)
            ]

        st.caption(f"🔴 **{len(no_pres_flt)} districts** with no presence")

        # Show as colored cards grouped by state
        for state_lbl, grp in no_pres_flt.groupby("state_label"):
            krm_color = KRM_COLORS.get(grp["krm"].iloc[0], "#B0BEC5")
            krm_lbl   = grp["krm"].iloc[0]
            pills = "".join(
                f'<span style="background:#fce8e6;color:#c5221f;border-radius:16px;'
                f'padding:3px 10px;font-size:11px;font-weight:600;margin:2px;'
                f'display:inline-block;">{d}</span>'
                for d in sorted(grp["district_title"])
            )
            st.markdown(f"""
            <div style="background:#fff;border-radius:11px;padding:13px 16px;
                        border-left:5px solid {krm_color};margin-bottom:10px;
                        box-shadow:0 1px 6px rgba(0,0,0,.07);">
              <div style="display:flex;justify-content:space-between;align-items:center;
                          margin-bottom:8px;">
                <b style="font-size:14px;color:#1a1a2e;">{state_lbl}</b>
                <span style="font-size:11px;color:{krm_color};font-weight:700;">
                  KRM: {krm_lbl} &nbsp;·&nbsp; {len(grp)} districts absent
                </span>
              </div>
              <div>{pills}</div>
            </div>
            """, unsafe_allow_html=True)

        # Download no-presence list
        dl = no_pres_flt[["state_label","district_title","krm","jn_kro","pop_fmt","status"]].rename(columns={
            "state_label":"State","district_title":"District",
            "krm":"KRM","jn_kro":"JN. KRO","pop_fmt":"Population","status":"Status"
        })
        st.download_button(
            "⬇️ Download No-Presence List",
            data=dl.to_csv(index=False),
            file_name="no_presence_districts.csv",
            mime="text/csv",
        )

    # ═════════════════════════════════════════════════════════
    # TAB 3  — KRM VIEW
    # ═════════════════════════════════════════════════════════
    with tab_krm:
        st.markdown('<div class="sec">👤 KRM Territory Deep-Dive</div>', unsafe_allow_html=True)

        active_krms = sorted([k for k in df["krm"].unique() if k != "UNASSIGNED"])
        chosen_krm  = st.selectbox("Select KRM", active_krms, key="krm_deep")
        krm_df = df[df["krm"] == chosen_krm]

        color = KRM_COLORS.get(chosen_krm, "#4285F4")
        total_k   = len(krm_df)
        active_k  = len(krm_df[krm_df["status"] == "ACTIVE"])
        absent_k  = len(krm_df[krm_df["status"] == "NO PRESENCE"])
        pop_k     = krm_df["population"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Districts",  total_k)
        m2.metric("✅ Active",         active_k)
        m3.metric("🔴 No Presence",    absent_k)
        m4.metric("Population",       f"{pop_k/1e7:.2f} Cr")

        col_a, col_b = st.columns(2)

        with col_a:
            # Active vs no-presence per state for this KRM
            krm_pres = (
                krm_df.groupby(["state_label", "status"])
                .size().reset_index(name="count")
            )
            fig_k = px.bar(
                krm_pres, x="count", y="state_label", color="status",
                orientation="h", barmode="stack",
                color_discrete_map={"ACTIVE": "#34A853", "NO PRESENCE": "#EA4335"},
                title=f"{chosen_krm} — Active vs No-Presence by State",
                text="count", height=350,
                labels={"state_label":"State","count":"Districts"},
            )
            fig_k.update_traces(textposition="inside", insidetextanchor="middle")
            fig_k.update_layout(
                yaxis=dict(categoryorder="total ascending"),
                legend=dict(orientation="h", y=1.08, x=0, title=""),
                margin=dict(l=5, r=10, t=50, b=5),
            )
            st.plotly_chart(fig_k, use_container_width=True)

        with col_b:
            # Top districts by population for this KRM
            top_krm_df = krm_df.nlargest(20, "population")
            fig_kbar = px.bar(
                top_krm_df.sort_values("population"),
                x="population", y="district_title",
                color="status",
                color_discrete_map={"ACTIVE": "#34A853", "NO PRESENCE": "#EA4335"},
                orientation="h",
                title=f"{chosen_krm} — Top Districts by Population",
                labels={"district_title":"District","population":"Population"},
                text="pop_fmt", height=350,
            )
            fig_kbar.update_traces(textposition="outside")
            fig_kbar.update_layout(
                yaxis=dict(categoryorder="total ascending"),
                legend=dict(orientation="h", y=1.08, x=0, title=""),
                margin=dict(l=5, r=60, t=50, b=5),
            )
            st.plotly_chart(fig_kbar, use_container_width=True)

    # ═════════════════════════════════════════════════════════
    # TAB 4  — STATE SUMMARY
    # ═════════════════════════════════════════════════════════
    with tab_state:
        st.markdown('<div class="sec">🏛 State-wise Summary</div>', unsafe_allow_html=True)

        state_sum = (
            df[df["state"].isin(INCLUDE_STATES)]
            .groupby("state_label")
            .agg(
                Total_Districts    = ("district", "count"),
                Active             = ("status",   lambda x: (x == "ACTIVE").sum()),
                No_Presence        = ("status",   lambda x: (x == "NO PRESENCE").sum()),
                Population         = ("population","sum"),
                KRMs               = ("krm",      lambda x: ", ".join(sorted(set(x[x!="UNASSIGNED"]))) or "—"),
            )
            .reset_index()
        )
        state_sum["Coverage %"] = (state_sum["Active"] / state_sum["Total_Districts"] * 100).round(1)
        state_sum["Pop (Cr)"]   = (state_sum["Population"] / 1e7).round(2)

        s1, s2 = st.columns(2)
        with s1:
            fig_ss = px.bar(
                state_sum.sort_values("Population"),
                x="Population", y="state_label",
                orientation="h",
                color="Coverage %",
                color_continuous_scale="RdYlGn",
                range_color=[0, 100],
                title="States by Population (color = coverage %)",
                text="Pop (Cr)",
                height=400,
                labels={"state_label":"State"},
            )
            fig_ss.update_traces(texttemplate="%{text}Cr", textposition="outside")
            fig_ss.update_layout(margin=dict(l=5,r=60,t=40,b=5))
            st.plotly_chart(fig_ss, use_container_width=True)

        with s2:
            fig_cov2 = px.bar(
                state_sum.sort_values("Coverage %"),
                x="Coverage %", y="state_label",
                orientation="h",
                color="Coverage %",
                color_continuous_scale="RdYlGn",
                range_color=[0, 100],
                title="KRM District Coverage % by State",
                text="Coverage %",
                height=400,
                labels={"state_label":"State"},
            )
            fig_cov2.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_cov2.add_vline(x=50, line_dash="dash", line_color="#555")
            fig_cov2.update_layout(margin=dict(l=5,r=60,t=40,b=5))
            st.plotly_chart(fig_cov2, use_container_width=True)

        st.dataframe(
            state_sum[["state_label","Total_Districts","Active","No_Presence","Coverage %","Pop (Cr)","KRMs"]]
            .rename(columns={"state_label":"State","Total_Districts":"Total","Active":"✅ Active",
                              "No_Presence":"🔴 Absent"}),
            use_container_width=True, height=280,
        )

    # ═════════════════════════════════════════════════════════
    # TAB — SALES & KRO
    # ═════════════════════════════════════════════════════════
    with tab_sales:
        st.markdown('<div class="sec">💰 Sales &amp; KRO Data (from census workbook)</div>',
                    unsafe_allow_html=True)
        st.caption("These come from the extra columns in the census file: JN. KRO, Responsible, "
                   "Total Sale, last 6-month avg, June Sale, and GG/IG sale figures.")

        sales_df = flt[flt[["jn_kro", "responsible"]].apply(
            lambda r: bool(r["jn_kro"]) or bool(r["responsible"]), axis=1
        ) | flt["total_sale"].notna()].copy()

        sk1, sk2, sk3, sk4 = st.columns(4)
        sk1.metric("Districts with Sales Data", len(sales_df))
        sk2.metric("Total Sale (sum)", f"{sales_df['total_sale'].sum():,.0f}")
        sk3.metric("June Sale (sum)", f"{sales_df['june_sale'].sum():,.0f}")
        sk4.metric("Avg 6-Month (mean)", f"{sales_df['avg_6month'].mean():,.1f}" if len(sales_df) else "0")

        if sales_df.empty:
            st.info("No JN. KRO / Responsible / Sale figures found for the current filter selection.")
        else:
            sales_display = sales_df[[
                "state_label", "district_title", "krm", "jn_kro", "responsible",
                "total_sale", "avg_6month", "june_sale",
                "gg_total_sale", "gg_avg_6month", "ig_total_sale", "ig_avg_6month",
            ]].rename(columns={
                "state_label": "State", "district_title": "District", "krm": "KRM",
                "jn_kro": "JN. KRO", "responsible": "Responsible",
                "total_sale": "Total Sale", "avg_6month": "Last 6-Mo Avg",
                "june_sale": "June Sale", "gg_total_sale": "GG Total Sale",
                "gg_avg_6month": "GG Avg 6-Mo", "ig_total_sale": "IG Total Sale",
                "ig_avg_6month": "IG Avg 6-Mo",
            }).sort_values("Total Sale", ascending=False, na_position="last").reset_index(drop=True)

            st.dataframe(sales_display, use_container_width=True, height=440)
            st.download_button(
                "⬇️ Download Sales & KRO CSV",
                data=sales_display.to_csv(index=False),
                file_name="sales_kro_data.csv",
                mime="text/csv",
            )

    # ═════════════════════════════════════════════════════════
    # TAB — DATA TABLE
    # ═════════════════════════════════════════════════════════
    with tab_table:
        st.markdown('<div class="sec">📋 Full District Data</div>', unsafe_allow_html=True)

        srch = st.text_input("🔍 Search district / state…", key="tbl_search")
        tbl  = flt.copy()
        if srch:
            tbl = tbl[
                tbl["district_title"].str.contains(srch, case=False, na=False) |
                tbl["state_label"].str.contains(srch, case=False, na=False)
            ]

        # Style the status column
        def color_status(val):
            if val == "ACTIVE":       return "background-color:#e6f4ea;color:#137333;font-weight:700"
            if val == "NO PRESENCE":  return "background-color:#fce8e6;color:#c5221f;font-weight:700"
            return ""

        base_cols = ["state_label","district_title","population","pop_lakh","krm","jn_kro","status"]
        base_rename = {
            "state_label":"State","district_title":"District",
            "population":"Population","pop_lakh":"Pop (Lakh)",
            "krm":"KRM","jn_kro":"JN. KRO","status":"Status",
        }

        extra_toggle = st.toggle("Show Sales columns", value=False, key="tbl_show_extra")
        extras_cols_map = {
            "responsible":"Responsible",
            "total_sale":"Total Sale", "avg_6month":"Last 6-Mo Avg", "june_sale":"June Sale",
            "gg_total_sale":"GG Total Sale", "gg_avg_6month":"GG Avg 6-Mo",
            "ig_total_sale":"IG Total Sale", "ig_avg_6month":"IG Avg 6-Mo",
        }

        cust_cols = [c for c in custom_column_names() if c in tbl.columns]

        cols = list(base_cols)
        rename = dict(base_rename)
        if extra_toggle:
            cols += list(extras_cols_map.keys())
            rename.update(extras_cols_map)
        if cust_cols:
            # Guard against a custom column name colliding with an existing
            # display label (e.g. an admin-created "KRO" column) — collisions
            # would otherwise produce duplicate column names and break
            # Styler.map further down.
            used_labels = set(rename.values())
            for c in cust_cols:
                label = c
                if label in used_labels:
                    label = f"{c} (custom)"
                rename[c] = label
                used_labels.add(label)
            cols += cust_cols

        display_tbl = (
            tbl[cols]
            .rename(columns=rename)
            .sort_values("Population", ascending=False)
            .reset_index(drop=True)
        )

        st.caption(f"Showing {len(display_tbl)} districts")
        st.dataframe(
            display_tbl.style.map(color_status, subset=["Status"]),
            use_container_width=True,
            height=480,
        )

        st.download_button(
            "⬇️ Download CSV",
            data=display_tbl.to_csv(index=False),
            file_name="india_krm_presence.csv",
            mime="text/csv",
        )

    # ═════════════════════════════════════════════════════════
    # TAB — ADMIN (admin user only)
    # ═════════════════════════════════════════════════════════
    if is_admin and tab_admin is not None:
        with tab_admin:
            # ── User accounts (create viewer / admin logins) ──────
            st.markdown('<div class="sec">👥 Admin — User Accounts</div>', unsafe_allow_html=True)
            st.caption("Create login credentials for viewers here. Accounts are saved to `users.json` "
                       "on the server — attach a persistent Railway volume so they survive redeploys.")

            users_now = load_users()
            admin_count = sum(1 for r in users_now.values() if r.get("role") == "admin")

            for uname, rec in sorted(users_now.items()):
                ua, ub, uc = st.columns([3, 2, 1])
                ua.write(f"**{uname}**")
                ub.write(f"`{rec.get('role','viewer')}`")
                is_self = uname == st.session_state.get("user")
                is_only_admin = rec.get("role") == "admin" and admin_count <= 1
                if is_self or is_only_admin:
                    uc.caption("—")
                else:
                    if uc.button("🗑 Remove", key=f"deluser_{uname}"):
                        users_now.pop(uname)
                        save_users(users_now)
                        st.rerun()

            st.markdown("##### ➕ Create a new account")
            with st.form("add_user_form"):
                new_uname = st.text_input("Username")
                new_pw    = st.text_input("Password", type="password")
                new_role  = st.selectbox("Role", ["viewer", "admin"])
                create_user_submitted = st.form_submit_button("Create Account")

            if create_user_submitted:
                uname_clean = new_uname.strip().lower()
                if not uname_clean or not new_pw:
                    st.error("Please enter both a username and a password.")
                elif uname_clean in users_now:
                    st.error("That username already exists.")
                else:
                    users_now[uname_clean] = {"password_hash": _hash(new_pw), "role": new_role}
                    save_users(users_now)
                    st.success(f"Account '{uname_clean}' ({new_role}) created.")
                    st.rerun()

            st.markdown("---")

            st.markdown('<div class="sec">🛠 Admin — Custom Columns</div>', unsafe_allow_html=True)
            st.caption("Add a brand-new column to the district dataset and fill in a value for each "
                       "district. Saved changes persist across sessions and appear throughout the "
                       "dashboard (toggle it on in the Data Table tab).")

            existing_cols = custom_column_names()
            meta = load_custom_meta()

            # ── Existing custom columns: manage / delete ──────────
            st.markdown("#### Existing custom columns")
            if existing_cols:
                for c in existing_cols:
                    ca, cb = st.columns([5, 1])
                    ca.write(f"• **{c}**  <span style='color:#888;font-size:11px;'>({meta.get(c,'text')})</span>",
                              unsafe_allow_html=True)
                    if cb.button("🗑 Delete", key=f"del_{c}"):
                        cdf = load_custom_columns()
                        cdf = cdf.drop(columns=[c])
                        save_custom_columns(cdf)
                        meta.pop(c, None)
                        save_custom_meta(meta)
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.caption("No custom columns yet.")

            st.markdown("---")

            # ── Add a new column ───────────────────────────────────
            st.markdown("#### Add a new column")
            with st.form("add_col_form"):
                new_col_name = st.text_input("Column name", placeholder="e.g. Priority, Notes, Target 2026")
                col_type = st.radio("Value type", ["Text", "Number"], horizontal=True)
                submitted = st.form_submit_button("➕ Create Column")

            if submitted:
                name_clean = new_col_name.strip()
                if not name_clean:
                    st.error("Please enter a column name.")
                elif name_clean in existing_cols or name_clean in df.columns:
                    st.error("A column with that name already exists.")
                else:
                    cdf = load_custom_columns()
                    if cdf.empty or "dist_code" not in cdf.columns or cdf["dist_code"].isna().all():
                        cdf = df[["dist_code"]].drop_duplicates().reset_index(drop=True)
                    cdf[name_clean] = "0" if col_type == "Number" else ""
                    save_custom_columns(cdf)
                    meta[name_clean] = "number" if col_type == "Number" else "text"
                    save_custom_meta(meta)
                    st.session_state["admin_edit_col"] = name_clean
                    st.cache_data.clear()
                    st.success(f"Column '{name_clean}' created. Fill in values below and save.")
                    st.rerun()

            st.markdown("---")

            # ── Fill in values per district ────────────────────────
            all_cols_now = custom_column_names()
            if all_cols_now:
                st.markdown("#### Fill in values per district")
                edit_col = st.selectbox(
                    "Column to edit",
                    all_cols_now,
                    index=all_cols_now.index(st.session_state.get("admin_edit_col", all_cols_now[0]))
                    if st.session_state.get("admin_edit_col") in all_cols_now else 0,
                )

                admin_state_filter = st.selectbox(
                    "Filter by state (optional)",
                    ["All States"] + sorted(df["state_label"].unique()),
                    key="admin_state_filter",
                )

                edit_pool = df.copy()
                if admin_state_filter != "All States":
                    edit_pool = edit_pool[edit_pool["state_label"] == admin_state_filter]

                is_number_col = meta.get(edit_col) == "number"

                edit_view = edit_pool[["dist_code", "state_label", "district_title", edit_col]].rename(
                    columns={"state_label": "State", "district_title": "District"}
                ).sort_values(["State", "District"]).reset_index(drop=True)
                if is_number_col:
                    edit_view[edit_col] = pd.to_numeric(edit_view[edit_col], errors="coerce")

                col_config = {
                    edit_col: (st.column_config.NumberColumn(edit_col)
                               if is_number_col else st.column_config.TextColumn(edit_col))
                }

                edited = st.data_editor(
                    edit_view,
                    use_container_width=True,
                    height=440,
                    disabled=["dist_code", "State", "District"],
                    column_config=col_config,
                    key="admin_data_editor",
                )

                if st.button("💾 Save Changes", type="primary"):
                    cdf = load_custom_columns()
                    edited_vals = edited.set_index("dist_code")[edit_col]
                    edited_vals = edited_vals.map(lambda v: "" if pd.isna(v) else str(v))
                    cdf = cdf.set_index("dist_code")
                    if edit_col not in cdf.columns:
                        cdf[edit_col] = ""
                    cdf.loc[edited_vals.index, edit_col] = edited_vals
                    cdf = cdf.reset_index()
                    save_custom_columns(cdf)
                    st.cache_data.clear()
                    st.success("Saved.")
                    st.rerun()

    st.markdown("---")
    st.caption("HMB PRESENCE MAP Dashboard · POPULATION DATA: Census 2011 · Presence Tracker · Built with Streamlit + Plotly")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.get("auth"):
    login_page()
else:
    dashboard()
