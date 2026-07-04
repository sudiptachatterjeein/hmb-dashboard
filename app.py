"""
India KRM District Dashboard  —  v5
======================================
• Login system
• 🔍 Live smart search: KRM / KRO / JR.KRO / District / State
• 📊 Power-BI-style live dashboard with auto-refresh
• 📦 Product-wise sales (GG / IG) with drill-down
• 📍 Active / No-Presence map & slicer
• WB now included back in active list
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import os
import json
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HMB PRESENCE MAP",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden;}

/* ── KPI card ── */
.kpi-box{background:#fff;border-radius:12px;padding:14px 16px;
         border-top:4px solid var(--c,#4285F4);
         box-shadow:0 2px 10px rgba(0,0,0,.08);text-align:center;}
.kpi-val{font-size:24px;font-weight:800;color:#1a1a2e;line-height:1.1;}
.kpi-label{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.6px;margin-top:3px;}

/* ── Banner ── */
.top-banner{background:linear-gradient(135deg,#0f3460 0%,#16213e 60%,#1a1a2e 100%);
            border-radius:14px;padding:16px 24px;margin-bottom:14px;}
.banner-title{color:#fff;font-size:21px;font-weight:800;}
.banner-sub{color:#90cdf4;font-size:11px;margin-top:3px;}

/* ── Section header ── */
.sec{font-size:13px;font-weight:700;color:#1a1a2e;
     border-left:4px solid #4285F4;padding-left:8px;margin:10px 0 7px;}

/* ── Search result card ── */
.search-card{background:#fff;border-radius:10px;padding:10px 14px;
             border-left:4px solid var(--bc,#4285F4);
             box-shadow:0 1px 6px rgba(0,0,0,.08);margin-bottom:8px;cursor:pointer;}
.search-role{font-size:10px;font-weight:700;text-transform:uppercase;
             letter-spacing:.5px;color:var(--bc,#4285F4);}
.search-name{font-size:15px;font-weight:800;color:#1a1a2e;margin:2px 0;}
.search-sub{font-size:11px;color:#666;}

/* ── Metric delta ── */
.delta-up  {color:#34A853;font-size:12px;font-weight:700;}
.delta-down{color:#EA4335;font-size:12px;font-weight:700;}

/* ── State coverage bar ── */
.cov-row{background:#fff;border-radius:9px;padding:9px 12px;
         margin-bottom:7px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.cov-bar-bg{background:#f0f0f0;border-radius:5px;height:5px;margin-top:4px;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────
USERS = {
    "sudipta":  hashlib.sha256("sudipta@2026".encode()).hexdigest(),
    "manager": hashlib.sha256("krm@2026".encode()).hexdigest(),
    "viewer":  hashlib.sha256("view@2026".encode()).hexdigest(),
}

def check_pw(u, p):
    return USERS.get(u.lower()) == hashlib.sha256(p.encode()).hexdigest()

def login_page():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(html_block("""
        <div style='text-align:center;margin-bottom:22px;'>
          <div style='font-size:58px;'>🇮🇳</div>
          <div style='font-size:22px;font-weight:800;color:#1a1a2e;margin-top:6px;'>HMB Presence Map</div>
          <div style='font-size:12px;color:#888;margin-top:4px;'>
              KRM · KRO · JR.KRO · Sales Dashboard
          </div>
        </div>"""), unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username", placeholder="sudipta / manager / viewer")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("🔐  Sign In", use_container_width=True):
                if check_pw(u, p):
                    st.session_state.update({
                        "auth": True, "user": u,
                        "login_time": datetime.now(timezone.utc).astimezone(IST).strftime("%d %b %Y %H:%M") + " IST",
                    })
                    st.rerun()
                else:
                    st.error("❌ Wrong credentials")
        st.caption("DEVELOPED BY SUDIPTA CHATTERJEE")

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
    "BIPUL PANKAJ":        "#E91E63",
    "UNASSIGNED":          "#B0BEC5",
}

ROLE_COLORS = {
    "KRM":    "#4285F4",
    "KRO":    "#34A853",
    "JR.KRO": "#FF6D00",
    "RESPONSIBLE": "#9C27B0",
}

STATE_LABELS = {
    "UTTAR PRADESH":    "Uttar Pradesh",
    "BIHAR":            "Bihar",
    "JHARKHAND":        "Jharkhand",
    "ASSAM":            "Assam",
    "TRIPURA":          "Tripura",
    "ARUNACHAL PRADESH":"Arunachal Pradesh",
    "ORISSA":           "Odisha",
    "WEST BENGAL":      "West Bengal",
    "RAJASTHAN":        "Rajasthan",
    "MANIPUR":          "Manipur",
}

STATE_ALIAS = {
    "UTTARPRADESH": "UTTAR PRADESH",
    "ODISHA":       "ORISSA",
    "WB":           "WEST BENGAL",
    "KOLKATA":      "WEST BENGAL",
}

STATE_CENTROIDS = {
    "UTTAR PRADESH":    (26.8, 80.9),
    "BIHAR":            (25.1, 85.3),
    "JHARKHAND":        (23.6, 85.3),
    "ASSAM":            (26.2, 92.9),
    "TRIPURA":          (23.7, 91.7),
    "ARUNACHAL PRADESH":(28.2, 94.7),
    "ORISSA":           (20.5, 84.7),
    "WEST BENGAL":      (22.9, 87.8),
    "RAJASTHAN":        (27.0, 74.2),
    "MANIPUR":          (24.7, 93.9),
}

DIST_ALIAS = {
    # Jharkhand
    "EAST SINGHBHUM":       "PURBI SINGHBHUM",
    "JABRA":                "GARHWA",
    "SARAIKELA KHARSAWAN":  "SARAIKELA-KHARSAWAN",
    "LOHARDAGGA":           "LOHARDAGA",
    # Assam
    "LAHARIGHAT":           "MORIGAON",
    "BISWANATH .C":         "SONITPUR",
    "BISWANATH":            "SONITPUR",
    "DHEKIAJHULI":          "SONITPUR",
    "SILCHAR":              "CACHAR",
    "MARIGAON":             "MORIGAON",
    "KAMRUP METRO":         "KAMRUP METROPOLITAN",
    # Arunachal Pradesh
    "ITANAGAR":             "PAPUM PARE",
    "HOLLONGI":             "PAPUM PARE",
    # Uttar Pradesh
    "BHADOHI":              "SANT RAVIDAS NAGAR (BHADOHI)",
    "BARABANKI":            "BARA BANKI",
    "KANPUR":               "KANPUR NAGAR",
    # Bihar
    "MOTIHARI":             "PURBA CHAMPARAN",
    # Odisha
    "BALASORE":             "BALESHWAR",
    "JAJPUR":               "JAJAPUR",
    # West Bengal name variants
    "MEDINIPUR EAST":       "PURBA MEDINIPUR",
    "MEDINIPUR WEST":       "PASCHIM MEDINIPUR",
    "DINAJPUR DAKSHIN":     "DAKSHIN DINAJPUR",
    "DINAJPUR UTTAR":       "UTTAR DINAJPUR",
    "24 PARAGANAS NORTH":   "NORTH TWENTY FOUR PARGANAS",
    "24 PARAGANAS SOUTH":   "SOUTH TWENTY FOUR PARGANAS",
    "EAST BARDHAMAN":       "PURBA BARDHAMAN",
    "WEST BARDHAMAN":       "PASCHIM BARDHAMAN",
    # Skip entries
    "VERBAL":               "_SKIP_",
    "INDRA NAGAR":          "_SKIP_",
    "SIDDHI ASHRAM":        "_SKIP_",
    "SABROOM":              "_SKIP_",
    "SHANTI SHARMA STEEL":  "_SKIP_",
    "SWASTIKA STEEL":       "_SKIP_",
}

DISTRICT_COORDS = {
    # UP
    "LUCKNOW":(26.85,80.95),"AGRA":(27.18,78.01),"VARANASI":(25.32,83.00),
    "GORAKHPUR":(26.76,83.37),"JAUNPUR":(25.73,82.68),"GHAZIPUR":(25.58,83.57),
    "FATEHPUR":(25.93,80.81),"SANT RAVIDAS NAGAR (BHADOHI)":(25.39,82.57),
    "BARA BANKI":(26.93,81.20),"KANPUR NAGAR":(26.47,80.33),
    # Bihar
    "PATNA":(25.59,85.14),"GAYA":(24.79,85.00),"MUZAFFARPUR":(26.12,85.39),
    "SAHARSA":(25.88,86.60),"JEHANABAD":(25.21,84.99),"KHAGARIA":(25.50,86.47),
    "MUNGER":(25.37,86.47),"LAKHISARAI":(25.16,86.09),"ARARIA":(26.15,87.47),
    "SUPAUL":(26.12,86.60),"VAISHALI":(25.69,85.20),"ROHTAS":(24.97,83.91),
    "PURBA CHAMPARAN":(26.65,84.91),
    # Jharkhand
    "RANCHI":(23.36,85.33),"DHANBAD":(23.80,86.43),"BOKARO":(23.79,85.97),
    "HAZARIBAGH":(23.99,85.36),"DEOGHAR":(24.48,86.70),"GIRIDIH":(24.19,86.30),
    "DUMKA":(24.27,87.25),"GODDA":(24.83,87.21),"KODARMA":(24.47,85.59),
    "RAMGARH":(23.63,85.52),"CHATRA":(24.21,84.87),"JAMTARA":(23.96,86.80),
    "KHUNTI":(23.07,85.28),"SAHIBGANJ":(25.24,87.64),
    "PURBI SINGHBHUM":(22.80,86.18),"GARHWA":(24.16,83.81),
    "LATEHAR":(23.74,84.50),"PALAMU":(24.03,84.07),"GUMLA":(23.04,84.54),
    "SARAIKELA-KHARSAWAN":(22.68,85.93),"LOHARDAGA":(23.43,84.69),
    # Assam
    "KAMRUP METROPOLITAN":(26.14,91.74),"KAMRUP":(26.07,91.35),
    "DIBRUGARH":(27.48,94.91),"JORHAT":(26.75,94.20),"SONITPUR":(26.63,92.80),
    "CACHAR":(24.80,92.86),"KARIMGANJ":(24.87,92.35),"GOALPARA":(26.17,90.62),
    "BONGAIGAON":(26.48,90.56),"MORIGAON":(26.25,92.34),"DARRANG":(26.50,91.90),
    # Tripura
    "WEST TRIPURA":(23.84,91.28),"SOUTH TRIPURA":(23.27,91.66),
    "NORTH TRIPURA":(24.42,92.01),"DHALAI":(24.00,91.89),
    # Arunachal Pradesh
    "PAPUM PARE":(27.10,93.62),
    # Odisha
    "JAJAPUR":(20.85,86.33),"BALESHWAR":(21.49,86.93),
    # West Bengal
    "KOLKATA":(22.57,88.36),"DARJILING":(27.04,88.26),"HOWRAH":(22.59,88.30),
    "PURBA BARDHAMAN":(23.25,87.85),"PASCHIM BARDHAMAN":(23.66,87.07),
    "PURBA MEDINIPUR":(22.43,87.72),"PASCHIM MEDINIPUR":(22.42,86.93),
    "MURSHIDABAD":(24.18,88.27),"NADIA":(23.47,88.56),"BIRBHUM":(23.90,87.53),
    "NORTH TWENTY FOUR PARGANAS":(22.85,88.57),
    "SOUTH TWENTY FOUR PARGANAS":(22.00,88.41),
    "HOOGHLY":(22.90,88.39),"BANKURA":(23.23,86.96),
    "PURULIA":(23.33,86.36),"COOCH BEHAR":(26.33,89.44),
    "MALDAH":(25.01,88.13),"JALPAIGURI":(26.54,88.73),
    "UTTAR DINAJPUR":(26.17,88.12),"DAKSHIN DINAJPUR":(25.62,88.77),
    "ALIPURDUAR":(26.49,89.52),"JHARGRAM":(22.45,86.99),
}

FILES = {
    "census":  "india-districts-census-2011.xlsx",
    "active":  "activedistrict.xlsx",
    "custom":  "custom_columns.csv",
    "meta":    "custom_columns_meta.json",
}

TEAM_FILE  = "sales_backend_teams.json"  # admin-managed Sales Backend Team ↔ State/District mapping
ALIAS_FILE = "custom_alias_map.json"     # admin-managed State/District name-mapping overrides

SALES_SOURCE_FILE = "sales_invoice_data.xlsx"
# Optional admin-uploaded raw invoice/order export. Expected columns (case-insensitive,
# order doesn't matter): INVOICE NO, DESPATCH DATE, ORDER NO, ORDER DATE, BILLING NAME,
# CLIENT NAME, STATE, DISTRICT/ST, QTY, PRODUCT.
# When present, ALL sales figures (Total Sale, current-month Sale, 6-Month Avg, GG/IG
# totals) across every tab are computed live from this file instead of the pre-built
# sale columns in the census workbook — population, KRM/KRO/JR.KRO ownership etc. still
# come from the census file and are auto-matched in by district. Remove the file (via
# the admin tab) to revert to the census workbook's built-in sale columns.

MONTH_NAMES = ["January","February","March","April","May","June","July",
               "August","September","October","November","December"]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def find_month_sale_column(columns):
    """Locate the 'current month' sale column in the census workbook
    (e.g. 'June Sale', 'July Sale'). This header changes every month as the
    sheet gets refreshed, so instead of hardcoding a month name we detect it
    by pattern — this keeps the dashboard working automatically after each
    monthly data refresh, with no code change required.

    Returns (column_name, month_name), or (None, None) if nothing matches.
    """
    cols = [str(c).strip() for c in columns]

    # 1) Exact "<Month> Sale" match
    for month in MONTH_NAMES:
        target = f"{month} Sale".lower()
        for c in cols:
            if c.lower() == target:
                return c, month

    # 2) Fallback: any "<word> Sale" column that isn't a known aggregate
    known = {"total sale", "gg total sale", "ig total sale"}
    for c in cols:
        cl = c.lower()
        if cl.endswith(" sale") and cl not in known:
            guess_month = c.split(" ")[0].title()
            return c, guess_month

    return None, None

def jitter(name, base, spread):
    h = int(hashlib.md5(str(name).encode()).hexdigest()[:4], 16)
    return base + (h / 65535 - 0.5) * spread

def get_coords(district, state):
    if district in DISTRICT_COORDS:
        return DISTRICT_COORDS[district]
    lat0, lon0 = STATE_CENTROIDS.get(state, (22.5, 82.0))
    return jitter(district, lat0, 1.3), jitter(district, lon0, 1.7)

def fmt_mt(v):
    """Format a sales quantity expressed in Metric Tons (MT)."""
    if pd.isna(v): return "—"
    if v >= 1e5:
        return f"{v/1e3:,.1f}K MT"
    return f"{v:,.1f} MT"

def html_block(s: str) -> str:
    """Strip per-line leading whitespace before passing multi-line HTML to
    st.markdown(). Without this, lines indented 4+ spaces (to match Python
    code indentation) get misread by the Markdown parser as an indented
    code block, so the HTML tags show up as literal, unrendered text."""
    return "\n".join(line.lstrip() for line in s.strip("\n").split("\n"))

def safe_div(a, b):
    return round(a / b * 100, 1) if b else 0

def forecast_next_month(monthly_state_df):
    """Simple linear-trend projection of next month's QTY per state, from a
    (state, month, QTY) series. Not a trained ML model — a transparent,
    explainable trend line — but useful as an early-warning signal. Needs
    at least 2 distinct months of data per state to fit a trend; states
    with only 1 month get their forecast set equal to that month's value.
    Returns a DataFrame: state, last_month, last_actual, forecast_next, trend_pct.
    """
    rows = []
    for state, g in monthly_state_df.groupby("state"):
        g = g.sort_values("month")
        y = g["QTY"].to_numpy(dtype=float)
        last_month = g["month"].iloc[-1]
        last_actual = y[-1]
        if len(y) >= 2:
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            forecast = max(0.0, slope * len(y) + intercept)
        else:
            forecast = last_actual
        trend_pct = safe_div(forecast - last_actual, last_actual) if last_actual else 0
        rows.append({
            "state": state, "last_month": last_month, "last_actual": last_actual,
            "forecast_next": forecast, "trend_pct": trend_pct, "months_of_data": len(y),
        })
    return pd.DataFrame(rows).sort_values("forecast_next", ascending=False)

def file_mtime(path):
    return os.path.getmtime(path) if os.path.exists(path) else 0

IST = timezone(timedelta(hours=5, minutes=30))

def get_last_update_str():
    """Human-readable date/time (India, +5:30) of the most recently updated data file."""
    keys = ["census", "active", "custom"]
    mtimes = [file_mtime(FILES[k]) for k in keys if file_mtime(FILES[k]) > 0]
    if file_mtime(SALES_SOURCE_FILE) > 0:
        mtimes.append(file_mtime(SALES_SOURCE_FILE))
    if not mtimes:
        return "No data uploaded yet"
    ist_dt = datetime.fromtimestamp(max(mtimes), tz=timezone.utc).astimezone(IST)
    return ist_dt.strftime("%d %b %Y · %I:%M %p") + " IST"

# ─────────────────────────────────────────────────────────────────────────────
# SALES BACKEND TEAM  (admin-managed State / District mapping)
# ─────────────────────────────────────────────────────────────────────────────
def load_teams():
    if os.path.exists(TEAM_FILE):
        try:
            with open(TEAM_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_teams(teams):
    with open(TEAM_FILE, "w") as f:
        json.dump(teams, f, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# STATE / DISTRICT NAME MAPPING  (admin-managed overrides)
# ─────────────────────────────────────────────────────────────────────────────
# The "active district" file and the census file often spell state/district
# names differently (e.g. "WB" vs "WEST BENGAL", "MOTIHARI" vs "PURBA
# CHAMPARAN"). STATE_ALIAS / DIST_ALIAS above cover the mappings known when
# this app was built, but new mismatches will keep showing up as the source
# files get updated. Rather than editing code every time, admins can add new
# mappings from the "🗺️ Location Mapping" admin tab; those go here, in a
# JSON file, and are merged on top of the built-in defaults at load time.
def load_alias_overrides():
    if os.path.exists(ALIAS_FILE):
        try:
            with open(ALIAS_FILE, "r") as f:
                data = json.load(f)
            return {"states": data.get("states", {}), "districts": data.get("districts", {})}
        except Exception:
            return {"states": {}, "districts": {}}
    return {"states": {}, "districts": {}}

def save_alias_overrides(overrides):
    with open(ALIAS_FILE, "w") as f:
        json.dump(overrides, f, indent=2)

def effective_alias_maps():
    """Built-in STATE_ALIAS/DIST_ALIAS merged with admin-added overrides
    (overrides win on conflict)."""
    overrides = load_alias_overrides()
    state_alias = {**STATE_ALIAS, **{k.upper(): v.upper() for k, v in overrides["states"].items()}}
    dist_alias  = {**DIST_ALIAS,  **{k.upper(): v.upper() for k, v in overrides["districts"].items()}}
    return state_alias, dist_alias

# ─────────────────────────────────────────────────────────────────────────────
# RAW SALES / INVOICE DATA  (optional admin-uploaded data source)
# ─────────────────────────────────────────────────────────────────────────────
def classify_product(product):
    """GG / IG bucketing for the product-wise cards. Anything that doesn't
    contain 'GG' or 'IG' in its product text falls into OTHER (still counted
    in Total Sale, just not split into the GG/IG cards)."""
    p = str(product).upper()
    if "GG" in p: return "GG"
    if "IG" in p: return "IG"
    return "OTHER"

def compute_invoice_sales(path, state_alias, dist_alias):
    """Read a raw invoice/order-level sales export and aggregate it to
    district level (Total Sale, current-month Sale, 6-Month Avg, GG/IG).

    Expected columns (case-insensitive, any order): INVOICE NO, DESPATCH
    DATE, ORDER NO, ORDER DATE, BILLING NAME, CLIENT NAME, STATE,
    DISTRICT/ST, QTY, PRODUCT. Only STATE, DISTRICT/ST, QTY and a date
    column (DESPATCH DATE, falling back to ORDER DATE) are required.

    Returns (agg_df, month_name, unmatched_df, row_count) or
    (None, None, None, 0) if no file / no usable rows.
    """
    if not path or not os.path.exists(path):
        return None, None, None, 0, None

    try:
        inv = pd.read_csv(path) if str(path).lower().endswith(".csv") else pd.read_excel(path)
    except Exception as e:
        st.error(f"⚠️ Couldn't read the sales data file: {e}")
        return None, None, None, 0, None

    inv.columns = [str(c).strip().upper() for c in inv.columns]

    def pick(*names):
        for n in names:
            if n in inv.columns:
                return n
        return None

    col_state    = pick("STATE")
    col_district = pick("DISTRICT/ST", "DISTRICT / ST", "DISTRICT", "DIST", "DISTRICT NAME")
    col_qty      = pick("QTY", "QUANTITY")
    col_date     = pick("DESPATCH DATE", "DISPATCH DATE", "ORDER DATE")
    col_product  = pick("PRODUCT", "PRODUCT NAME", "ITEM")

    missing = [label for label, col in [
        ("STATE", col_state), ("DISTRICT/ST", col_district),
        ("QTY", col_qty), ("DESPATCH DATE (or ORDER DATE)", col_date),
    ] if col is None]
    if missing:
        st.error(
            "⚠️ Sales data file is missing required column(s): "
            f"**{', '.join(missing)}**.\n\nColumns found: {', '.join(inv.columns)}"
        )
        return None, None, None, 0, None

    inv = inv.rename(columns={col_state: "STATE", col_district: "DISTRICT_RAW",
                               col_qty: "QTY", col_date: "DATE"})
    inv["PRODUCT"] = inv[col_product] if col_product else ""

    inv["STATE"]        = inv["STATE"].astype(str).str.strip().str.upper()
    inv["DISTRICT_RAW"] = inv["DISTRICT_RAW"].astype(str).str.strip().str.upper()
    inv["QTY"]          = pd.to_numeric(inv["QTY"], errors="coerce").fillna(0)
    inv["DATE"]         = pd.to_datetime(inv["DATE"], errors="coerce")
    inv = inv.dropna(subset=["DATE"])
    row_count = len(inv)
    if inv.empty:
        return None, None, None, 0, None

    inv["state_norm"] = inv["STATE"].map(lambda s: state_alias.get(s, s))
    inv["dist_norm"]  = inv["DISTRICT_RAW"].map(lambda d: dist_alias.get(d, d))
    inv = inv[inv["dist_norm"] != "_SKIP_"]

    inv["month_period"] = inv["DATE"].dt.to_period("M")
    latest_period  = inv["month_period"].max()
    month_name     = latest_period.strftime("%B")
    months_present = sorted(inv["month_period"].unique())
    last6          = months_present[-6:]

    inv["bucket"] = inv["PRODUCT"].map(classify_product)

    g = ["state_norm", "dist_norm"]
    total = inv.groupby(g)["QTY"].sum().rename("total_sale")
    month = inv[inv["month_period"] == latest_period].groupby(g)["QTY"].sum().rename("month_sale")
    avg6  = inv[inv["month_period"].isin(last6)].groupby(g)["QTY"].sum().rename("avg_6m")
    gg_t  = inv[inv["bucket"] == "GG"].groupby(g)["QTY"].sum().rename("gg_total")
    ig_t  = inv[inv["bucket"] == "IG"].groupby(g)["QTY"].sum().rename("ig_total")
    gg_a  = inv[(inv["bucket"] == "GG") & inv["month_period"].isin(last6)].groupby(g)["QTY"].sum().rename("gg_avg")
    ig_a  = inv[(inv["bucket"] == "IG") & inv["month_period"].isin(last6)].groupby(g)["QTY"].sum().rename("ig_avg")

    agg = pd.concat([total, month, avg6, gg_t, ig_t, gg_a, ig_a], axis=1).fillna(0).reset_index()
    agg = agg.rename(columns={"state_norm": "state", "dist_norm": "district"})

    unmatched = (
        inv[["STATE", "DISTRICT_RAW", "state_norm", "dist_norm"]]
        .drop_duplicates()
        .rename(columns={"STATE": "state_raw", "DISTRICT_RAW": "district_raw"})
        .reset_index(drop=True)
    )

    # Monthly state-level series (for the simple trend forecast) — state level
    # gives more data points per series than per-district would.
    monthly_state = (
        inv.groupby(["state_norm", "month_period"])["QTY"].sum()
        .reset_index().rename(columns={"state_norm": "state", "month_period": "month"})
    )
    monthly_state["month"] = monthly_state["month"].astype(str)

    return agg, month_name, unmatched, row_count, monthly_state


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading data…")
def load_all(_ts):
    """_ts is a tuple of file mtimes; changing it busts the cache."""

    # ── Census workbook (district identity + population, always the source) ──
    raw = pd.read_excel(FILES["census"])
    raw.columns = [str(c).strip() for c in raw.columns]

    state_alias, dist_alias = effective_alias_maps()

    # ── Sales figures: prefer an admin-uploaded raw invoice file if present,
    #    otherwise fall back to the pre-built sale columns in the census sheet.
    invoice_agg, invoice_month, invoice_unmatched, invoice_rows, invoice_monthly_state = compute_invoice_sales(
        SALES_SOURCE_FILE, state_alias, dist_alias
    )
    using_invoice_data = invoice_agg is not None

    if using_invoice_data:
        month_name = invoice_month
        core = raw[["District code","State name","District name","Population",
                    "KRM","KRO","JN. KRO","Responsible"]].copy()
        core.columns = ["dist_code","state","district","population",
                        "krm","kro","jn_kro","responsible"]
    else:
        # The "current month" sale column's header changes every time the
        # sheet is refreshed (e.g. "June Sale" → "July Sale"). Detect it by
        # pattern so the dashboard doesn't break every month.
        month_col, month_name = find_month_sale_column(raw.columns)
        if month_col is None:
            st.error(
                "⚠️ Couldn't find a monthly sale column (expected something like "
                f"'June Sale' or 'July Sale') in **{FILES['census']}**, and no "
                "sales data file has been uploaded.\n\n"
                f"Columns found: {', '.join(raw.columns)}"
            )
            st.stop()

        core = raw[["District code","State name","District name","Population",
                    "KRM","KRO","JN. KRO","Responsible",
                    "Total Sale","last 6 month avg.", month_col,
                    "GG TOTAL SALE","GG AVERAGE OF 6 MONTH",
                    "IG TOTAL SALE","IG AVERAGE OF 6 MONTH"]].copy()

        core.columns = ["dist_code","state","district","population",
                        "krm","kro","jn_kro","responsible",
                        "total_sale","avg_6m","month_sale",
                        "gg_total","gg_avg","ig_total","ig_avg"]

    # Drop any fully-blank trailing rows in the census sheet (no state/district)
    core = core.dropna(subset=["state","district"]).copy()

    core["state"]    = core["state"].str.strip().str.upper()
    core["district"] = core["district"].str.strip().str.upper()
    core["population"] = pd.to_numeric(core["population"], errors="coerce").fillna(0).astype(int)

    for col in ["krm","kro","jn_kro","responsible"]:
        core[col] = core[col].fillna("").str.strip().str.upper()
        core[col] = core[col].replace("", None)

    sale_cols = ["total_sale","avg_6m","month_sale","gg_total","gg_avg","ig_total","ig_avg"]
    if using_invoice_data:
        # Population/KRM/etc. stay keyed on the census district; sales figures
        # are looked up (auto-matched) from the invoice aggregation by the
        # same (state, district) key — districts with no invoices get 0s.
        core = core.merge(invoice_agg, on=["state","district"], how="left")
        for col in sale_cols:
            core[col] = pd.to_numeric(core[col], errors="coerce").fillna(0)
    else:
        for col in sale_cols:
            core[col] = pd.to_numeric(core[col], errors="coerce")

    # ── Custom columns ────────────────────────────────────────
    try:
        custom = pd.read_csv(FILES["custom"])
        if "dist_code" in custom.columns:
            core = core.merge(custom, on="dist_code", how="left")
    except Exception:
        pass

    # ── Active districts ──────────────────────────────────────
    act = pd.read_excel(FILES["active"], header=None)
    act.columns = ["a","b","state_raw","district_raw"]
    act = act.dropna(subset=["state_raw","district_raw"])
    act = act[act["state_raw"].astype(str).str.strip() != "STATE"].copy()
    act["state_raw"]    = act["state_raw"].str.strip().str.upper()
    act["district_raw"] = act["district_raw"].str.strip().str.upper()
    act["state_norm"]   = act["state_raw"].map(lambda s: state_alias.get(s, s))
    act["dist_norm"]    = act["district_raw"].map(lambda d: dist_alias.get(d, d))
    act = act[~act["dist_norm"].isin(["_SKIP_"])]

    active_set = set(
        act.apply(lambda r: (r["state_norm"], r["dist_norm"]), axis=1)
    )

    # ── Diagnostics: rows (from either the active-district file or the
    #    uploaded sales file) whose mapped name still isn't a real census
    #    (state, district) — these need a mapping fix from the admin.
    valid_pairs = set(zip(core["state"], core["district"]))
    unmatched_mask = ~act.apply(lambda r: (r["state_norm"], r["dist_norm"]) in valid_pairs, axis=1)
    unmatched_active = (
        act[unmatched_mask][["state_raw","district_raw","state_norm","dist_norm"]]
        .drop_duplicates().reset_index(drop=True)
    )
    unmatched_active["source"] = "Active-District File"

    if using_invoice_data and invoice_unmatched is not None and not invoice_unmatched.empty:
        inv_mask = ~invoice_unmatched.apply(lambda r: (r["state_norm"], r["dist_norm"]) in valid_pairs, axis=1)
        unmatched_sales = invoice_unmatched[inv_mask].drop_duplicates().reset_index(drop=True)
        unmatched_sales["source"] = "Sales Data File"
    else:
        unmatched_sales = pd.DataFrame(columns=["state_raw","district_raw","state_norm","dist_norm","source"])

    unmatched_locations = pd.concat([unmatched_active, unmatched_sales], ignore_index=True) \
        .drop_duplicates(subset=["state_raw","district_raw"]).reset_index(drop=True)

    # ── Determine included states (all states with KRM OR active presence) ──
    krm_states = set(core[core["krm"].notna()]["state"].unique())
    active_states = {s for s, d in active_set}
    include = krm_states | active_states
    df = core[core["state"].isin(include)].copy()

    # ── Tag presence ──────────────────────────────────────────
    df["status"] = df.apply(
        lambda r: "ACTIVE" if (r["state"], r["district"]) in active_set else "NO PRESENCE",
        axis=1
    )

    # ── Display helpers ───────────────────────────────────────
    df["state_label"]    = df["state"].map(lambda s: STATE_LABELS.get(s, s.title()))
    df["district_title"] = df["district"].str.title()
    df["pop_fmt"]        = df["population"].apply(lambda x: f"{x:,}")
    df["pop_lakh"]       = (df["population"] / 1e5).round(2)
    df["lat"]            = df.apply(lambda r: get_coords(r["district"], r["state"])[0], axis=1)
    df["lon"]            = df.apply(lambda r: get_coords(r["district"], r["state"])[1], axis=1)
    df["krm_display"]    = df["krm"].fillna("UNASSIGNED")

    # Full canonical (state, district) list from the census file — used to
    # populate the admin mapping dropdowns, independent of `include` above.
    census_districts = core[["state","district"]].drop_duplicates().reset_index(drop=True)

    sales_source_info = {
        "using_invoice_data": using_invoice_data,
        "invoice_rows": invoice_rows,
        "monthly_state": invoice_monthly_state if using_invoice_data else None,
    }

    return df, month_name, unmatched_locations, census_districts, sales_source_info

def get_ts():
    return tuple(file_mtime(f) for f in FILES.values()) + (file_mtime(ALIAS_FILE), file_mtime(SALES_SOURCE_FILE))

# ─────────────────────────────────────────────────────────────────────────────
# SMART SEARCH INDEX
# ─────────────────────────────────────────────────────────────────────────────
def build_search_index(df):
    rows = []
    # KRM
    for name in df["krm"].dropna().unique():
        states = df[df["krm"]==name]["state_label"].unique()
        dists  = df[df["krm"]==name]["district_title"].unique()
        rows.append({"name": name, "role": "KRM",
                     "detail": f"{len(dists)} districts · " + ", ".join(sorted(states)),
                     "filter_col": "krm", "filter_val": name})
    # KRO
    for name in df["kro"].dropna().unique():
        dists = df[df["kro"]==name]["district_title"].unique()
        rows.append({"name": name, "role": "KRO",
                     "detail": f"{len(dists)} district(s): " + ", ".join(sorted(dists)),
                     "filter_col": "kro", "filter_val": name})
    # JR.KRO
    for name in df["jn_kro"].dropna().unique():
        dists = df[df["jn_kro"]==name]["district_title"].unique()
        rows.append({"name": name, "role": "JR.KRO",
                     "detail": f"{len(dists)} district(s): " + ", ".join(sorted(dists)),
                     "filter_col": "jn_kro", "filter_val": name})
    # Responsible
    for name in df["responsible"].dropna().unique():
        dists = df[df["responsible"]==name]["district_title"].unique()
        rows.append({"name": name, "role": "RESPONSIBLE",
                     "detail": f"{len(dists)} district(s): " + ", ".join(sorted(dists)),
                     "filter_col": "responsible", "filter_val": name})
    # Districts
    for _, row in df[["district","district_title","state_label"]].drop_duplicates("district").iterrows():
        rows.append({"name": row["district_title"], "role": "DISTRICT",
                     "detail": row["state_label"],
                     "filter_col": "district", "filter_val": row["district"]})
    # States
    for sl in df["state_label"].unique():
        rows.append({"name": sl, "role": "STATE",
                     "detail": f"{df[df['state_label']==sl]['district'].nunique()} districts",
                     "filter_col": "state_label", "filter_val": sl})
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def dashboard():
    # ── Auto-refresh mtime check ──────────────────────────────
    ts = get_ts()
    if st.session_state.get("last_ts") != ts:
        st.session_state["last_ts"] = ts
        st.cache_data.clear()

    df, month_name, unmatched_locations, census_districts, sales_source_info = load_all(ts)
    srch_idx= build_search_index(df)
    teams   = load_teams()
    is_admin= st.session_state.get("user","").lower() == "sudipta"

    # ── SESSION: search jump state ────────────────────────────
    if "jump_filter" not in st.session_state:
        st.session_state["jump_filter"] = {}  # {col: val}

    # ── SIDEBAR ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user'].title()}")
        st.caption(f"Logged in: {st.session_state.get('login_time','')}")
        st.markdown("---")

        # ════════════════════════════════════════════════════
        # FILTERS
        # ════════════════════════════════════════════════════
        st.markdown("### 🔍 Filters")

        presence_icons = {
            "All": "🌐 All Districts",
            "ACTIVE": "✅ Active Only",
            "NO PRESENCE": "🔴 No Presence",
        }
        sel_presence = st.radio("📍 Presence", list(presence_icons.keys()),
                                format_func=lambda x: presence_icons[x])

        states_avail  = ["All States"] + sorted(df["state_label"].unique())
        sel_state     = st.selectbox("🏛 State", states_avail)

        krm_avail     = ["All KRMs"] + sorted([k for k in df["krm_display"].unique() if k != "UNASSIGNED"])
        sel_krm       = st.selectbox("👤 KRM", krm_avail)

        kro_avail     = ["All KROs"] + sorted([k for k in df["kro"].dropna().unique()])
        sel_kro       = st.selectbox("🧑‍💼 KRO", kro_avail)

        jrkro_avail   = ["All JR.KROs"] + sorted([k for k in df["jn_kro"].dropna().unique()])
        sel_jrkro     = st.selectbox("👶 JR.KRO", jrkro_avail)

        team_opts = ["— All / No Team —"] + sorted(teams.keys())
        sel_team  = st.selectbox("🧑‍💼 Sales Backend Team", team_opts, key="team_jump_select")

        # District depends on above
        pool = df.copy()
        if sel_presence != "All":        pool = pool[pool["status"]       == sel_presence]
        if sel_state    != "All States": pool = pool[pool["state_label"]  == sel_state]
        if sel_krm      != "All KRMs":  pool = pool[pool["krm_display"]  == sel_krm]
        if sel_kro      != "All KROs":  pool = pool[pool["kro"]          == sel_kro]
        if sel_jrkro    != "All JR.KROs":pool = pool[pool["jn_kro"]      == sel_jrkro]
        dist_avail = ["All Districts"] + sorted(pool["district_title"].unique())
        sel_dist   = st.selectbox("🏙 District", dist_avail)

        st.markdown("---")
        st.markdown("### ⚙️ Map")
        map_color = st.radio("Color by", ["Presence Status","KRM Territory","Population"])
        map_style = st.selectbox("Base map", ["carto-positron","open-street-map","carto-darkmatter"])
        show_lbl  = st.toggle("Labels on map", value=False)

        st.markdown("---")
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.session_state["last_ts"] = ()
            st.rerun()
        auto = st.toggle("Auto-refresh 30s", value=False)

    # ── TOP HEADER: last update (left) · Smart Search + Login/Logout (right) ──
    hdr_l, hdr_r1, hdr_r2 = st.columns([3, 1.3, 1])
    with hdr_l:
        st.markdown(
            f'<div style="font-size:13px;color:#555;padding-top:12px;">'
            f'🕒 <b>Last data update (IST):</b> {get_last_update_str()}</div>',
            unsafe_allow_html=True,
        )
    with hdr_r1:
        with st.popover("🔍 Smart Search", use_container_width=True):
            st.caption("Search KRM · KRO · JR.KRO · District · State")
            query = st.text_input("", placeholder="Type name or place…", label_visibility="collapsed", key="global_search")

            if query and len(query.strip()) >= 2:
                mask = srch_idx["name"].str.contains(query.strip(), case=False, na=False)
                results = srch_idx[mask].head(12)
                if results.empty:
                    st.caption("No results found.")
                else:
                    for _, r in results.iterrows():
                        label = f"[{r['role']}]  {r['name']}"
                        if st.button(label, key=f"sr_{r['role']}_{r['name']}", use_container_width=True):
                            st.session_state["jump_filter"] = {
                                r["filter_col"]: r["filter_val"]
                            }
                            st.session_state["global_search"] = ""
                            st.rerun()
                        st.caption(r["detail"])

            if st.session_state["jump_filter"]:
                jf_disp = st.session_state["jump_filter"]
                jval_disp = list(jf_disp.values())[0]
                st.markdown(
                    f'<div style="background:#e8f0fe;border-radius:8px;padding:6px 10px;'
                    f'font-size:11px;color:#1a73e8;margin-top:4px;">'
                    f'🎯 Showing: <b>{jval_disp}</b></div>', unsafe_allow_html=True
                )
                if st.button("✖ Clear search filter", use_container_width=True):
                    st.session_state["jump_filter"] = {}
                    st.rerun()
    with hdr_r2:
        with st.popover(f"👤 {st.session_state['user'].title()}", use_container_width=True):
            st.caption(f"Logged in: {st.session_state.get('login_time','')}")
            if st.button("🚪 Logout", use_container_width=True, key="logout_top"):
                st.session_state.clear(); st.rerun()

    # ── Build final filter ────────────────────────────────────
    jf  = st.session_state.get("jump_filter", {})
    flt = df.copy()

    # Apply jump filter first (from search click)
    for col, val in jf.items():
        if col in flt.columns:
            flt = flt[flt[col].astype(str).str.upper() == str(val).upper()]

    # Then sidebar filters
    if sel_presence != "All":          flt = flt[flt["status"]       == sel_presence]
    if sel_state    != "All States":   flt = flt[flt["state_label"]  == sel_state]
    if sel_krm      != "All KRMs":    flt = flt[flt["krm_display"]  == sel_krm]
    if sel_kro      != "All KROs":    flt = flt[flt["kro"]          == sel_kro]
    if sel_jrkro    != "All JR.KROs": flt = flt[flt["jn_kro"]       == sel_jrkro]
    if sel_dist     != "All Districts":flt = flt[flt["district_title"]== sel_dist]

    # Sales Backend Team slicer (state/district mapping set by admin)
    if sel_team != "— All / No Team —":
        t_info  = teams.get(sel_team, {})
        t_states= set(t_info.get("states", []))
        t_dists = set(t_info.get("districts", []))
        if t_states or t_dists:
            flt = flt[flt["state"].isin(t_states) | flt["district"].isin(t_dists)]
        else:
            flt = flt.iloc[0:0]

    # ── Auto-refresh ──────────────────────────────────────────
    if auto:
        import time; time.sleep(30); st.rerun()

    # ═══════════════════════════════════════════════════════════
    # TOP SECTION — HMB PRESENCE MAP
    # ═══════════════════════════════════════════════════════════
    map_col, cov_col = st.columns([3, 1])

    with map_col:
        st.markdown('<div class="sec">🗺️ HMB Presence Map</div>', unsafe_allow_html=True)
        fig_top = go.Figure()

        # Auto-enable district labels when a single state is drilled into,
        # so the full state + all its districts are clearly visible.
        effective_show_lbl = show_lbl or (sel_state != "All States")
        hover_fields = flt[["district_title","state_label","krm_display","kro","jn_kro","responsible"]] \
            .fillna("—").values

        if map_color == "Presence Status":
            for status, color in [("ACTIVE","#34A853"),("NO PRESENCE","#EA4335")]:
                g = flt[flt["status"]==status]
                if g.empty: continue
                fig_top.add_trace(go.Scattermapbox(
                    lat=g["lat"], lon=g["lon"],
                    mode="markers+text" if effective_show_lbl else "markers",
                    marker=dict(size=11, color=color, opacity=0.85),
                    text=g["district_title"] if effective_show_lbl else None,
                    textposition="top center", textfont=dict(size=8,color="#222"),
                    name=status,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>State: %{customdata[1]}<br>"
                        "KRM: %{customdata[2]}<br>KRO: %{customdata[3]}<br>"
                        "JR.KRO: %{customdata[4]}<br>Responsible: %{customdata[5]}"
                        "<extra></extra>"
                    ),
                    customdata=g[["district_title","state_label","krm_display","kro","jn_kro","responsible"]].fillna("—").values,
                ))
        elif map_color == "KRM Territory":
            for krm_name, g in flt.groupby("krm_display"):
                color = KRM_COLORS.get(krm_name, "#B0BEC5")
                fig_top.add_trace(go.Scattermapbox(
                    lat=g["lat"], lon=g["lon"],
                    mode="markers+text" if effective_show_lbl else "markers",
                    marker=dict(size=10, color=color, opacity=0.85),
                    text=g["district_title"] if effective_show_lbl else None,
                    textposition="top center", textfont=dict(size=8,color="#222"),
                    name=krm_name,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>State: %{customdata[1]}<br>"
                        "KRM: <b>%{customdata[2]}</b><br>KRO: %{customdata[3]}<br>"
                        "JR.KRO: %{customdata[4]}<br>Responsible: %{customdata[5]}"
                        "<extra></extra>"
                    ),
                    customdata=g[["district_title","state_label","krm_display","kro","jn_kro","responsible"]].fillna("—").values,
                ))
        else:
            import plotly.colors as pc
            smax = flt["population"].max() if not flt.empty else 1
            nc   = pc.sample_colorscale(pc.sequential.YlOrRd,
                   (flt["population"]/(smax or 1)).clip(0,1).fillna(0).tolist())
            sizes= (flt["population"]/(smax or 1)*16+5).clip(5,21)
            fig_top.add_trace(go.Scattermapbox(
                lat=flt["lat"], lon=flt["lon"],
                mode="markers+text" if effective_show_lbl else "markers",
                marker=dict(size=sizes.tolist(), color=nc, opacity=0.85),
                text=flt["district_title"] if effective_show_lbl else None,
                textposition="top center", textfont=dict(size=8,color="#222"),
                name="Population",
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>State: %{customdata[1]}<br>"
                    "KRM: %{customdata[2]}<br>KRO: %{customdata[3]}<br>"
                    "JR.KRO: %{customdata[4]}<br>Responsible: %{customdata[5]}"
                    "<extra></extra>"
                ),
                customdata=flt[["district_title","state_label","krm_display","kro","jn_kro","responsible"]].fillna("—").values,
            ))

        zoom, clat, clon = 4.2, 23.5, 84.0
        if sel_state != "All States":
            # Center on the mean of the state's own districts (tighter & more
            # accurate than the static state centroid) so the full state map
            # with all its districts fills the view.
            if not flt.empty:
                clat, clon = float(flt["lat"].mean()), float(flt["lon"].mean())
            else:
                sk = [k for k,v in STATE_LABELS.items() if v==sel_state]
                if sk and sk[0] in STATE_CENTROIDS:
                    clat,clon = STATE_CENTROIDS[sk[0]]
            zoom = 6.8
        if sel_dist != "All Districts" and not flt.empty:
            clat,clon = float(flt["lat"].mean()),float(flt["lon"].mean()); zoom=9.0

        fig_top.update_layout(
            mapbox=dict(style=map_style,zoom=zoom,center=dict(lat=clat,lon=clon)),
            legend=dict(bgcolor="rgba(255,255,255,.92)",bordercolor="#ddd",
                        borderwidth=1,font=dict(size=11),x=0.01,y=0.99),
            margin=dict(l=0,r=0,t=0,b=0), height=520,
        )
        st.plotly_chart(fig_top, use_container_width=True)
        cap = "🟢 Active  ·  🔴 No Presence  ·  Hover for KRM / KRO / JR.KRO / Responsible"
        if sel_state != "All States":
            cap += f"  ·  📍 Zoomed to **{sel_state}** — all districts labeled"
        st.caption(cap)

    with cov_col:
        st.markdown('<div class="sec">Coverage</div>', unsafe_allow_html=True)
        sp = flt.groupby(["state_label","status"]).size().unstack(fill_value=0).reset_index()
        for c in ["ACTIVE","NO PRESENCE"]:
            if c not in sp.columns: sp[c]=0
        for _, row in sp.iterrows():
            a=int(row.get("ACTIVE",0)); np2=int(row.get("NO PRESENCE",0))
            tot=a+np2; p2=int(a/tot*100) if tot else 0
            bc="#34A853" if p2>=60 else "#FBBC04" if p2>=30 else "#EA4335"
            st.markdown(html_block(f"""
            <div class="cov-row">
              <div style="font-weight:700;font-size:12px;">{row['state_label']}</div>
              <div style="display:flex;justify-content:space-between;font-size:10px;color:#666;margin:3px 0;">
                <span>✅{a} &nbsp;🔴{np2}</span>
                <span style="color:{bc};font-weight:700;">{p2}%</span>
              </div>
              <div class="cov-bar-bg">
                <div style="background:{bc};width:{p2}%;height:5px;border-radius:5px;"></div>
              </div>
            </div>"""), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Banner ────────────────────────────────────────────────
    active_n = int((flt["status"]=="ACTIVE").sum())
    nopres_n = int((flt["status"]=="NO PRESENCE").sum())
    total    = len(flt)
    pct_cov  = safe_div(active_n, total)
    total_sale = flt["total_sale"].sum()
    avg_sale   = flt["avg_6m"].sum()

    st.markdown(html_block(f"""
    <div class="top-banner">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div class="banner-title">🇮🇳 HMB Presence & Sales Dashboard</div>
          <div class="banner-sub">
            {sel_state} &nbsp;·&nbsp; {sel_krm} &nbsp;·&nbsp;
            {sel_kro} &nbsp;·&nbsp; {sel_jrkro} &nbsp;·&nbsp;
            <b style="color:#ffd54f">{presence_icons[sel_presence]}</b>
            {f'&nbsp;·&nbsp; 🧑‍💼 Team: <b style="color:#a5d6a7">{sel_team}</b>' if sel_team != "— All / No Team —" else ""}
          </div>
        </div>
        <div style="text-align:right;color:#90cdf4;font-size:12px;line-height:1.9;">
          {flt['state_label'].nunique()} States &nbsp;|&nbsp;
          {total} Districts &nbsp;|&nbsp;
          Pop: <b style="color:#fff">{flt['population'].sum()/1e7:.2f} Cr</b><br>
          Total Sale: <b style="color:#ffd54f">{fmt_mt(total_sale)}</b> &nbsp;|&nbsp;
          6M Avg: <b style="color:#a5d6a7">{fmt_mt(avg_sale)}</b>
        </div>
      </div>
    </div>"""), unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    kpis = [
        (str(total),          "Total Districts",     "#4285F4"),
        (str(active_n),       "✅ Active",           "#34A853"),
        (str(nopres_n),       "🔴 No Presence",      "#EA4335"),
        (f"{pct_cov}%",       "Coverage",            "#FBBC04"),
        (fmt_mt(total_sale),  "Total Sale",          "#9C27B0"),
        (fmt_mt(avg_sale),    "6-Month Avg",         "#00BCD4"),
    ]
    for col,(val,lbl,clr) in zip([k1,k2,k3,k4,k5,k6],kpis):
        col.markdown(
            f'<div class="kpi-box" style="--c:{clr};">'
            f'<div class="kpi-val">{val}</div>'
            f'<div class="kpi-label">{lbl}</div></div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # TABS
    # ═══════════════════════════════════════════════════════════
    tab_names = [
        "📊 Live Dashboard",
        "📍 Presence Analysis",
        "📦 Product Sales",
        "👥 Team View",
        "📋 Data Table (Sales Backend Team)",
    ]
    if is_admin:
        tab_names.append("🛠️ Sales Backend Teams (Admin)")
        tab_names.append("🧭 Location Mapping (Admin)")
        tab_names.append("📤 Sales Data (Admin)")

    _tabs = st.tabs(tab_names)
    tab_live, tab_pres, tab_sales, tab_team, tab_table = _tabs[:5]
    tab_admin   = _tabs[5] if is_admin else None
    tab_mapping = _tabs[6] if is_admin else None
    tab_sales_up= _tabs[7] if is_admin else None

    # ═══════════════════════════════════════════════════════════
    # TAB 1 — LIVE DASHBOARD (Power-BI style)
    # ═══════════════════════════════════════════════════════════
    with tab_live:
        st.markdown('<div class="sec">📊 Live Overview</div>', unsafe_allow_html=True)

        # Row 1: State performance
        r1a, r1b = st.columns([2, 1])

        with r1a:
            st.markdown('<div class="sec">State-wise Sales</div>', unsafe_allow_html=True)
            state_sale = (
                flt.groupby("state_label")
                .agg(Total_Sale=("total_sale","sum"),
                     Avg_6M=("avg_6m","sum"),
                     Month_Sale=("month_sale","sum"),
                     Districts=("district","count"),
                     Active=("status", lambda x:(x=="ACTIVE").sum()))
                .reset_index().sort_values("Total_Sale", ascending=True)
            )
            state_sale["Coverage%"] = state_sale.apply(
                lambda r: safe_div(r["Active"],r["Districts"]), axis=1)

            fig_ss = go.Figure()
            fig_ss.add_trace(go.Bar(
                y=state_sale["state_label"], x=state_sale["Total_Sale"],
                orientation="h", name="Total Sale",
                marker_color="#4285F4", opacity=0.9,
                text=state_sale["Total_Sale"].map(lambda v: f"{v:,.0f} MT" if pd.notna(v) and v>0 else ""),
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Total: %{x:.1f} MT<extra></extra>",
            ))
            fig_ss.add_trace(go.Bar(
                y=state_sale["state_label"], x=state_sale["Month_Sale"],
                orientation="h", name=f"{month_name} Sale",
                marker_color="#34A853", opacity=0.85,
                hovertemplate=f"<b>%{{y}}</b><br>{month_name}: %{{x:.1f}} MT<extra></extra>",
            ))
            fig_ss.update_layout(
                barmode="group", height=340,
                legend=dict(orientation="h",x=0,y=1.08,title=""),
                margin=dict(l=5,r=80,t=40,b=5),
                plot_bgcolor="#fafafa",
                xaxis_title="Sales (MT)",
            )
            st.plotly_chart(fig_ss, use_container_width=True)

        with r1b:
            st.markdown('<div class="sec">Coverage Scorecard</div>', unsafe_allow_html=True)
            for _, row in state_sale.sort_values("Coverage%",ascending=False).iterrows():
                pct2 = row["Coverage%"]
                bar_c = "#34A853" if pct2 >= 60 else "#FBBC04" if pct2 >= 30 else "#EA4335"
                sale_str = f"{row['Total_Sale']:,.1f} MT" if pd.notna(row['Total_Sale']) and row['Total_Sale']>0 else "—"
                st.markdown(html_block(f"""
                <div class="cov-row">
                  <div style="display:flex;justify-content:space-between;">
                    <span style="font-weight:700;font-size:12px;">{row['state_label']}</span>
                    <span style="font-size:11px;color:#666;">{sale_str}</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;font-size:10px;color:#888;margin:2px 0;">
                    <span>✅{int(row['Active'])} / {int(row['Districts'])}</span>
                    <span style="color:{bar_c};font-weight:700;">{pct2}%</span>
                  </div>
                  <div class="cov-bar-bg">
                    <div style="background:{bar_c};width:{pct2}%;height:5px;border-radius:5px;"></div>
                  </div>
                </div>"""), unsafe_allow_html=True)

        # Row 2: District top/bottom + trend
        r2a, r2b, r2c = st.columns(3)

        with r2a:
            st.markdown('<div class="sec">🏆 Top 10 Districts by Sale</div>', unsafe_allow_html=True)
            top10 = flt.nlargest(10, "total_sale")[["district_title","state_label","total_sale","krm_display"]]
            fig_t10 = px.bar(
                top10.sort_values("total_sale"),
                x="total_sale", y="district_title", orientation="h",
                color="krm_display", color_discrete_map=KRM_COLORS,
                labels={"district_title":"","total_sale":"Sale (MT)","krm_display":"KRM"},
                height=340, text="total_sale",
            )
            fig_t10.update_traces(texttemplate="%{text:.0f} MT", textposition="outside")
            fig_t10.update_layout(showlegend=False, margin=dict(l=5,r=60,t=10,b=5))
            st.plotly_chart(fig_t10, use_container_width=True)

        with r2b:
            st.markdown('<div class="sec">📦 GG vs IG Sales</div>', unsafe_allow_html=True)
            gg_tot = flt["gg_total"].sum()
            ig_tot = flt["ig_total"].sum()
            if gg_tot > 0 or ig_tot > 0:
                fig_pie = go.Figure(go.Pie(
                    labels=["GG Total","IG Total"],
                    values=[gg_tot, ig_tot],
                    hole=0.45,
                    marker_colors=["#4285F4","#EA4335"],
                ))
                fig_pie.update_layout(height=200,margin=dict(l=5,r=5,t=10,b=5),
                                      showlegend=True,
                                      legend=dict(orientation="h",x=0,y=-0.1))
                st.plotly_chart(fig_pie, use_container_width=True)
                c1,c2 = st.columns(2)
                c1.metric("GG Total", f"{gg_tot:,.1f} MT")
                c2.metric("IG Total", f"{ig_tot:,.1f} MT")
            else:
                st.info("No GG/IG sales data in current filter.")

        with r2c:
            st.markdown(f'<div class="sec">📉 {month_name} vs 6M Avg</div>', unsafe_allow_html=True)
            comp = flt[flt["total_sale"].notna()][["district_title","month_sale","avg_6m"]].copy()
            comp = comp.dropna(subset=["month_sale","avg_6m"]).nlargest(12,"avg_6m")
            if not comp.empty:
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Bar(
                    x=comp["district_title"], y=comp["avg_6m"],
                    name="6M Avg", marker_color="#90CAF9",
                ))
                fig_comp.add_trace(go.Bar(
                    x=comp["district_title"], y=comp["month_sale"],
                    name=f"{month_name} Sale", marker_color="#1565C0",
                ))
                fig_comp.update_layout(
                    barmode="group", height=240,
                    margin=dict(l=5,r=5,t=10,b=60),
                    xaxis_tickangle=-45,
                    legend=dict(orientation="h",x=0,y=1.1),
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.info("No monthly data available.")

        # Row 3: KRM performance table
        st.markdown('<div class="sec">👤 KRM Performance Summary</div>', unsafe_allow_html=True)
        krm_perf = (
            flt[flt["krm_display"] != "UNASSIGNED"]
            .groupby("krm_display")
            .agg(
                Districts=("district","count"),
                Active=("status",lambda x:(x=="ACTIVE").sum()),
                Total_Sale=("total_sale","sum"),
                Avg_6M=("avg_6m","sum"),
                Month_Sale=("month_sale","sum"),
                GG_Total=("gg_total","sum"),
                IG_Total=("ig_total","sum"),
                States=("state_label",lambda x:", ".join(sorted(set(x)))),
            ).reset_index()
        )
        krm_perf["Coverage%"] = krm_perf.apply(
            lambda r: safe_div(r["Active"],r["Districts"]),axis=1)
        krm_perf["vs_avg"] = krm_perf.apply(
            lambda r: safe_div(r["Month_Sale"],r["Avg_6M"]/6) - 100
            if pd.notna(r["Avg_6M"]) and r["Avg_6M"]>0 else None, axis=1)

        st.dataframe(
            krm_perf.rename(columns={
                "krm_display":"KRM","Districts":"Dists","Active":"✅Active",
                "Total_Sale":"Total (MT)","Avg_6M":"6M Avg (MT)","Month_Sale":f"{month_name} (MT)",
                "GG_Total":"GG (MT)","IG_Total":"IG (MT)","Coverage%":"Cover%",
                "vs_avg":"vs Avg%","States":"States"
            }).sort_values("Total (MT)",ascending=False),
            use_container_width=True, height=250,
        )

    # ═══════════════════════════════════════════════════════════
    # TAB 3 — PRESENCE ANALYSIS
    # ═══════════════════════════════════════════════════════════
    with tab_pres:
        st.markdown('<div class="sec">Active vs No-Presence Breakdown</div>', unsafe_allow_html=True)
        full = df.copy()  # unfiltered for overview
        p1, p2 = st.columns(2)

        with p1:
            pres_df = full.groupby(["state_label","status"]).size().reset_index(name="count")
            fig_p = px.bar(pres_df, x="count", y="state_label", color="status",
                           orientation="h", barmode="stack",
                           color_discrete_map={"ACTIVE":"#34A853","NO PRESENCE":"#EA4335"},
                           title="All States — Active vs No-Presence",
                           text="count", height=400,
                           labels={"state_label":"State","count":"Districts"})
            fig_p.update_traces(textposition="inside",insidetextanchor="middle")
            fig_p.update_layout(yaxis=dict(categoryorder="total ascending"),
                                legend=dict(orientation="h",y=1.08,x=0,title=""),
                                margin=dict(l=5,r=10,t=50,b=5))
            st.plotly_chart(fig_p, use_container_width=True)

        with p2:
            cov = (full.groupby("state_label")
                   .apply(lambda g: round(len(g[g["status"]=="ACTIVE"])/len(g)*100,1))
                   .reset_index(name="Cov%").sort_values("Cov%"))
            colors=[("#34A853" if v>=60 else "#FBBC04" if v>=30 else "#EA4335") for v in cov["Cov%"]]
            fig_c = go.Figure(go.Bar(
                x=cov["Cov%"],y=cov["state_label"],orientation="h",marker_color=colors,
                text=cov["Cov%"].map(lambda v:f"{v}%"),textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x}%<extra></extra>",
            ))
            fig_c.add_vline(x=50,line_dash="dash",line_color="#888",annotation_text="50%")
            fig_c.update_layout(title="Coverage % by State",xaxis=dict(range=[0,115]),
                                height=400,showlegend=False,margin=dict(l=5,r=60,t=50,b=5))
            st.plotly_chart(fig_c, use_container_width=True)

        # No-Presence detail
        st.markdown('<div class="sec">🔴 No-Presence Districts</div>', unsafe_allow_html=True)
        np_df = df[df["status"]=="NO PRESENCE"].copy()
        f1,f2,f3 = st.columns(3)
        np_st  = f1.selectbox("State",  ["All"]+sorted(np_df["state_label"].unique()), key="np_st")
        np_krm = f2.selectbox("KRM",    ["All"]+sorted([k for k in np_df["krm_display"].unique() if k!="UNASSIGNED"]), key="np_krm")
        np_srch= f3.text_input("Search district", placeholder="Type…", key="np_srch")

        np_flt = np_df.copy()
        if np_st  !="All": np_flt=np_flt[np_flt["state_label"]==np_st]
        if np_krm !="All": np_flt=np_flt[np_flt["krm_display"]==np_krm]
        if np_srch: np_flt=np_flt[np_flt["district_title"].str.contains(np_srch,case=False,na=False)]

        st.caption(f"🔴 **{len(np_flt)} no-presence districts**")
        for sl, grp in np_flt.groupby("state_label"):
            kn = grp["krm_display"].iloc[0]
            kc = KRM_COLORS.get(kn,"#B0BEC5")
            pills="".join(
                f'<span style="background:#fce8e6;color:#c5221f;border-radius:14px;'
                f'padding:3px 9px;font-size:11px;font-weight:600;margin:2px;display:inline-block;">{d}</span>'
                for d in sorted(grp["district_title"])
            )
            st.markdown(html_block(f"""
            <div style="background:#fff;border-radius:10px;padding:12px 15px;
                        border-left:5px solid {kc};margin-bottom:9px;
                        box-shadow:0 1px 5px rgba(0,0,0,.07);">
              <div style="display:flex;justify-content:space-between;margin-bottom:7px;">
                <b style="font-size:13px;">{sl}</b>
                <span style="font-size:11px;color:{kc};font-weight:700;">{kn} · {len(grp)} absent</span>
              </div>{pills}</div>"""), unsafe_allow_html=True)

        st.download_button("⬇️ Download No-Presence CSV",
            data=np_flt[["state_label","district_title","krm_display","pop_fmt","status"]]
                 .rename(columns={"state_label":"State","district_title":"District",
                                  "krm_display":"KRM","pop_fmt":"Population","status":"Status"})
                 .to_csv(index=False),
            file_name="no_presence.csv", mime="text/csv")

    # ═══════════════════════════════════════════════════════════
    # TAB 4 — PRODUCT SALES  (GG / IG)
    # ═══════════════════════════════════════════════════════════
    with tab_sales:
        st.markdown('<div class="sec">📦 Product-wise Sales — GG &amp; IG</div>', unsafe_allow_html=True)

        has_sales = flt["total_sale"].notna() & (flt["total_sale"]>0)
        sales_df  = flt[has_sales].copy()

        if sales_df.empty:
            st.info("No sales data in current filter. Adjust slicers or check Excel data.")
        else:
            s1,s2,s3,s4 = st.columns(4)
            s1.metric("Total Sale (MT)",  f"{sales_df['total_sale'].sum():,.1f}")
            s2.metric("6M Avg (MT)",      f"{sales_df['avg_6m'].sum():,.1f}")
            s3.metric(f"{month_name} Sale (MT)", f"{sales_df['month_sale'].sum():,.1f}")
            s4.metric("Districts w/ Sale", len(sales_df))

            st.markdown("<br>", unsafe_allow_html=True)
            c1,c2 = st.columns(2)

            # GG vs IG breakdown
            with c1:
                st.markdown('<div class="sec">GG vs IG — District Comparison</div>', unsafe_allow_html=True)
                prod_df = sales_df[["district_title","gg_total","ig_total"]].dropna(subset=["gg_total","ig_total"])
                prod_df = prod_df.sort_values("gg_total", ascending=True).tail(15)
                fig_gg = go.Figure()
                fig_gg.add_trace(go.Bar(
                    y=prod_df["district_title"], x=prod_df["gg_total"],
                    orientation="h", name="GG", marker_color="#4285F4",
                    text=prod_df["gg_total"].map(lambda v:f"{v:,.0f} MT"),
                    textposition="outside",
                ))
                fig_gg.add_trace(go.Bar(
                    y=prod_df["district_title"], x=prod_df["ig_total"],
                    orientation="h", name="IG", marker_color="#EA4335",
                    text=prod_df["ig_total"].map(lambda v:f"{v:,.0f} MT"),
                    textposition="outside",
                ))
                fig_gg.update_layout(
                    barmode="group", height=420,
                    yaxis=dict(categoryorder="total ascending"),
                    legend=dict(orientation="h",x=0,y=1.08,title=""),
                    margin=dict(l=5,r=80,t=40,b=5),
                )
                st.plotly_chart(fig_gg, use_container_width=True)

            with c2:
                st.markdown('<div class="sec">GG vs IG — State Totals</div>', unsafe_allow_html=True)
                st_prod = sales_df.groupby("state_label").agg(
                    GG=("gg_total","sum"), IG=("ig_total","sum"),
                    Total=("total_sale","sum")
                ).reset_index().sort_values("Total",ascending=True)
                fig_stprod = go.Figure()
                fig_stprod.add_trace(go.Bar(
                    y=st_prod["state_label"], x=st_prod["GG"],
                    orientation="h", name="GG", marker_color="#4285F4",
                ))
                fig_stprod.add_trace(go.Bar(
                    y=st_prod["state_label"], x=st_prod["IG"],
                    orientation="h", name="IG", marker_color="#EA4335",
                ))
                fig_stprod.update_layout(
                    barmode="stack", height=300,
                    legend=dict(orientation="h",x=0,y=1.08,title=""),
                    margin=dict(l=5,r=60,t=40,b=5),
                )
                st.plotly_chart(fig_stprod, use_container_width=True)

                # GG Avg vs IG Avg
                gg_avg_t = sales_df["gg_avg"].sum()
                ig_avg_t = sales_df["ig_avg"].sum()
                c2a,c2b = st.columns(2)
                c2a.metric("GG 6M Avg",f"{gg_avg_t:,.1f} MT")
                c2b.metric("IG 6M Avg",f"{ig_avg_t:,.1f} MT")

            # District-level sales table
            st.markdown('<div class="sec">📋 District Sales Detail</div>', unsafe_allow_html=True)
            sale_tbl = sales_df[[
                "state_label","district_title","krm_display","kro","jn_kro",
                "total_sale","avg_6m","month_sale","gg_total","gg_avg","ig_total","ig_avg"
            ]].rename(columns={
                "state_label":"State","district_title":"District","krm_display":"KRM",
                "kro":"KRO","jn_kro":"JR.KRO",
                "total_sale":"Total (MT)","avg_6m":"6M Avg (MT)","month_sale":f"{month_name} (MT)",
                "gg_total":"GG (MT)","gg_avg":"GG Avg (MT)","ig_total":"IG (MT)","ig_avg":"IG Avg (MT)"
            }).sort_values("Total (MT)",ascending=False).reset_index(drop=True)

            st.dataframe(sale_tbl, use_container_width=True, height=380)
            st.download_button("⬇️ Download Sales CSV",
                               data=sale_tbl.to_csv(index=False),
                               file_name="district_sales.csv", mime="text/csv")

            # ── AI Forecast (simple trend projection, only available with
            #    uploaded invoice-level data — we need real dated rows to
            #    build a month-by-month series) ──
            st.markdown("---")
            st.markdown('<div class="sec">🔮 AI Sales Forecast — Next Month (beta)</div>', unsafe_allow_html=True)
            monthly_state = sales_source_info.get("monthly_state")
            if not sales_source_info.get("using_invoice_data") or monthly_state is None or monthly_state.empty:
                st.info(
                    "Forecasting needs dated, invoice-level sales data with more than one "
                    "month of history. Upload your sales file(s) in **📤 Sales Data (Admin)** "
                    "to unlock this."
                )
            else:
                st.caption(
                    "A simple, transparent linear-trend projection per state (not a trained "
                    "ML model) — fits a straight line through each state's monthly totals and "
                    "extrapolates one month ahead. Treat it as an early-warning signal, not a "
                    "guarantee."
                )
                fc = forecast_next_month(monthly_state)
                fc_disp = fc.merge(
                    pd.Series(STATE_LABELS).rename("label"),
                    left_on="state", right_index=True, how="left"
                )
                fc_disp["label"] = fc_disp["label"].fillna(fc_disp["state"].str.title())

                fcol1, fcol2 = st.columns([2,1])
                with fcol1:
                    top_fc = fc_disp.head(15).sort_values("forecast_next")
                    fig_fc = go.Figure()
                    fig_fc.add_trace(go.Bar(
                        y=top_fc["label"], x=top_fc["last_actual"],
                        orientation="h", name="Last Actual Month", marker_color="#90CAF9",
                    ))
                    fig_fc.add_trace(go.Bar(
                        y=top_fc["label"], x=top_fc["forecast_next"],
                        orientation="h", name="Forecast — Next Month", marker_color="#FF6D00",
                    ))
                    fig_fc.update_layout(
                        barmode="group", height=420,
                        legend=dict(orientation="h", x=0, y=1.08, title=""),
                        margin=dict(l=5, r=20, t=40, b=5),
                    )
                    st.plotly_chart(fig_fc, use_container_width=True)
                with fcol2:
                    risers = fc_disp.nlargest(5, "trend_pct")[["label","trend_pct"]]
                    fallers = fc_disp.nsmallest(5, "trend_pct")[["label","trend_pct"]]
                    st.markdown("**📈 Trending Up**")
                    for _, r in risers.iterrows():
                        st.markdown(f"- {r['label']}: <span style='color:#34A853;font-weight:700;'>+{r['trend_pct']}%</span>", unsafe_allow_html=True)
                    st.markdown("**📉 Trending Down**")
                    for _, r in fallers.iterrows():
                        st.markdown(f"- {r['label']}: <span style='color:#EA4335;font-weight:700;'>{r['trend_pct']}%</span>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # TAB 5 — TEAM VIEW
    # ═══════════════════════════════════════════════════════════
    with tab_team:
        st.markdown('<div class="sec">👥 Team Hierarchy View</div>', unsafe_allow_html=True)

        # KRM summary cards
        for krm_name, kgrp in flt[flt["krm_display"]!="UNASSIGNED"].groupby("krm_display"):
            color = KRM_COLORS.get(krm_name,"#B0BEC5")
            act_k = int((kgrp["status"]=="ACTIVE").sum())
            tot_k = len(kgrp)
            sale_k= kgrp["total_sale"].sum()

            with st.expander(f"👤 {krm_name} — {tot_k} districts · {sale_k:,.1f} MT total", expanded=False):
                cm1,cm2,cm3,cm4 = st.columns(4)
                cm1.metric("Districts", tot_k)
                cm2.metric("✅ Active", act_k)
                cm3.metric("🔴 Absent", tot_k-act_k)
                cm4.metric("Total Sale", f"{sale_k:,.1f} MT")

                st.markdown("**KRO / JR.KRO breakdown:**")
                # KRO level
                kro_grp = kgrp[kgrp["kro"].notna()].groupby("kro")
                for kro_name, kro_data in kro_grp:
                    st.markdown(f"&nbsp;&nbsp;🧑‍💼 **KRO: {kro_name}** — {len(kro_data)} districts")
                    jrkro_g = kro_data[kro_data["jn_kro"].notna()].groupby("jn_kro")
                    for jr_name, jr_data in jrkro_g:
                        dists = ", ".join(jr_data["district_title"].tolist())
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;👶 JR.KRO: **{jr_name}** → {dists}")

                # Districts table for this KRM
                ktbl = kgrp[["district_title","state_label","status","total_sale","month_sale","kro","jn_kro"]].rename(
                    columns={"district_title":"District","state_label":"State",
                             "status":"Status","total_sale":"Total (MT)","month_sale":f"{month_name} (MT)",
                             "kro":"KRO","jn_kro":"JR.KRO"}
                ).sort_values("Total (MT)",ascending=False).reset_index(drop=True)
                st.dataframe(ktbl, use_container_width=True, height=220)

    # ═══════════════════════════════════════════════════════════
    # TAB 6 — DATA TABLE
    # ═══════════════════════════════════════════════════════════
    with tab_table:
        st.markdown('<div class="sec">📋 Full District Data — Sales Backend Team</div>', unsafe_allow_html=True)

        # ── Admin: upload custom data / define extra columns ──
        extra_cols = []
        if is_admin:
            with st.expander("🛠️ Admin: Upload Custom Data / Add Columns", expanded=False):
                st.caption(
                    "Upload an Excel or CSV file with a **dist_code** column (matching the "
                    "census 'District code') plus any extra columns you want to track (e.g. "
                    "remarks, targets, contact numbers). They get merged into this table by "
                    "district automatically."
                )
                cc_file = st.file_uploader("Custom columns file", type=["xlsx","xls","csv"], key="custom_cols_uploader")
                if cc_file is not None:
                    try:
                        cc_df = pd.read_csv(cc_file) if cc_file.name.lower().endswith(".csv") else pd.read_excel(cc_file)
                        cc_df.columns = [str(c).strip() for c in cc_df.columns]
                        if "dist_code" not in cc_df.columns:
                            st.error("File must contain a 'dist_code' column matching the census District code.")
                        else:
                            cc_df.to_csv(FILES["custom"], index=False)
                            st.cache_data.clear()
                            st.success(f"Saved {len(cc_df)} rows with columns: "
                                       f"{', '.join([c for c in cc_df.columns if c != 'dist_code'])}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't read file: {e}")

                try:
                    existing_cc = pd.read_csv(FILES["custom"])
                    extra_cols = [c for c in existing_cc.columns if c != "dist_code"]
                except Exception:
                    extra_cols = []

                if extra_cols:
                    st.markdown("##### Column Types (for display formatting)")
                    meta = {}
                    if os.path.exists(FILES["meta"]):
                        try:
                            with open(FILES["meta"]) as f: meta = json.load(f)
                        except Exception: meta = {}
                    new_meta = {}
                    mcols = st.columns(min(len(extra_cols), 4) or 1)
                    for i, c in enumerate(extra_cols):
                        with mcols[i % len(mcols)]:
                            new_meta[c] = st.selectbox(
                                c, ["text","number"],
                                index=0 if meta.get(c,"text")=="text" else 1,
                                key=f"ccmeta_{c}",
                            )
                    if st.button("💾 Save Column Types"):
                        with open(FILES["meta"], "w") as f:
                            json.dump(new_meta, f, indent=2)
                        st.success("Saved.")
                else:
                    st.caption("No custom columns yet — upload a file above.")
        else:
            extra_cols = [c for c in flt.columns if c not in [
                "dist_code","state","district","population","krm","kro","jn_kro","responsible",
                "total_sale","avg_6m","month_sale","gg_total","gg_avg","ig_total","ig_avg",
                "status","state_label","district_title","pop_fmt","pop_lakh","lat","lon","krm_display",
            ]]

        srch2 = st.text_input("🔍 Search…", key="tbl_srch2")
        tbl   = flt.copy()
        if srch2:
            tbl = tbl[tbl["district_title"].str.contains(srch2,case=False,na=False)|
                      tbl["state_label"].str.contains(srch2,case=False,na=False)|
                      tbl["krm_display"].str.contains(srch2,case=False,na=False)]

        base_cols = ["state_label","district_title","krm_display","kro","jn_kro","responsible",
                     "population","total_sale","avg_6m","month_sale","gg_total","ig_total","status"]
        rename_map = {
            "state_label":"State","district_title":"District","krm_display":"KRM",
            "kro":"KRO","jn_kro":"JR.KRO","responsible":"Responsible",
            "population":"Population","total_sale":"Total (MT)","avg_6m":"6M Avg (MT)",
            "month_sale":f"{month_name} (MT)","gg_total":"GG (MT)","ig_total":"IG (MT)","status":"Status"
        }
        # Guard against a custom column name colliding with a reserved built-in
        # column/display-label (e.g. a custom column literally called "KRO",
        # which would otherwise duplicate the built-in KRO column and break
        # Styler downstream, since pandas requires unique column names to style).
        reserved = {c.lower() for c in base_cols} | {v.lower() for v in rename_map.values()}
        safe_extra_cols = [c for c in extra_cols if c in tbl.columns and c.lower() not in reserved]
        skipped_extra_cols = [c for c in extra_cols if c in tbl.columns and c.lower() in reserved]

        show_cols = base_cols + safe_extra_cols
        disp = tbl[show_cols].rename(columns=rename_map)
        # Final safety net: never let a duplicate column name reach Styler.
        disp = disp.loc[:, ~disp.columns.duplicated()]
        disp = disp.sort_values("Total (MT)",ascending=False).reset_index(drop=True)

        if skipped_extra_cols:
            st.caption(
                f"⚠️ Custom column(s) {', '.join(skipped_extra_cols)} share a name with a "
                "built-in column and were hidden here to avoid a display conflict — rename "
                "them in your upload to show both."
            )

        def status_style(val):
            if val=="ACTIVE":      return "background:#e6f4ea;color:#137333;font-weight:700"
            if val=="NO PRESENCE": return "background:#fce8e6;color:#c5221f;font-weight:700"
            return ""

        try:
            styled = disp.style.map(status_style, subset=["Status"])
        except AttributeError:
            styled = disp.style.applymap(status_style, subset=["Status"])

        st.caption(f"Showing {len(disp)} rows")
        st.dataframe(styled, use_container_width=True, height=480)
        st.download_button("⬇️ Download Full CSV",
                           data=disp.to_csv(index=False),
                           file_name="full_data.csv", mime="text/csv")

    # ═══════════════════════════════════════════════════════════
    # TAB 7 — SALES BACKEND TEAMS (ADMIN ONLY)
    # ═══════════════════════════════════════════════════════════
    if is_admin and tab_admin is not None:
        with tab_admin:
            st.markdown('<div class="sec">🛠️ Sales Backend Team Management</div>', unsafe_allow_html=True)
            st.caption(
                "Map States and/or Districts to each Sales Backend Team. Viewers can then use the "
                "🧑‍💼 **Sales Backend Team** slicer at the top of the dashboard to jump straight to that "
                "team's territory. Changes are saved to `sales_backend_teams.json`."
            )

            all_states_map = (df[["state","state_label"]].drop_duplicates()
                               .set_index("state_label")["state"].to_dict())
            all_dist_map = df[["district","district_title","state_label"]].drop_duplicates()

            edit_target   = st.session_state.get("admin_edit_team")
            widget_suffix = edit_target if edit_target else "new"

            st.markdown("#### ➕ Add / Update Team")
            if edit_target:
                st.info(f"✏️ Editing **{edit_target}** — change the fields below and Save, or Cancel.")
                if st.button("✖ Cancel edit"):
                    st.session_state["admin_edit_team"] = None
                    st.rerun()

            default_name   = edit_target if edit_target else ""
            default_states = [STATE_LABELS.get(s, s.title())
                               for s in teams.get(edit_target, {}).get("states", [])] if edit_target else []

            t_state_labels = st.multiselect(
                "Mapped States", sorted(all_states_map.keys()),
                default=default_states, key=f"admin_team_states_{widget_suffix}",
            )
            dist_pool = all_dist_map if not t_state_labels else all_dist_map[all_dist_map["state_label"].isin(t_state_labels)]
            default_dist_titles = [d.title() for d in teams.get(edit_target, {}).get("districts", [])] if edit_target else []
            default_dist_titles = [d for d in default_dist_titles if d in dist_pool["district_title"].values]

            with st.form(f"team_form_{widget_suffix}", clear_on_submit=False):
                t_name = st.text_input("Team Name", value=default_name,
                                        placeholder="e.g. Sales Backend Team - East")
                t_dist_labels = st.multiselect(
                    "Mapped Districts (optional — for finer control within a state)",
                    sorted(dist_pool["district_title"].unique()), default=default_dist_titles,
                )
                submitted = st.form_submit_button("💾 Save Team", use_container_width=True)

                if submitted:
                    clean_name = t_name.strip()
                    if not clean_name:
                        st.error("Team name is required.")
                    else:
                        raw_states = [all_states_map[s] for s in t_state_labels]
                        raw_dists  = dist_pool[dist_pool["district_title"].isin(t_dist_labels)]["district"].tolist()
                        if edit_target and edit_target != clean_name and edit_target in teams:
                            del teams[edit_target]
                        teams[clean_name] = {"states": raw_states, "districts": raw_dists}
                        save_teams(teams)
                        st.session_state["admin_edit_team"] = None
                        st.success(f"✅ Team '{clean_name}' saved with {len(raw_states)} state(s) and {len(raw_dists)} district(s).")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### 📋 Existing Teams")
            if not teams:
                st.info("No Sales Backend Teams created yet. Add one above.")
            else:
                for tname, tinfo in sorted(teams.items()):
                    st_labels = sorted(STATE_LABELS.get(s, s.title()) for s in tinfo.get("states", []))
                    d_labels  = sorted(d.title() for d in tinfo.get("districts", []))
                    with st.expander(f"🧑‍💼 {tname} — {len(st_labels)} state(s) · {len(d_labels)} district(s)"):
                        st.write("**States:** " + (", ".join(st_labels) if st_labels else "—"))
                        st.write("**Districts:** " + (", ".join(d_labels) if d_labels else "—"))
                        ec1, ec2 = st.columns(2)
                        if ec1.button("✏️ Edit", key=f"edit_team_{tname}", use_container_width=True):
                            st.session_state["admin_edit_team"] = tname
                            st.rerun()
                        if ec2.button("🗑️ Delete", key=f"del_team_{tname}", use_container_width=True):
                            del teams[tname]
                            save_teams(teams)
                            st.rerun()

    # ═══════════════════════════════════════════════════════════
    # TAB 8 — LOCATION MAPPING (ADMIN ONLY)
    # ═══════════════════════════════════════════════════════════
    if is_admin and tab_mapping is not None:
        with tab_mapping:
            st.markdown('<div class="sec">🧭 State / District Name Mapping</div>', unsafe_allow_html=True)
            st.caption(
                "The **Active District** file and the **Census** file don't always spell state "
                "or district names the same way (e.g. `WB` vs West Bengal, `MOTIHARI` vs Purba "
                "Champaran). When a name doesn't match, that district silently drops out of the "
                "'Active' count everywhere in the dashboard. Fix mismatches here — changes save "
                "to `custom_alias_map.json` and apply immediately, no code edits needed."
            )

            state_label_map = {s: STATE_LABELS.get(s, s.title())
                                for s in sorted(census_districts["state"].unique())}
            label_to_state  = {v: k for k, v in state_label_map.items()}
            sorted_state_labels = sorted(state_label_map.values())

            def district_options(raw_state):
                opts = sorted(census_districts[census_districts["state"] == raw_state]["district"].unique())
                return {d.title(): d for d in opts}

            # ── Diagnostics: entries that don't resolve to a real district ──
            st.markdown("#### ⚠️ Unmatched Location Entries")
            if unmatched_locations.empty:
                st.success("✅ All entries in the active-district and sales data files matched a census district. Nothing to fix.")
            else:
                st.warning(
                    f"**{len(unmatched_locations)}** entries (from the active-district file "
                    "and/or the uploaded sales data file) don't match any census district — "
                    "these are **not** being counted anywhere in the dashboard until mapped below."
                )
                for i, row in unmatched_locations.iterrows():
                    with st.expander(
                        f"❓ {row['district_raw'].title()}  —  ({row['state_raw'].title()})  "
                        f"· from {row.get('source','Unknown source')}"
                    ):
                        st.caption(
                            f"Currently resolves to **{row['state_norm'].title()} / "
                            f"{row['dist_norm'].title()}**, which isn't a census district."
                        )
                        guess_state = row["state_norm"] if row["state_norm"] in state_label_map else (
                            row["state_raw"] if row["state_raw"] in state_label_map
                            else next(iter(state_label_map))
                        )
                        sel_state_label = st.selectbox(
                            "Correct State", sorted_state_labels,
                            index=sorted_state_labels.index(state_label_map[guess_state]),
                            key=f"map_state_{i}",
                        )
                        sel_state_raw = label_to_state[sel_state_label]
                        dopts = district_options(sel_state_raw)
                        skip = st.checkbox(
                            "🚫 Not a real district — skip this entry entirely",
                            key=f"map_skip_{i}",
                        )
                        sel_dist_label = None
                        if not skip:
                            if dopts:
                                sel_dist_label = st.selectbox(
                                    "Correct District", sorted(dopts.keys()), key=f"map_dist_{i}"
                                )
                            else:
                                st.info("No census districts found for that state.")

                        if st.button("💾 Save Mapping", key=f"map_save_{i}"):
                            ov = load_alias_overrides()
                            if sel_state_raw != row["state_raw"]:
                                ov["states"][row["state_raw"]] = sel_state_raw
                            if skip:
                                ov["districts"][row["district_raw"]] = "_SKIP_"
                            elif sel_dist_label:
                                ov["districts"][row["district_raw"]] = dopts[sel_dist_label]
                            save_alias_overrides(ov)
                            st.cache_data.clear()
                            st.success("Saved — refreshing…")
                            st.rerun()

            # ── Existing custom mappings, with delete ──
            st.markdown("---")
            st.markdown("#### 📖 Custom Mappings on File")
            overrides = load_alias_overrides()
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("**State mappings**")
                if not overrides["states"]:
                    st.caption("None yet.")
                else:
                    for raw, target in sorted(overrides["states"].items()):
                        rr1, rr2 = st.columns([4, 1])
                        rr1.write(f"`{raw}` → **{STATE_LABELS.get(target, target.title())}**")
                        if rr2.button("🗑️", key=f"del_state_alias_{raw}"):
                            ov = load_alias_overrides()
                            ov["states"].pop(raw, None)
                            save_alias_overrides(ov)
                            st.cache_data.clear()
                            st.rerun()
            with mc2:
                st.markdown("**District mappings**")
                if not overrides["districts"]:
                    st.caption("None yet.")
                else:
                    for raw, target in sorted(overrides["districts"].items()):
                        rr1, rr2 = st.columns([4, 1])
                        label = "🚫 Skip" if target == "_SKIP_" else target.title()
                        rr1.write(f"`{raw}` → **{label}**")
                        if rr2.button("🗑️", key=f"del_dist_alias_{raw}"):
                            ov = load_alias_overrides()
                            ov["districts"].pop(raw, None)
                            save_alias_overrides(ov)
                            st.cache_data.clear()
                            st.rerun()

            # ── Add a mapping proactively, before it ever shows up as unmatched ──
            st.markdown("---")
            st.markdown("#### ➕ Add a Manual Mapping")
            st.caption("Pre-map a name you already know will appear, without waiting for it to surface as unmatched.")
            with st.form("manual_alias_form", clear_on_submit=True):
                mtype = st.radio("Mapping type", ["District", "State"], horizontal=True)
                raw_input = st.text_input("Raw name (exactly as it appears in the active-district file)")
                if mtype == "District":
                    m_state_label = st.selectbox("Belongs to State", sorted_state_labels, key="manual_state_pick")
                    m_dopts = district_options(label_to_state[m_state_label])
                    target_label = st.selectbox(
                        "Maps to Census District", sorted(m_dopts.keys()) if m_dopts else [],
                        key="manual_dist_pick",
                    )
                else:
                    target_label = st.selectbox("Maps to Census State", sorted_state_labels, key="manual_state_target")

                if st.form_submit_button("💾 Save Mapping"):
                    raw_clean = raw_input.strip().upper()
                    if not raw_clean:
                        st.error("Enter a raw name first.")
                    else:
                        ov = load_alias_overrides()
                        if mtype == "District":
                            ov["districts"][raw_clean] = m_dopts[target_label]
                        else:
                            ov["states"][raw_clean] = label_to_state[target_label]
                        save_alias_overrides(ov)
                        st.cache_data.clear()
                        st.success(f"Saved mapping for '{raw_clean}'.")
                        st.rerun()

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════
    # TAB 9 — SALES DATA UPLOAD (ADMIN ONLY)
    # ═══════════════════════════════════════════════════════════
    if is_admin and tab_sales_up is not None:
        with tab_sales_up:
            st.markdown('<div class="sec">📤 Sales Data Source</div>', unsafe_allow_html=True)
            st.caption(
                "By default, sales figures (Total Sale, current-month Sale, 6-Month Avg, "
                "GG/IG) come from the pre-built columns in the census workbook. Upload raw "
                "invoice / order-level exports here instead — you can upload several files at "
                "once (e.g. one per region or per week) and they'll be combined automatically — "
                "and every module (top Presence Map, Live Dashboard, Product Sales, Team View, "
                "Data Table) will compute those figures live from it. Population, KRM/KRO/JR.KRO "
                "ownership, and district identity keep coming from the census file and are "
                "auto-matched in by district, so you don't need to duplicate that data here."
            )

            if sales_source_info["using_invoice_data"]:
                st.success(
                    f"✅ **Using uploaded sales data** — {sales_source_info['invoice_rows']:,} "
                    f"invoice rows loaded, current month detected as **{month_name}**."
                )
                if st.button("🗑️ Remove uploaded sales data & revert to census sale columns"):
                    if os.path.exists(SALES_SOURCE_FILE):
                        os.remove(SALES_SOURCE_FILE)
                    st.cache_data.clear()
                    st.success("Reverted to census workbook sale columns.")
                    st.rerun()
            else:
                st.info(
                    "ℹ️ **Using the census workbook's built-in sale columns** — no sales data "
                    "file uploaded yet."
                )

            st.markdown("---")
            st.markdown("#### ⬆️ Upload Sales Data (single or multiple files)")
            st.caption(
                "Accepted formats: `.xlsx` or `.csv`. Required columns (any order, case-"
                "insensitive) — **STATE**, **DISTRICT/ST**, **QTY**, and **DESPATCH DATE** "
                "(or ORDER DATE). Optional but recommended: **PRODUCT** (used to split GG vs "
                "IG — matched by the text 'GG' / 'IG' appearing in the product name), "
                "**INVOICE NO**, **ORDER NO**, **BILLING NAME**, **CLIENT NAME**. "
                "Uploading a new batch replaces the previous one."
            )
            ups = st.file_uploader(
                "Sales data file(s)", type=["xlsx", "xls", "csv"],
                accept_multiple_files=True, key="sales_data_uploader",
            )
            if ups:
                with st.spinner(f"Combining {len(ups)} file(s)…"):
                    frames = []
                    read_errors = []
                    for f in ups:
                        try:
                            frames.append(pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f))
                        except Exception as e:
                            read_errors.append(f"{f.name}: {e}")
                    if read_errors:
                        st.error("Couldn't read: " + "; ".join(read_errors))
                    if frames:
                        combined = pd.concat(frames, ignore_index=True, sort=False)
                        combined.to_excel(SALES_SOURCE_FILE, index=False)
                        csv_twin = SALES_SOURCE_FILE.replace(".xlsx", ".csv")
                        if os.path.exists(csv_twin):
                            os.remove(csv_twin)
                        st.cache_data.clear()
                        st.success(f"Combined {len(frames)} file(s), {len(combined):,} total rows — processing…")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### 📐 How the figures are computed")
            st.markdown(html_block("""
            <ul style='font-size:13px;color:#333;line-height:1.7;'>
              <li><b>District match:</b> each row's STATE / DISTRICT-ST is matched to a
                  census district using the same name-mapping table as the
                  🧭 Location Mapping tab. Rows that don't match show up there for you to fix.</li>
              <li><b>Total Sale:</b> sum of QTY for a district, across all rows in the file.</li>
              <li><b>Current-month Sale:</b> sum of QTY for the most recent calendar month
                  found in DESPATCH DATE / ORDER DATE — this also sets the month label used
                  across the dashboard (e.g. "July (MT)").</li>
              <li><b>6-Month Avg:</b> sum of QTY over the most recent 6 calendar months
                  present in the file (matches how the census workbook's own
                  "last 6 month avg." column was structured).</li>
              <li><b>GG / IG split:</b> a row counts toward GG if its PRODUCT text contains
                  "GG", toward IG if it contains "IG"; everything else still counts toward
                  Total Sale but isn't split into either card.</li>
            </ul>
            """), unsafe_allow_html=True)

    st.caption("🇮🇳 HMB Presence & Sales Dashboard · Built with Streamlit + Plotly")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.get("auth"):
    login_page()
else:
    dashboard()
