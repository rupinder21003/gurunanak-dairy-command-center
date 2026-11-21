"""appp.py - Guru Nanak Dairy | Velvet Ledger Studio (Streamlit + MySQL + Pandas + Plotly)."""
import datetime as dt
import inspect
import io
import math
import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from mysql.connector import Error as MySQLError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find db.py next to this file

st.set_page_config(
    page_title="Guru Nanak Dairy | Velvet Ledger",
    page_icon="🥛",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    import db
except ModuleNotFoundError:
    st.error(
        "db.py was not found. Put **db.py** in the SAME folder as this file "
        f"(`{os.path.dirname(os.path.abspath(__file__))}`) and refresh the page."
    )
    st.stop()

C = db.COL
REFRESH_SECONDS = 5
DATE_FMT = "%d-%b-%Y"  # Consistent format matching MySQL rows e.g. 01-Apr-2025

VIOLET = "#8B5CF6"
SOFT_VIOLET = "#A78BFA"
DEEP_INDIGO = "#4C1D95"
IRIS = "#6366F1"
MINT = "#22C55E"
AMBER_DOT = "#FACC15"
ROSE_DOT = "#FB7185"
SLATE_AXIS = "#94A3B8"

PALETTE = [VIOLET, IRIS, SOFT_VIOLET, "#38BDF8", "#C084FC", "#818CF8", "#E879F9"]
LAYOUT = dict(
    height=360,
    margin=dict(l=14, r=14, t=52, b=14),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#E2E8F0"),
    xaxis=dict(gridcolor="rgba(139, 92, 246, 0.12)", zerolinecolor="rgba(139, 92, 246, 0.2)"),
    yaxis=dict(gridcolor="rgba(139, 92, 246, 0.12)", zerolinecolor="rgba(139, 92, 246, 0.2)"),
)


def _full(fn):
    """Stretch-to-width argument that works on old and new Streamlit versions."""
    try:
        sig = str(inspect.signature(fn))
    except (TypeError, ValueError):
        sig = ""
    return {"width": "stretch"} if "stretch" in sig else {"use_container_width": True}


FD, FE, FP, FB, FDL = (
    _full(st.dataframe),
    _full(st.data_editor),
    _full(st.plotly_chart),
    _full(st.button),
    _full(st.download_button),
)

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

<style>
html, body, [class*="css"], .stMarkdown, .stText, label, input, select, textarea, button {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
code, pre, .vk-num, [data-testid="stMetricValue"] {
  font-family: 'JetBrains Mono', monospace !important;
}

header[data-testid="stHeader"] {
  background: rgba(7, 7, 11, 0.72) !important;
  backdrop-filter: blur(10px);
}

.stApp {
  background:
    radial-gradient(ellipse 65% 45% at 52% 0%, rgba(124, 58, 237, 0.24), transparent 65%),
    radial-gradient(ellipse 40% 35% at 92% 15%, rgba(79, 70, 229, 0.14), transparent 60%),
    #07070B;
  color: #F4F4F8;
}
.block-container {
  padding-top: 3.4rem !important;
  padding-bottom: 2.8rem !important;
  max-width: 1520px;
}

/* ---------- sidebar (unclipped & crisp) ---------- */
section[data-testid="stSidebar"] {
  min-width: 265px !important;
  max-width: 280px !important;
  background: linear-gradient(180deg, #09090E 0%, #0D0B16 100%) !important;
  border-right: 1px solid rgba(139, 92, 246, 0.18);
}
section[data-testid="stSidebar"] > div:first-child {
  padding-left: 14px !important;
  padding-right: 14px !important;
  overflow-x: hidden !important;
}
section[data-testid="stSidebar"] * {
  color: #E2E8F0;
  box-sizing: border-box;
}
.sb-top {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 6px 4px 14px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.16);
}
.sb-orb {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-weight: 800;
  color: #FFFFFF;
  background: linear-gradient(135deg, #8B5CF6, #5B21B6);
  box-shadow: 0 0 18px rgba(139, 92, 246, 0.45);
}
.sb-brand-name {
  font-size: 0.96rem;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.sb-brand-tag {
  font-size: 0.66rem;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: #A78BFA;
  font-weight: 700;
  margin-top: 2px;
}
.sb-group-lbl {
  font-size: 0.67rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #A78BFA;
  margin: 14px 4px 8px;
}
section[data-testid="stSidebar"] div[role="radiogroup"] {
  gap: 5px;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label {
  background: rgba(18, 17, 29, 0.55) !important;
  border-radius: 10px !important;
  padding: 9px 12px !important;
  width: 100% !important;
  border: 1px solid rgba(139, 92, 246, 0.08) !important;
  color: #CBD5E1 !important;
  font-weight: 500 !important;
  transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
  background: rgba(139, 92, 246, 0.14) !important;
  border-color: rgba(167, 139, 250, 0.25) !important;
  color: #FFFFFF !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(90deg, rgba(139, 92, 246, 0.28), rgba(91, 33, 182, 0.16)) !important;
  border-color: rgba(167, 139, 250, 0.45) !important;
  color: #FFFFFF !important;
  font-weight: 700 !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
  display: none !important;
}
.pulse-box {
  margin-top: 14px;
  padding: 13px 14px;
  border-radius: 15px;
  background: radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.30), rgba(18, 15, 31, 0.94) 75%);
  border: 1px solid rgba(167, 139, 250, 0.26);
}
.pulse-badge {
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #DDD6FE;
  margin-bottom: 4px;
}
.pulse-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #FFFFFF;
  margin-bottom: 4px;
}
.pulse-copy {
  font-size: 0.73rem;
  color: #C4B5FD;
  line-height: 1.42;
}

/* ---------- top studio bar ---------- */
.studio-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 22px;
  border-radius: 18px;
  background: rgba(15, 15, 24, 0.88);
  border: 1px solid rgba(139, 92, 246, 0.22);
  backdrop-filter: blur(12px);
  margin-bottom: 18px;
}
.studio-kicker {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #A78BFA;
}
.studio-h1 {
  font-size: 1.55rem;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-top: 2px;
}
.studio-sub {
  font-size: 0.85rem;
  color: #9CA3AF;
  margin-top: 3px;
}
.studio-pills {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.pill-violet {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 13px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  color: #EDE9FE;
  background: rgba(124, 58, 237, 0.24);
  border: 1px solid rgba(167, 139, 250, 0.36);
}
.pill-violet i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #A78BFA;
  box-shadow: 0 0 8px #A78BFA;
  display: inline-block;
}
.pill-node {
  padding: 6px 13px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 600;
  color: #E2E8F0;
  background: rgba(24, 24, 37, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

/* ---------- form band headers ---------- */
.band-tag {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #C4B5FD;
  margin: 10px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.18);
}

/* ---------- KPI wave cards ---------- */
.vk-card {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 16px 18px 14px;
  background: linear-gradient(160deg, rgba(24, 21, 38, 0.95) 0%, rgba(12, 12, 20, 0.98) 100%);
  border: 1px solid rgba(139, 92, 246, 0.20);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}
.vk-card:hover {
  transform: translateY(-2px);
  border-color: rgba(167, 139, 250, 0.45);
  box-shadow: 0 12px 28px rgba(109, 40, 217, 0.22);
}
.vk-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.vk-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #E4E4E7;
}
.vk-badge {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 0.85rem;
  background: rgba(139, 92, 246, 0.16);
  border: 1px solid rgba(167, 139, 250, 0.24);
}
.vk-body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}
.vk-num {
  font-size: 1.52rem;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: -0.02em;
  line-height: 1.15;
}
.vk-sub {
  font-size: 0.75rem;
  color: #34D399;
  margin-top: 8px;
  font-weight: 500;
}

/* ---------- feed list cards ---------- */
.feed-panel {
  border-radius: 18px;
  padding: 18px;
  background: rgba(15, 15, 24, 0.90);
  border: 1px solid rgba(139, 92, 246, 0.18);
  margin-bottom: 14px;
}
.feed-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 13px;
  background: rgba(24, 24, 38, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.10);
  margin-bottom: 8px;
}
.feed-main {
  font-size: 0.86rem;
  font-weight: 600;
  color: #F4F4F8;
}
.feed-meta {
  font-size: 0.74rem;
  color: #9CA3AF;
  margin-top: 2px;
}
.dot-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.74rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.12);
  color: #E9D5FF;
  white-space: nowrap;
}
.dot-pill i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

/* ---------- buttons, tabs, inputs, tables ---------- */
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {
  border-radius: 11px;
  font-weight: 600;
  border: 1px solid rgba(196, 181, 253, 0.25);
  color: #FFFFFF;
  background: linear-gradient(135deg, #8B5CF6, #6D28D9);
  box-shadow: 0 4px 16px rgba(109, 40, 217, 0.35);
  transition: all 0.15s ease;
}
.stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {
  transform: translateY(-1px);
  background: linear-gradient(135deg, #7C3AED, #5B21B6);
  color: #FFFFFF;
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.48);
}
.stButton>button:disabled {
  background: #27273A;
  border-color: transparent;
  color: #71717A;
  box-shadow: none;
}
button[data-baseweb="tab"] {
  font-weight: 600;
  color: #A1A1AA;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #C4B5FD !important;
}
div[data-baseweb="tab-highlight"] {
  background-color: #8B5CF6 !important;
  height: 3px;
}
div[data-testid="stDataFrame"] {
  border-radius: 14px;
  border: 1px solid rgba(139, 92, 246, 0.20);
}
div[data-testid="stMetric"] {
  background: rgba(18, 17, 29, 0.92);
  border: 1px solid rgba(139, 92, 246, 0.20);
  border-left: 3px solid #8B5CF6;
  border-radius: 14px;
  padding: 12px 16px;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------- helpers
def clean_label(col):
    """Strip BOM / mojibake artifacts like ï»¿ from column names."""
    return str(col).replace("\ufeff", "").replace("ï»¿", "").strip()


def num(val, default=0.0):
    """Safely convert numeric or numeric-string values into float."""
    if val is None or (not isinstance(val, str) and pd.isna(val)):
        return default
    try:
        return float(str(val).replace(",", "").replace("Rs", "").strip())
    except (ValueError, TypeError):
        return default


def parse_date(val):
    """Parse any date string/object cleanly into a datetime.date object."""
    if val is None or (not isinstance(val, str) and pd.isna(val)):
        return dt.date.today()
    if isinstance(val, dt.datetime):
        return val.date()
    if isinstance(val, dt.date):
        return val
    try:
        parsed = pd.to_datetime(str(val).strip(), dayfirst=True, errors="coerce")
        if pd.notna(parsed):
            return parsed.date()
    except Exception:  # noqa: BLE001
        pass
    return dt.date.today()


def fmt_date(val):
    """Format any date consistently as DD-Mon-YYYY (e.g. 01-Apr-2025)."""
    return parse_date(val).strftime(DATE_FMT)


def normalize_dates_df(df):
    """Ensure date columns use uniform DD-Mon-YYYY formatting and clean display headers."""
    if df is None or df.empty:
        return df
    out = df.copy()
    rename_map = {col: clean_label(col) for col in out.columns if clean_label(col) != col}
    if rename_map:
        out = out.rename(columns=rename_map)
    date_col = clean_label(C.get("date", "Date"))
    for col in out.columns:
        if col == date_col or "date" in col.lower():
            out[col] = out[col].apply(lambda x: fmt_date(x) if pd.notna(x) and str(x).strip() else x)
    return out


def normalize_record_dates(vals, meta):
    """Format date fields uniformly before saving to MySQL (handles both DATE and TEXT date columns)."""
    out = dict(vals)
    dtype_map = {r.col: r.dtype.lower() for r in meta.itertuples()}
    date_col = C.get("date")
    for col, val in list(out.items()):
        c_clean = clean_label(col)
        if col == date_col or c_clean.lower() == "date" or "date" in c_clean.lower():
            dtype = dtype_map.get(col, "")
            d_obj = parse_date(val)
            if dtype in db.DT_TYPES:
                out[col] = dt.datetime.combine(d_obj, dt.time())
            elif dtype == db.DATE_ONLY:
                out[col] = d_obj
            else:
                out[col] = d_obj.strftime(DATE_FMT)
    return out


def _ordered_form_cols(meta, computed, pk, auto):
    """Order columns logically: Schedule & Item -> Category & Channel -> Volumes, Pricing & Costs."""
    preferred_order = [
        C.get("date"),
        C.get("dow"),
        C.get("product"),
        C.get("category"),
        C.get("unit"),
        C.get("ctype"),
        C.get("qty"),
        C.get("rate"),
        C.get("discount"),
        C.get("cogs"),
        C.get("opex"),
        C.get("gross"),
        C.get("net"),
        C.get("profit"),
    ]
    rows_by_col = {r.col: r for r in meta.itertuples()}
    ordered = []
    seen = set()

    for col in preferred_order:
        if col and col in rows_by_col and col not in seen:
            r = rows_by_col[col]
            if not ((auto and r.col in computed) or r.col == pk):
                ordered.append(r)
            seen.add(col)

    for r in meta.itertuples():
        if r.col not in seen:
            if not ((auto and r.col in computed) or r.col == pk):
                ordered.append(r)
            seen.add(r.col)

    return ordered


def _wave_svg(seed_str, uid):
    """Soft glowing area sparkline SVG matching violet KPI cards."""
    h = sum((i + 1) * ord(ch) for i, ch in enumerate(str(seed_str)))
    ys = [18 - ((h >> (idx * 3)) % 12) for idx in range(6)]
    xs = [2, 20, 38, 56, 74, 92]
    pts = [(xs[i], ys[i]) for i in range(6)]
    line_d = " M " + " L ".join(f"{x},{y}" for x, y in pts)
    area_d = line_d + f" L {xs[-1]},26 L {xs[0]},26 Z"
    dot_x, dot_y = pts[4]
    grad_id = f"g_{uid}_{abs(h) % 9999}"
    return (
        f'<svg width="96" height="28" viewBox="0 0 96 28" fill="none" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#A78BFA" stop-opacity="0.45"/>'
        f'<stop offset="100%" stop-color="#8B5CF6" stop-opacity="0.0"/>'
        f'</linearGradient></defs>'
        f'<path d="{area_d}" fill="url(#{grad_id})"/>'
        f'<path d="{line_d}" stroke="#A78BFA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{dot_x}" cy="{dot_y}" r="3.5" fill="#DDD6FE" stroke="#7C3AED" stroke-width="1.5"/>'
        f'</svg>'
    )


def header(kicker, title, subtitle, health):
    db_tag = (
        f'<span class="pill-node">MySQL {health["version"].split("-")[0]} · {health["host"]}:{health["port"]}</span>'
        if health["ok"]
        else '<span class="pill-node">Preview Mode · Sample Data</span>'
    )
    st.markdown(
        f'<div class="studio-bar">'
        f'  <div>'
        f'    <div class="studio-kicker">{kicker}</div>'
        f'    <div class="studio-h1">{title}</div>'
        f'    <div class="studio-sub">{subtitle}</div>'
        f'  </div>'
        f'  <div class="studio-pills">'
        f'    <span class="pill-violet"><i></i>STREAMING</span>'
        f'    {db_tag}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kpi(col, idx, label, value, sub="", icon=""):
    col.markdown(
        f'<div class="vk-card">'
        f'  <div class="vk-head"><span class="vk-title-wrap"><span class="vk-badge">{icon}</span>{label}</span></div>'
        f'  <div class="vk-body"><span class="vk-num">{value}</span>{_wave_svg(label + value, idx)}</div>'
        f'  <div class="vk-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def finish(msg, icon="✅"):
    """After any create / update / delete: clear cache, queue a toast, rerun the whole app."""
    st.cache_data.clear()
    st.session_state["_flash"] = (msg, icon)
    st.rerun()


def fail(e):
    msg = "Duplicate value for a unique field." if isinstance(e, MySQLError) and getattr(e, "errno", None) == 1062 else str(e)
    st.toast(msg, icon="❌")
    st.error(msg)


def live(fn):
    every = REFRESH_SECONDS if st.session_state.get("auto_refresh", True) else None
    return st.fragment(run_every=every)(fn)


def date_filter(key, label="date range"):
    if st.checkbox(f"Filter by {label}", key=f"{key}_use"):
        rng = st.date_input(
            f"{label.capitalize()} ({DATE_FMT})",
            key=f"{key}_rng",
            value=(dt.date.today() - dt.timedelta(days=90), dt.date.today()),
            format="DD/MM/YYYY",
        )
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            return rng[0], rng[1]
    return None, None


def to_xlsx(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Export")
    return buf.getvalue()


# ----------------------------------------------------------------- cloud preview fallback data
def _sample_sales_df():
    return pd.DataFrame([
        {
            "id": 101,
            "Date": "01-Apr-2025",
            "Day of Week": "Tuesday",
            "Category": "Milk",
            "Product": "Full Cream Milk",
            "Customer Type": "Retail",
            "Quantity Sold": 45,
            "Unit": "Litre",
            "Rate per Unit (Rs)": 62.0,
            "Gross Revenue (Rs)": 2790.0,
            "Discount (Rs)": 90.0,
            "Net Revenue (Rs)": 2700.0,
            "Cost of Goods (Rs)": 1850.0,
            "Operating Cost (Rs)": 220.0,
            "Net Profit (Rs)": 630.0,
        },
        {
            "id": 102,
            "Date": "02-Apr-2025",
            "Day of Week": "Wednesday",
            "Category": "Paneer",
            "Product": "Fresh Malai Paneer",
            "Customer Type": "Wholesale",
            "Quantity Sold": 24,
            "Unit": "Kg",
            "Rate per Unit (Rs)": 360.0,
            "Gross Revenue (Rs)": 8640.0,
            "Discount (Rs)": 440.0,
            "Net Revenue (Rs)": 8200.0,
            "Cost of Goods (Rs)": 5400.0,
            "Operating Cost (Rs)": 650.0,
            "Net Profit (Rs)": 2150.0,
        },
        {
            "id": 103,
            "Date": "03-Apr-2025",
            "Day of Week": "Thursday",
            "Category": "Ghee",
            "Product": "Desi Bilona Ghee",
            "Customer Type": "Retail",
            "Quantity Sold": 12,
            "Unit": "Litre",
            "Rate per Unit (Rs)": 780.0,
            "Gross Revenue (Rs)": 9360.0,
            "Discount (Rs)": 360.0,
            "Net Revenue (Rs)": 9000.0,
            "Cost of Goods (Rs)": 5900.0,
            "Operating Cost (Rs)": 520.0,
            "Net Profit (Rs)": 2580.0,
        },
        {
            "id": 104,
            "Date": "04-Apr-2025",
            "Day of Week": "Friday",
            "Category": "Curd",
            "Product": "Farm Dahi Bowl",
            "Customer Type": "Retail",
            "Quantity Sold": 60,
            "Unit": "Kg",
            "Rate per Unit (Rs)": 75.0,
            "Gross Revenue (Rs)": 4500.0,
            "Discount (Rs)": 150.0,
            "Net Revenue (Rs)": 4350.0,
            "Cost of Goods (Rs)": 2700.0,
            "Operating Cost (Rs)": 310.0,
            "Net Profit (Rs)": 1340.0,
        },
        {
            "id": 105,
            "Date": "05-Apr-2025",
            "Day of Week": "Saturday",
            "Category": "Butter",
            "Product": "White Makhan",
            "Customer Type": "Wholesale",
            "Quantity Sold": 18,
            "Unit": "Kg",
            "Rate per Unit (Rs)": 520.0,
            "Gross Revenue (Rs)": 9360.0,
            "Discount (Rs)": 360.0,
            "Net Revenue (Rs)": 9000.0,
            "Cost of Goods (Rs)": 6100.0,
            "Operating Cost (Rs)": 540.0,
            "Net Profit (Rs)": 2360.0,
        },
    ])


def _render_preview_mode(health):
    df = _sample_sales_df()
    st.info(
        f"Cloud preview mode is active because MySQL ({health['host']}:{health['port']}) is not reachable from Streamlit Cloud. "
        "Sample dairy records are displayed below so you can view the full Velvet Studio interface."
    )
    net = float(df["Net Revenue (Rs)"].sum())
    profit = float(df["Net Profit (Rs)"].sum())
    r1 = st.columns(4)
    kpi(r1[0], 1, "Net Revenue", f"Rs {net:,.0f}", "Sample preview", "◈")
    kpi(r1[1], 2, "Net Profit", f"Rs {profit:,.0f}", "Sample preview", "✦")
    kpi(r1[2], 3, "Profit Margin", f"{(profit / net * 100) if net else 0:.2f}%", "Net profit ÷ net revenue", "◎")
    kpi(r1[3], 4, "Transactions", f"{len(df):,}", "Sample records", "❖")
    st.write("")
    cat = (
        df.groupby("Category", as_index=False)
        .agg(revenue=("Net Revenue (Rs)", "sum"), profit=("Net Profit (Rs)", "sum"))
        .sort_values("revenue", ascending=False)
    )
    c1, c2 = st.columns(2)
    m = cat.melt(id_vars="Category", value_vars=["revenue", "profit"], var_name="metric", value_name="Rs")
    fig1 = px.bar(
        m,
        x="Category",
        y="Rs",
        color="metric",
        barmode="group",
        title="Category-wise Revenue & Profit (Sample)",
        color_discrete_map={"revenue": IRIS, "profit": VIOLET},
    )
    fig1.update_layout(xaxis_title=None, yaxis_title="Rs", legend_title=None, **LAYOUT)
    c1.plotly_chart(fig1, **FP)

    fig2 = px.line(
        df,
        x="Date",
        y=["Net Revenue (Rs)", "Net Profit (Rs)"],
        markers=True,
        color_discrete_map={"Net Revenue (Rs)": IRIS, "Net Profit (Rs)": VIOLET},
        title=f"Daily Revenue & Profit Trend ({DATE_FMT})",
    )
    fig2.update_layout(xaxis_title=None, yaxis_title="Rs", legend_title=None, **LAYOUT)
    c2.plotly_chart(fig2, **FP)

    st.dataframe(normalize_dates_df(df), hide_index=True, **FD)


def field(col, dtype, key, default=None, choices=None):
    """Render the right input widget for a MySQL column type with clean labels & uniform dates."""
    lbl = clean_label(col)
    missing = default is None or (not isinstance(default, str) and pd.isna(default))
    is_date_col = (
        dtype == db.DATE_ONLY
        or dtype in db.DT_TYPES
        or col == C.get("date")
        or lbl.lower() == "date"
        or "date" in lbl.lower()
    )
    if is_date_col:
        d = dt.date.today() if missing else parse_date(default)
        v = st.date_input(f"{lbl} · {DATE_FMT}", value=d, format="DD/MM/YYYY", key=key)
        if dtype in db.DT_TYPES:
            return dt.datetime.combine(v, dt.time())
        if dtype == db.DATE_ONLY:
            return v
        return v.strftime(DATE_FMT)
    if dtype in db.INT_TYPES:
        return st.number_input(lbl, step=1, min_value=0, value=0 if missing else int(num(default)), key=key)
    if dtype in db.NUM_TYPES:
        return st.number_input(lbl, step=0.5, min_value=0.0, format="%.2f", value=0.0 if missing else num(default), key=key)
    opts = (choices or {}).get(col) or (choices or {}).get(lbl)
    if opts:
        cur = None if missing else str(default)
        opts = opts if cur is None or cur in opts else [cur] + opts
        return st.selectbox(lbl, opts, index=0 if cur is None else opts.index(cur), key=key)
    return st.text_input(lbl, value="" if missing else str(default), key=key)


def sale_inputs(prefix, defaults=None, auto=True, new_cat=False):
    """Structured, ordered form body generated from real table columns."""
    meta, choices, vals = db.insertable_meta(), db.get_choices(), {}
    computed = {C["gross"], C["net"], C["profit"]}
    pk = db.pk_info()[0]
    ordered_rows = _ordered_form_cols(meta, computed, pk, auto)

    schedule_item = {C.get("date"), C.get("dow"), C.get("product")}
    cat_channel = {C.get("category"), C.get("unit"), C.get("ctype")}

    grp1 = [r for r in ordered_rows if r.col in schedule_item]
    grp2 = [r for r in ordered_rows if r.col in cat_channel]
    grp3 = [r for r in ordered_rows if r.col not in schedule_item and r.col not in cat_channel]

    if grp1:
        st.markdown('<div class="band-tag">01 · Schedule & Item</div>', unsafe_allow_html=True)
        c1 = st.columns(3)
        for idx, r in enumerate(grp1):
            with c1[idx % 3]:
                vals[r.col] = field(r.col, r.dtype.lower(), f"{prefix}_{r.col}", (defaults or {}).get(r.col), choices)

    if grp2:
        st.markdown('<div class="band-tag">02 · Category & Channel</div>', unsafe_allow_html=True)
        c2 = st.columns(3)
        for idx, r in enumerate(grp2):
            with c2[idx % 3]:
                vals[r.col] = field(r.col, r.dtype.lower(), f"{prefix}_{r.col}", (defaults or {}).get(r.col), choices)

    if grp3:
        st.markdown('<div class="band-tag">03 · Volume, Pricing & Costs</div>', unsafe_allow_html=True)
        c3 = st.columns(3)
        for idx, r in enumerate(grp3):
            with c3[idx % 3]:
                vals[r.col] = field(r.col, r.dtype.lower(), f"{prefix}_{r.col}", (defaults or {}).get(r.col), choices)

    if new_cat:
        extra = st.text_input("New category name (leave blank to use the selected category)", key=f"{prefix}_newcat")
        if extra.strip():
            vals[C["category"]] = extra.strip()
    return normalize_record_dates(vals, meta)


def row_picker(key, multi=False):
    """Search box + list of up to 200 matching rows. Returns pk value (or list of pk values)."""
    pk = db.pk_info()[0]
    s = st.text_input("🔍 Narrow the list (product / category / any text / ID)", key=f"{key}_s")
    df = db.get_sales_page({"search": s}, 1, 200)
    if df.empty:
        st.info("No rows match.")
        return [] if multi else None
    date_col = C.get("date")
    labels = {
        f"#{r[pk]} · {fmt_date(r.get(date_col)) if date_col in r else ''} · {r.get(C['product'])} · {r.get(C['category'])} · Rs {num(r.get(C['net'])):,.2f}": r[pk]
        for r in df.to_dict("records")
    }
    if multi:
        return [labels[x] for x in st.multiselect("Select rows", list(labels), key=f"{key}_m")]
    return labels[st.selectbox("Select a transaction", list(labels), key=f"{key}_sel")]


if "_flash" in st.session_state:
    _m, _i = st.session_state.pop("_flash")
    st.toast(_m)

# ----------------------------------------------------------------- sidebar
health = db.check_connection()

with st.sidebar:
    st.markdown(
        '<div class="sb-top">'
        '  <div class="sb-orb">✦</div>'
        '  <div><div class="sb-brand-name">Guru Nanak Dairy</div><div class="sb-brand-tag">Velvet Studio</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sb-group-lbl">Menu</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigate",
        [
            "✦  Dairy Pulse",
            "❖  Ledger & Ops",
            "◈  Vault & Analytics",
            "◎  Chronicle Logs",
        ],
        label_visibility="collapsed",
    )
    st.markdown('<div class="sb-group-lbl">Sync Engine</div>', unsafe_allow_html=True)
    st.toggle(f"Auto-sync every {REFRESH_SECONDS}s", value=True, key="auto_refresh")
    if st.button("↻ Sync Now", **FB):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f'<div class="pulse-box">'
        f'  <div class="pulse-badge">✦ Format: {DATE_FMT}</div>'
        f'  <div class="pulse-title">Creamery Radar</div>'
        f'  <div class="pulse-copy">Ordered inputs, uniform dates & live MySQL sync.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

if not health["ok"]:
    header("PREVIEW", "Welcome back, Dairy Studio", "Cloud preview mode (MySQL offline in cloud container)", health)
    _render_preview_mode(health)
    st.stop()

try:
    ready, why = db.schema_ready()
except Exception as e:  # noqa: BLE001
    ready, why = False, f"Could not read the database: {e}"
if not ready:
    header("SCHEMA", "Setup Incomplete", "Database schema check reported an issue", health)
    st.warning(why)
    st.stop()


# =================================================================== PAGE 1
def render_dashboard():
    k = db.get_kpis()
    net, profit = num(k["net_revenue"]), num(k["net_profit"])
    r1 = st.columns(4)
    kpi(r1[0], 1, "Net Revenue", f"Rs {net:,.0f}", "After discounts", "◈")
    kpi(r1[1], 2, "Net Profit", f"Rs {profit:,.0f}", "After COGS & operating cost", "✦")
    kpi(r1[2], 3, "Profit Margin", f"{(profit / net * 100) if net else 0:.2f}%", "Net profit ÷ net revenue", "◎")
    kpi(r1[3], 4, "Transactions", f"{int(num(k['transactions'])):,}", "All sales records", "❖")
    st.write("")
    r2 = st.columns(4)
    kpi(r2[0], 5, "Volume Sold", f"{num(k['volume']):,.0f}", "Total units", "🥛")
    kpi(r2[1], 6, "Avg Order Value", f"Rs {num(k['avg_order']):,.2f}", "Net revenue per order", "🛒")
    kpi(r2[2], 7, "COGS % Revenue", f"{(num(k['cogs']) / net * 100) if net else 0:.2f}%", f"Rs {num(k['cogs']):,.0f}", "⚙")
    kpi(
        r2[3],
        8,
        "Discounts Given",
        f"Rs {num(k['discount']):,.0f}",
        f"Opex {(num(k['opex']) / net * 100) if net else 0:.1f}% of revenue",
        "🏷",
    )
    st.caption(f"Synced with MySQL at {dt.datetime.now():%H:%M:%S}")

    c1, c2 = st.columns(2)
    cat = db.get_category_perf()
    if cat.empty:
        c1.info("No data yet.")
    else:
        m = cat.melt(id_vars="category", value_vars=["revenue", "profit"], var_name="metric", value_name="Rs")
        fig = px.bar(
            m,
            x="category",
            y="Rs",
            color="metric",
            barmode="group",
            title="Category-wise Revenue & Profit",
            color_discrete_map={"revenue": IRIS, "profit": VIOLET},
        )
        fig.update_layout(xaxis_title=None, yaxis_title="Rs", legend_title=None, **LAYOUT)
        c1.plotly_chart(fig, **FP)

    trend = db.get_daily_trend()
    cmap = {"revenue": IRIS, "profit": VIOLET}
    if not trend.empty:
        trend = trend.copy()
        trend["day"] = trend["day"].apply(fmt_date)
        fig = px.line(
            trend,
            x="day",
            y=["revenue", "profit"],
            markers=True,
            color_discrete_map=cmap,
            title=f"Daily Revenue & Profit Trend ({DATE_FMT})",
        )
    else:
        d = db.get_dow_perf()
        d["day_of_week"] = pd.Categorical(d["day_of_week"], db.DOW_ORDER, ordered=True)
        fig = px.line(
            d.sort_values("day_of_week"),
            x="day_of_week",
            y=["revenue", "profit"],
            markers=True,
            color_discrete_map=cmap,
            title="Revenue & Profit by Day of Week",
        )
    fig.update_layout(xaxis_title=None, yaxis_title="Rs", legend_title=None, **LAYOUT)
    c2.plotly_chart(fig, **FP)

    c3, c4 = st.columns(2)
    ct = db.get_ctype_split()
    if ct.empty:
        c3.info("No data yet.")
    else:
        fig = px.pie(
            ct,
            names="customer_type",
            values="revenue",
            hole=0.60,
            title="Revenue Share by Customer Type",
            color_discrete_sequence=PALETTE,
        )
        fig.update_layout(**LAYOUT)
        c3.plotly_chart(fig, **FP)

    tg = db.get_targets()
    s = cat.merge(tg, left_on="category", right_on="Category", how="left") if not cat.empty else cat
    if s.empty:
        c4.info("No data yet.")
    else:
        s["status"] = s.apply(
            lambda r: "No target set"
            if pd.isna(r["Target_Profit"])
            else ("Target achieved" if num(r["profit"]) >= num(r["Target_Profit"]) else "Below target"),
            axis=1,
        )
        fig = px.bar(
            s,
            x="category",
            y="profit",
            color="status",
            title="Profit vs Target Breakdown",
            color_discrete_map={"Target achieved": VIOLET, "Below target": "#F43F5E", "No target set": "#475569"},
        )
        fig.add_trace(
            go.Scatter(
                x=s["category"],
                y=s["Target_Profit"],
                mode="markers",
                name="Target",
                marker=dict(symbol="diamond", size=11, color="#FFFFFF", line=dict(width=2, color=VIOLET)),
            )
        )
        fig.update_layout(xaxis_title=None, yaxis_title="Net profit (Rs)", legend_title=None, **LAYOUT)
        c4.plotly_chart(fig, **FP)

    left_feed, right_brief = st.columns([1.4, 1.0])
    with left_feed:
        st.markdown('<div class="feed-panel"><div class="sb-group-lbl" style="margin-top:0">Latest Ledger Entries</div>', unsafe_allow_html=True)
        recent = db.get_sales_page({}, 1, 5)
        pk = db.pk_info()[0]
        date_col = C.get("date")
        if recent.empty:
            st.caption("No entries yet.")
        else:
            for row in recent.to_dict("records"):
                p_name = str(row.get(C["product"], "Item"))
                c_name = str(row.get(C["category"], "General"))
                d_str = fmt_date(row.get(date_col)) if date_col in row else ""
                n_val = num(row.get(C["net"]))
                dot_c = MINT if n_val >= 0 else ROSE_DOT
                st.markdown(
                    f'<div class="feed-row">'
                    f'  <div><div class="feed-main">#{row.get(pk)} · {p_name}</div>'
                    f'       <div class="feed-meta">{d_str} · {c_name} · Qty {num(row.get(C["qty"])):g}</div></div>'
                    f'  <span class="dot-pill"><i style="background:{dot_c}"></i>Rs {n_val:,.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with right_brief:
        top_cat = cat.sort_values("profit", ascending=False).iloc[0]["category"] if not cat.empty else "—"
        top_prof = num(cat.sort_values("profit", ascending=False).iloc[0]["profit"]) if not cat.empty else 0.0
        margin_pct = (profit / net * 100) if net else 0.0
        st.markdown(
            f'<div class="feed-panel">'
            f'  <div class="sb-group-lbl" style="margin-top:0">✦ Studio Digest</div>'
            f'  <div class="feed-main" style="font-size:1rem;margin-bottom:8px">Top Performer: {top_cat}</div>'
            f'  <div class="feed-meta" style="line-height:1.55">'
            f'    Leading category profit sits at <b style="color:#E9D5FF">Rs {top_prof:,.0f}</b> '
            f'    across <b style="color:#E9D5FF">{int(num(k["transactions"])):,}</b> recorded transactions, '
            f'    with a live net margin of <b style="color:#E9D5FF">{margin_pct:.2f}%</b>.'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def page_dashboard():
    header("OVERVIEW", "Welcome back, Dairy Studio", "Live revenue, margins, category pulse & targets", health)
    live(render_dashboard)()


# =================================================================== PAGE 2
def render_browse():
    ch = db.get_choices()
    c1, c2, c3, c4 = st.columns([2, 1.2, 1.2, 1.2])
    search = c1.text_input("🔍 Search product / category / ID", key="b_search")
    cat = c2.selectbox("Category", ["All"] + ch.get(C["category"], []), key="b_cat")
    ctype = c3.selectbox("Customer type", ["All"] + ch.get(C["ctype"], []), key="b_ctype")
    dow = c4.selectbox("Day of week", ["All"] + ch.get(C["dow"], []), key="b_dow")
    d1, d2, d3, d4 = st.columns([2, 1, 1, 1])
    with d1:
        d_from, d_to = date_filter("b_date", "date range") if db.date_column() else (None, None)
    min_net = d2.number_input("Min net revenue", min_value=0.0, step=50.0, key="b_min")
    max_net = d3.number_input("Max net revenue (0 = none)", min_value=0.0, step=50.0, key="b_max")
    size = d4.selectbox("Rows per page", [10, 25, 50, 100], key="b_size")
    filters = {
        "search": search,
        "category": cat,
        "ctype": ctype,
        "dow": dow,
        "min_net": min_net,
        "max_net": max_net,
        "date_from": d_from,
        "date_to": d_to,
    }
    total = db.count_sales(filters)
    pages = max(1, math.ceil(total / size))
    if st.session_state.get("b_page", 1) > pages:
        st.session_state["b_page"] = pages
    page_no = st.number_input("Page", min_value=1, max_value=pages, step=1, key="b_page")
    st.caption(f"{total:,} matching row(s) · page {page_no} of {pages} · dates formatted as {DATE_FMT}")
    st.dataframe(normalize_dates_df(db.get_sales_page(filters, page_no, size)), hide_index=True, **FD)


def tab_add():
    auto = st.checkbox(
        "Auto-calculate Gross, Net revenue & Net profit  "
        "(Gross = Qty × Rate · Net = Gross − Discount · Profit = Net − COGS − Operating cost)",
        value=True,
        key="add_auto",
    )
    with st.form("add_sale", clear_on_submit=True):
        vals = sale_inputs("add", auto=auto)
        st.write("")
        ok = st.form_submit_button("+ Record Entry")
    if ok:
        try:
            rid = db.add_sale(db.apply_formulas(vals) if auto else vals)
            finish(f"Entry created (id {rid})")
        except Exception as e:  # noqa: BLE001
            fail(e)


def tab_relational():
    st.caption(
        "Saves the sale **and**, if the category has no row in `category_targets` yet, creates that target - "
        "all in ONE transaction (both succeed or both roll back)."
    )
    with st.form("rel_sale", clear_on_submit=True):
        vals = sale_inputs("rel", auto=True, new_cat=True)
        st.markdown('<div class="band-tag">04 · Target Benchmark</div>', unsafe_allow_html=True)
        tgt = st.number_input("Target profit (Rs) - used only if the category is new", min_value=0.0, step=500.0)
        ok = st.form_submit_button("🔗 Save Entry + Target")
    if ok:
        try:
            rid, created = db.add_sale_with_target(db.apply_formulas(vals), tgt)
            finish(f"Entry {rid} saved" + (" + new category target created" if created else ""))
        except Exception as e:  # noqa: BLE001
            fail(e)


def tab_inspector():
    rid = row_picker("insp")
    if rid is None:
        return
    d = db.get_row_detail(rid)
    if d.empty:
        st.warning("Row not found.")
        return
    d = normalize_dates_df(d)
    r = d.iloc[0]
    net, prof = num(r.get(C["net"])), num(r.get(C["profit"]))
    m = st.columns(4)
    m[0].metric("Net revenue", f"Rs {net:,.2f}")
    m[1].metric("Net profit", f"Rs {prof:,.2f}")
    m[2].metric("Margin", f"{(prof / net * 100) if net else 0:.2f}%")
    m[3].metric("Category target", "-" if pd.isna(r["Category_Target"]) else f"Rs {num(r['Category_Target']):,.0f}")
    left, right = st.columns(2)
    left.markdown("**Full record (joined with category_targets)**")
    left.dataframe(pd.DataFrame({"Field": r.index, "Value": [str(v) for v in r.values]}), hide_index=True, **FD)
    ctx = db.get_category_context(str(r[C["category"]]))
    right.markdown(f"**{r[C['category']]} category context**")
    right.dataframe(
        pd.DataFrame(
            {
                "Metric": ["Transactions", "Quantity", "Revenue (Rs)", "Profit (Rs)"],
                "Value": [
                    f"{num(ctx['transactions']):,.0f}",
                    f"{num(ctx['quantity']):,.2f}",
                    f"{num(ctx['revenue']):,.2f}",
                    f"{num(ctx['profit']):,.2f}",
                ],
            }
        ),
        hide_index=True,
        **FD,
    )
    st.markdown(f"**Other sales of '{r[C['product']]}' (latest 25)**")
    st.dataframe(normalize_dates_df(db.get_related(str(r[C["product"]]))), hide_index=True, **FD)


def tab_edit():
    pk = db.pk_info()[0]
    meta = db.insertable_meta()
    st.subheader("Inline grid editor")
    s = st.text_input("🔍 Filter rows to edit (first 200 matches are shown)", key="inl_s")
    original = normalize_dates_df(db.get_sales_page({"search": s}, 1, 200)).set_index(pk, drop=False)
    edited = st.data_editor(original, key=f"inline_{s}", num_rows="fixed", hide_index=True, disabled=[pk], **FE)
    changed = [
        normalize_record_dates(edited.loc[i].to_dict(), meta)
        for i in edited.index
        if not edited.loc[i].equals(original.loc[i])
    ]
    if st.button(f"💾 Save {len(changed)} changed row(s)", disabled=not changed):
        try:
            finish(f"{db.save_inline_edits(changed)} row(s) updated")
        except Exception as e:  # noqa: BLE001
            fail(e)

    st.divider()
    st.subheader("Form-based full edit")
    rid = row_picker("edit")
    if rid is None:
        return
    row = db.get_row(rid)
    recalc = st.checkbox("Recalculate Gross, Net & Profit from the values below", value=True, key=f"rc_{rid}")
    with st.form(f"edit_form_{rid}"):
        vals = sale_inputs(f"edit{rid}", defaults=row, auto=recalc)
        st.write("")
        ok = st.form_submit_button("💾 Update row")
    if ok:
        try:
            db.update_sale(rid, db.apply_formulas(vals) if recalc else vals)
            finish(f"Row {rid} updated")
        except Exception as e:  # noqa: BLE001
            fail(e)


def tab_quick():
    rid = row_picker("quick")
    if rid is None:
        return
    row = db.get_row(rid)
    a, b, c = st.columns(3)
    a.metric("Quantity sold", f"{num(row.get(C['qty'])):g}")
    b.metric("Net revenue", f"Rs {num(row.get(C['net'])):,.2f}")
    c.metric("Customer type", str(row[C["ctype"]]))
    st.markdown("**Quantity ± (recalculates Gross, Net & Profit)**")
    amt = st.number_input("Amount", min_value=1.0, value=1.0, step=1.0, key="q_amt")
    p1, p2 = st.columns(2)
    for label, delta, col in (("➕ Increase", amt, p1), ("➖ Decrease", -amt, p2)):
        if col.button(label, key=f"q_{label}", **FB):
            try:
                finish(f"Quantity is now {db.adjust_quantity(rid, delta):g}")
            except Exception as e:  # noqa: BLE001
                fail(e)
    st.markdown("**Switch customer type**")
    others = [t for t in db.get_choices().get(C["ctype"], []) if t != str(row[C["ctype"]])]
    for t, col in zip(others, st.columns(max(1, len(others)))):
        if col.button(f"🔁 Switch to {t}", key=f"q_ct_{t}", **FB):
            try:
                db.set_customer_type(rid, t)
                finish(f"Customer type → {t}")
            except Exception as e:  # noqa: BLE001
                fail(e)


def tab_delete():
    st.subheader("Remove one entry")
    rid = row_picker("del1")
    ok = st.checkbox("I understand this permanently removes the entry", key="del_ok")
    if st.button("🗑️ Remove entry", disabled=not (rid is not None and ok)):
        try:
            db.delete_sale(rid)
            finish(f"Row {rid} removed", "🗑️")
        except Exception as e:  # noqa: BLE001
            fail(e)
    st.divider()
    st.subheader("Batch removal")
    ids = row_picker("delm", multi=True)
    ok2 = st.checkbox(f"Yes, remove these {len(ids)} row(s)", key="delm_ok")
    if st.button("🗑️ Remove selected", disabled=not (ids and ok2)):
        try:
            finish(f"{db.bulk_delete_sales(ids)} row(s) removed in one transaction", "🗑️")
        except Exception as e:  # noqa: BLE001
            fail(e)


def tab_targets():
    st.caption("Edit or add category profit targets. They power the Profit vs Target breakdown.")
    edited = st.data_editor(
        db.get_targets(),
        num_rows="dynamic",
        hide_index=True,
        key="targets_editor",
        column_config={"Target_Profit": st.column_config.NumberColumn("Target_Profit (Rs)", min_value=0.0)},
        **FE,
    )
    if st.button("💾 Save targets"):
        try:
            finish(f"{db.save_targets(edited.to_dict('records'))} target(s) saved")
        except Exception as e:  # noqa: BLE001
            fail(e)


def page_crud():
    header("OPERATIONS", "Ledger & Ops", "Search, create, inspect, refine, or remove sales entries", health)
    tabs = st.tabs(
        [
            "❖ Explorer",
            "+ New Entry",
            "🔗 Linked Target",
            "◎ Deep View",
            "✎ Grid & Form Edit",
            "⚡ Instant Tweaks",
            "🗑️ Cleanup",
            "🎯 Benchmarks",
        ]
    )
    with tabs[0]:
        live(render_browse)()
    for tab, fn in zip(
        tabs[1:], (tab_add, tab_relational, tab_inspector, tab_edit, tab_quick, tab_delete, tab_targets)
    ):
        with tab:
            fn()


# =================================================================== PAGE 3
def tab_import():
    st.subheader("Batch CSV Ingestion")
    sample = normalize_dates_df(db.get_sales_page({}, 1, 3))
    meta = db.insertable_meta()
    template = (
        sample[[x for x in meta["col"] if x in sample.columns]]
        if not sample.empty
        else pd.DataFrame(columns=[clean_label(c) for c in meta["col"]])
    )
    st.download_button(
        "⬇ Download CSV template (matching schema columns)",
        template.to_csv(index=False),
        "sales_template.csv",
        "text/csv",
    )
    st.caption(
        f"Required: Category, Product, Quantity Sold, Rate per Unit (Rs). Dates are automatically formatted to {DATE_FMT}."
    )
    file = st.file_uploader("Upload a sales .csv", type=["csv"])
    if not file:
        return
    try:
        raw = pd.read_csv(file)
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read the CSV: {e}")
        return
    clean, errors = db.validate_csv(raw)
    for msg in errors:
        st.warning(msg)
    if clean is None or clean.empty:
        st.error("No valid rows to import.")
        return
    clean = normalize_dates_df(clean)
    st.markdown(f"**Preview — {len(clean):,} valid row(s)**")
    st.dataframe(clean.head(100), hide_index=True, **FD)
    if st.button(f"📥 Commit {len(clean):,} rows to MySQL"):
        try:
            finish(f"Committed {db.bulk_insert_sales(clean):,} rows", "📥")
        except Exception as e:  # noqa: BLE001
            fail(e)


def tab_export():
    st.subheader("Snapshot Export")
    ch = db.get_choices()
    c1, c2, c3 = st.columns(3)
    cat = c1.selectbox("Category", ["All"] + ch.get(C["category"], []), key="x_cat")
    ctype = c2.selectbox("Customer type", ["All"] + ch.get(C["ctype"], []), key="x_ctype")
    dow = c3.selectbox("Day of week", ["All"] + ch.get(C["dow"], []), key="x_dow")
    d_from, d_to = date_filter("x_date", "date range") if db.date_column() else (None, None)
    df = normalize_dates_df(
        db.get_sales_filtered({"category": cat, "ctype": ctype, "dow": dow, "date_from": d_from, "date_to": d_to})
    )
    st.caption(f"{len(df):,} row(s) match your filters · dates formatted as {DATE_FMT}")
    st.dataframe(df.head(500), hide_index=True, **FD)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    a, b = st.columns(2)
    a.download_button(
        "⬇ Export CSV",
        df.to_csv(index=False),
        f"dairy_sales_{stamp}.csv",
        "text/csv",
        disabled=df.empty,
        **FDL,
    )
    b.download_button(
        "⬇ Export Excel (.xlsx)",
        to_xlsx(df),
        f"dairy_sales_{stamp}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=df.empty,
        **FDL,
    )


def tab_reports():
    st.subheader("KPI Matrix (18 Reports)")
    name = st.selectbox("Choose a KPI", list(db.KPI_QUERIES))
    df = normalize_dates_df(db.run_kpi(name))
    st.dataframe(df, hide_index=True, **FD)
    nums = [x for x in df.columns[1:] if pd.api.types.is_numeric_dtype(df[x])]
    if 1 < len(df) <= 30 and nums and not pd.api.types.is_numeric_dtype(df[df.columns[0]]):
        fig = px.bar(
            df,
            x=df.columns[0],
            y=nums[0],
            color=df.columns[0],
            color_discrete_sequence=PALETTE,
            title=name,
        )
        fig.update_layout(showlegend=False, **LAYOUT)
        st.plotly_chart(fig, **FP)
    a, b = st.columns(2)
    a.download_button("⬇ This KPI as CSV", df.to_csv(index=False), "kpi.csv", "text/csv", **FDL)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for i, n in enumerate(db.KPI_QUERIES, 1):
            normalize_dates_df(db.run_kpi(n)).to_excel(w, index=False, sheet_name=f"KPI {i}")
    b.download_button(
        "⬇ All 18 KPIs Workbook (.xlsx)",
        buf.getvalue(),
        "dairy_kpis.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        **FDL,
    )


def page_import_export():
    header("VAULT & METRICS", "Vault & Analytics", "CSV ingestion, filtered exports, and 18 KPI reports", health)
    t1, t2, t3 = st.tabs(["📥 CSV Ingest", "📤 Snapshot Export", "📈 KPI Matrix"])
    with t1:
        tab_import()
    with t2:
        tab_export()
    with t3:
        tab_reports()


# =================================================================== PAGE 4
def render_logs():
    c1, c2 = st.columns(2)
    entity = c1.selectbox("Entity", ["All", "sale", "category_target"], key="log_entity")
    limit = c2.selectbox("Rows", [50, 100, 200, 500], index=2, key="log_limit")
    st.caption(f"Newest first · synced {dt.datetime.now():%H:%M:%S}")
    st.dataframe(normalize_dates_df(db.get_audit_logs(entity, limit)), hide_index=True, **FD)


def page_logs():
    header("HISTORY", "Chronicle Logs", "Every create, edit, and removal recorded in MySQL", health)
    live(render_logs)()


# =================================================================== router
{
    "✦  Dairy Pulse": page_dashboard,
    "❖  Ledger & Ops": page_crud,
    "◈  Vault & Analytics": page_import_export,
    "◎  Chronicle Logs": page_logs,
}[page]()
