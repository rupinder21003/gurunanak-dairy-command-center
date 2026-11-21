"""db.py - MySQL layer for dairy_data.gurunanak_dairy_data (pool, health check, all CRUD + KPI SQL).

Column handling is metadata-driven: the app reads the real table structure from information_schema,
so extra columns in your table (Date, Invoice No, ...) are picked up automatically.
"""
import datetime as dt
import os
from contextlib import contextmanager
from decimal import Decimal

import mysql.connector
import pandas as pd
import streamlit as st
from mysql.connector import pooling

TABLE = "gurunanak_dairy_data"
TARGETS = "category_targets"
CACHE_TTL = 4

# Column names exactly as used in your SQL script
COL = {
    "category": "Category", "product": "Product", "ctype": "Customer Type", "qty": "Quantity Sold",
    "unit": "Unit", "rate": "Rate per Unit (Rs)", "gross": "Gross Revenue (Rs)", "disc": "Discount (Rs)",
    "net": "Net Revenue (Rs)", "cogs": "Cost of Goods (Rs)", "opex": "Operating Cost (Rs)",
    "profit": "Net Profit (Rs)", "dow": "Day of Week",
}
DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
INT_TYPES = {"tinyint", "smallint", "mediumint", "int", "bigint"}
NUM_TYPES = {"decimal", "float", "double"}
TEXT_TYPES = {"char", "varchar", "tinytext", "text", "mediumtext", "longtext", "enum"}
DATE_ONLY, DT_TYPES = "date", {"datetime", "timestamp"}


def q(name):
    return "`" + str(name).replace("`", "``") + "`"


def c(key):
    return q(COL[key])


# --------------------------------------------------------------------------
# Connection pool + health check
# --------------------------------------------------------------------------
_DEFAULTS = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "123456", "database": "dairy_data"}


def _read_secrets_file():
    """Reads the [mysql] section of .streamlit/secrets.toml ourselves (so Streamlit never shows a 'No secrets' error)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd(), os.path.expanduser("~")):
        path = os.path.join(base, ".streamlit", "secrets.toml")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            try:
                import tomllib  # Python 3.11+
                return dict(tomllib.loads(text).get("mysql", {}))
            except ImportError:
                cfg, in_mysql = {}, False
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("["):
                        in_mysql = line == "[mysql]"
                    elif in_mysql and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip().strip('"').strip("'")
                return cfg
        except Exception:  # noqa: BLE001
            continue
    return {}


def _settings():
    """secrets.toml [mysql] if present, otherwise the local defaults (127.0.0.1 / root / 123456 / dairy_data)."""
    s = {**_DEFAULTS, **_read_secrets_file()}
    s["port"] = int(s["port"])
    return s


@st.cache_resource(show_spinner=False)
def get_pool():
    s = _settings()
    cfg = {"host": s["host"], "port": int(s["port"]), "user": s["user"], "password": s["password"]}
    if s.get("ssl_ca"):
        cfg.update(ssl_ca=s["ssl_ca"], ssl_verify_cert=True)
    boot = mysql.connector.connect(**cfg)  # auto-create the database if it does not exist
    try:
        cur = boot.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {q(s['database'])}")
        boot.commit()
        cur.close()
    finally:
        boot.close()
    return pooling.MySQLConnectionPool(pool_name="dairy_pool", pool_size=5, pool_reset_session=True,
                                       database=s["database"], **cfg)


@contextmanager
def get_conn():
    conn = get_pool().get_connection()
    try:
        conn.ping(reconnect=True, attempts=2, delay=1)  # health check on every checkout
        yield conn
    finally:
        conn.close()


def check_connection():
    s = _settings()
    info = {"ok": False, "version": "", "host": s["host"], "port": s["port"], "error": ""}
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT VERSION()")
            info["version"] = cur.fetchone()[0]
            cur.close()
        info["ok"] = True
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
    return info


def schema_ready():
    """Returns (ok, message)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        found = {str(r[0]).lower() for r in cur.fetchall()}
        cur.close()
    missing = [t for t in (TABLE, TARGETS, "audit_logs") if t not in found]
    if missing:
        return False, f"Missing table(s): {', '.join(missing)}. Run schema.sql in MySQL Workbench."
    if pk_info() is None:
        return False, f"`{TABLE}` has no single-column primary key. Run schema.sql in MySQL Workbench (it adds an `id` column)."
    return True, ""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _clean(df):
    for col in df.columns:
        s = df[col]
        if s.dtype != object:
            continue
        if s.map(lambda x: isinstance(x, (bytes, bytearray))).any():
            df[col] = s.map(lambda x: x.decode() if isinstance(x, (bytes, bytearray)) else x)
        elif s.map(lambda x: isinstance(x, Decimal)).any():
            df[col] = s.astype(float)
        elif s.map(lambda x: isinstance(x, dt.date)).any():
            df[col] = pd.to_datetime(s)
    return df


def query_df(sql, params=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params) if params else cur.execute(sql)
        df = pd.DataFrame(cur.fetchall(), columns=cur.column_names)
        cur.close()
    return _clean(df)


def _write(work):
    """Run work(cursor) inside ONE transaction: commit on success, rollback on any error."""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            result = work(cur)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def _log(cur, action, entity, entity_id, details):
    cur.execute("INSERT INTO audit_logs (action, entity, entity_id, details) VALUES (%s, %s, %s, %s)",
                (action, entity, str(entity_id), details))


def py(v, dtype):
    """Convert numpy / pandas values to something mysql-connector accepts."""
    if v is None or pd.isna(v):
        return None
    if dtype in INT_TYPES:
        return int(round(float(v)))
    if dtype in NUM_TYPES:
        return Decimal(str(round(float(v), 4)))
    if dtype in DT_TYPES:
        return pd.Timestamp(v).to_pydatetime()
    if dtype == DATE_ONLY:
        return pd.Timestamp(v).date()
    return str(v)


# --------------------------------------------------------------------------
# Table metadata
# --------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def table_meta():
    return query_df(
        "SELECT COLUMN_NAME AS col, DATA_TYPE AS dtype, COLUMN_KEY AS ckey, EXTRA AS extra "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
        "ORDER BY ORDINAL_POSITION", (TABLE,))


def dtypes():
    m = table_meta()
    return dict(zip(m["col"], m["dtype"].str.lower()))


def pk_info():
    """(column_name, is_auto_increment) for a single-column primary key, else None."""
    m = table_meta()
    pk = m[m["ckey"] == "PRI"]
    if len(pk) != 1:
        return None
    return pk.iloc[0]["col"], "auto_increment" in str(pk.iloc[0]["extra"]).lower()


def insertable_meta():
    m = table_meta()
    return m[~m["extra"].str.lower().str.contains("auto_increment|generated", regex=True)].reset_index(drop=True)


def date_column():
    for col, t in dtypes().items():
        if t == DATE_ONLY or t in DT_TYPES:
            return col
    return None


@st.cache_data(ttl=30, show_spinner=False)
def get_choices():
    cols, out = set(table_meta()["col"]), {}
    for key in ("category", "ctype", "dow", "unit"):
        if COL[key] in cols:
            df = query_df(f"SELECT DISTINCT {c(key)} AS v FROM {q(TABLE)} WHERE {c(key)} IS NOT NULL ORDER BY 1")
            out[COL[key]] = df["v"].astype(str).tolist()
    return out


def apply_formulas(vals):
    """Gross = Qty x Rate;  Net = Gross - Discount;  Profit = Net - COGS - Operating cost."""
    cols = set(table_meta()["col"])
    f = lambda k: float(vals.get(COL[k]) or 0)  # noqa: E731
    gross = round(f("qty") * f("rate"), 2)
    net = round(gross - f("disc"), 2)
    profit = round(net - f("cogs") - f("opex"), 2)
    for key, val in (("gross", gross), ("net", net), ("profit", profit)):
        if COL[key] in cols:
            vals[COL[key]] = val
    return vals


# --------------------------------------------------------------------------
# READ (cached 4s; the app clears the cache after every write)
# --------------------------------------------------------------------------
def _sale_where(f):
    where, params = ["1=1"], []
    if f.get("search"):
        s = f["search"].strip()
        parts, ps = [], []
        for col, t in dtypes().items():
            if t in TEXT_TYPES:
                parts.append(f"{q(col)} LIKE %s")
                ps.append(f"%{s}%")
        pk = pk_info()
        if pk:
            parts.append(f"CAST({q(pk[0])} AS CHAR) = %s")
            ps.append(s)
        if parts:
            where.append("(" + " OR ".join(parts) + ")")
            params += ps
    for key in ("category", "ctype", "dow"):
        v = f.get(key)
        if v and v != "All":
            where.append(f"{c(key)} = %s")
            params.append(v)
    if f.get("min_net"):
        where.append(f"{c('net')} >= %s")
        params.append(float(f["min_net"]))
    if f.get("max_net"):
        where.append(f"{c('net')} <= %s")
        params.append(float(f["max_net"]))
    dcol = date_column()
    if dcol and f.get("date_from"):
        where.append(f"DATE({q(dcol)}) >= %s")
        params.append(f["date_from"])
    if dcol and f.get("date_to"):
        where.append(f"DATE({q(dcol)}) <= %s")
        params.append(f["date_to"])
    return " AND ".join(where), params


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def count_sales(filters):
    where, params = _sale_where(filters)
    return int(query_df(f"SELECT COUNT(*) AS n FROM {q(TABLE)} WHERE {where}", params).iloc[0]["n"])


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_sales_page(filters, page, page_size):
    where, params = _sale_where(filters)
    pk = pk_info()[0]
    return query_df(f"SELECT * FROM {q(TABLE)} WHERE {where} ORDER BY {q(pk)} LIMIT %s OFFSET %s",
                    params + [int(page_size), (int(page) - 1) * int(page_size)])


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_sales_filtered(filters):
    where, params = _sale_where(filters)
    return query_df(f"SELECT * FROM {q(TABLE)} WHERE {where} ORDER BY {q(pk_info()[0])}", params)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_row(pk_value):
    df = query_df(f"SELECT * FROM {q(TABLE)} WHERE {q(pk_info()[0])} = %s", (pk_value,))
    return df.to_dict("records")[0] if not df.empty else None


# 6. Inspector: JOIN with category_targets + category context + same-product history
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_row_detail(pk_value):
    return query_df(
        f"SELECT s.*, t.Target_Profit AS Category_Target FROM {q(TABLE)} s "
        f"LEFT JOIN {q(TARGETS)} t ON t.Category = s.{c('category')} WHERE s.{q(pk_info()[0])} = %s", (pk_value,))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_category_context(category):
    return query_df(
        f"SELECT COUNT(*) AS transactions, COALESCE(SUM({c('qty')}),0) AS quantity, "
        f"COALESCE(SUM({c('net')}),0) AS revenue, COALESCE(SUM({c('profit')}),0) AS profit "
        f"FROM {q(TABLE)} WHERE {c('category')} = %s", (category,)).iloc[0].to_dict()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_related(product):
    return query_df(f"SELECT * FROM {q(TABLE)} WHERE {c('product')} = %s ORDER BY {q(pk_info()[0])} DESC LIMIT 25",
                    (product,))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_targets():
    return query_df(f"SELECT Category, Target_Profit FROM {q(TARGETS)} ORDER BY Category")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_audit_logs(entity="All", limit=200):
    if entity != "All":
        return query_df("SELECT log_id, created_at, action, entity, entity_id, details FROM audit_logs "
                        "WHERE entity = %s ORDER BY log_id DESC LIMIT %s", (entity, int(limit)))
    return query_df("SELECT log_id, created_at, action, entity, entity_id, details FROM audit_logs "
                    "ORDER BY log_id DESC LIMIT %s", (int(limit),))


# ---- dashboard aggregates ----
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_kpis():
    return query_df(
        f"SELECT COUNT(*) AS transactions, COALESCE(SUM({c('qty')}),0) AS volume, "
        f"COALESCE(SUM({c('gross')}),0) AS gross, COALESCE(SUM({c('disc')}),0) AS discount, "
        f"COALESCE(SUM({c('net')}),0) AS net_revenue, COALESCE(SUM({c('cogs')}),0) AS cogs, "
        f"COALESCE(SUM({c('opex')}),0) AS opex, COALESCE(SUM({c('profit')}),0) AS net_profit, "
        f"COALESCE(AVG({c('net')}),0) AS avg_order FROM {q(TABLE)}").iloc[0].to_dict()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_category_perf():
    return query_df(
        f"SELECT {c('category')} AS category, COUNT(*) AS orders, SUM({c('qty')}) AS quantity, "
        f"SUM({c('net')}) AS revenue, SUM({c('profit')}) AS profit FROM {q(TABLE)} "
        f"GROUP BY {c('category')} ORDER BY revenue DESC")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_dow_perf():
    return query_df(
        f"SELECT {c('dow')} AS day_of_week, COUNT(*) AS sales, SUM({c('net')}) AS revenue, "
        f"SUM({c('profit')}) AS profit FROM {q(TABLE)} GROUP BY {c('dow')}")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctype_split():
    return query_df(
        f"SELECT {c('ctype')} AS customer_type, COUNT(*) AS orders, SUM({c('net')}) AS revenue "
        f"FROM {q(TABLE)} GROUP BY {c('ctype')}")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_daily_trend():
    dcol = date_column()
    if not dcol:
        return pd.DataFrame()
    return query_df(
        f"SELECT DATE({q(dcol)}) AS day, SUM({c('net')}) AS revenue, SUM({c('profit')}) AS profit "
        f"FROM {q(TABLE)} WHERE {q(dcol)} IS NOT NULL GROUP BY DATE({q(dcol)}) ORDER BY day")


# --------------------------------------------------------------------------
# CREATE
# --------------------------------------------------------------------------
def _insert_sale(cur, values):
    cols, dt_ = list(values), dtypes()
    cur.execute(f"INSERT INTO {q(TABLE)} ({', '.join(q(x) for x in cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                [py(values[x], dt_[x]) for x in cols])
    return cur.lastrowid


# 1. Single record
def add_sale(values):
    def work(cur):
        rid = _insert_sale(cur, values)
        _log(cur, "CREATE", "sale", rid, f"{values.get(COL['product'])} / {values.get(COL['category'])}")
        return rid
    return _write(work)


# 2. Relational: sale + category_targets row (if the category is new) in ONE transaction
def add_sale_with_target(values, target_if_new):
    def work(cur):
        rid = _insert_sale(cur, values)
        cat = values[COL["category"]]
        cur.execute(f"SELECT COUNT(*) FROM {q(TARGETS)} WHERE Category = %s", (cat,))
        created = False
        if cur.fetchone()[0] == 0:
            cur.execute(f"INSERT INTO {q(TARGETS)} (Category, Target_Profit) VALUES (%s, %s)",
                        (cat, Decimal(str(round(float(target_if_new), 2)))))
            _log(cur, "CREATE", "category_target", cat, f"Target set to {target_if_new}")
            created = True
        _log(cur, "CREATE", "sale", rid, f"{values.get(COL['product'])} / {cat}")
        return rid, created
    return _write(work)


# 3. Bulk CSV
def validate_csv(df):
    meta = insertable_meta()
    known = {r.col.lower(): (r.col, r.dtype.lower()) for r in meta.itertuples()}
    df = df.copy()
    df.columns = [str(x).strip() for x in df.columns]
    rename = {x: known[x.lower()][0] for x in df.columns if x.lower() in known}
    errors = []
    unknown = [x for x in df.columns if x not in rename]
    if unknown:
        errors.append("Ignored unknown column(s): " + ", ".join(unknown))
    df = df.rename(columns=rename)[list(rename.values())]
    base = [COL[k] for k in ("category", "product", "qty", "rate")]
    missing = [b for b in base if b not in df.columns]
    if missing:
        return None, errors + [f"Missing required column(s): {', '.join(missing)}"]
    bad = pd.Series(False, index=df.index)
    for col in df.columns:
        t = known[col.lower()][1]
        if t in INT_TYPES or t in NUM_TYPES:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            bad |= df[col].isna() & (col in (COL["qty"], COL["rate"]))
            df[col] = df[col].fillna(0)
            bad |= df[col] < 0
        elif t == DATE_ONLY or t in DT_TYPES:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            bad |= df[col].isna()
        else:
            txt = df[col].astype(str).str.strip()
            df[col] = txt.where(df[col].notna() & (txt != ""), None)
            bad |= df[col].isna() & (col in (COL["category"], COL["product"]))
    zero = lambda col: df[col] if col in df.columns else 0  # noqa: E731
    cols = set(table_meta()["col"])
    if COL["gross"] in cols and COL["gross"] not in df.columns:
        df[COL["gross"]] = (df[COL["qty"]] * df[COL["rate"]]).round(2)
    if COL["net"] in cols and COL["net"] not in df.columns:
        df[COL["net"]] = (df[COL["gross"]] - zero(COL["disc"])).round(2)
    if COL["profit"] in cols and COL["profit"] not in df.columns:
        df[COL["profit"]] = (df[COL["net"]] - zero(COL["cogs"]) - zero(COL["opex"])).round(2)
    if bad.any():
        errors.append("Invalid rows skipped (CSV line numbers): " + ", ".join(str(i + 2) for i in df.index[bad]))
    return df[~bad].reset_index(drop=True), errors


def bulk_insert_sales(df):
    cols, dt_ = list(df.columns), dtypes()
    rows = [[py(v, dt_[col]) for col, v in zip(cols, rec)] for rec in df.itertuples(index=False, name=None)]

    def work(cur):
        cur.executemany(f"INSERT INTO {q(TABLE)} ({', '.join(q(x) for x in cols)}) "
                        f"VALUES ({', '.join(['%s'] * len(cols))})", rows)
        _log(cur, "IMPORT", "sale", "bulk", f"CSV import of {len(rows)} row(s)")
        return len(rows)
    return _write(work)


# --------------------------------------------------------------------------
# UPDATE
# --------------------------------------------------------------------------
def _update_row(cur, pk_value, values):
    pk, dt_ = pk_info()[0], dtypes()
    cols = [x for x in values if x != pk and x in dt_]
    cur.execute(f"UPDATE {q(TABLE)} SET {', '.join(q(x) + ' = %s' for x in cols)} WHERE {q(pk)} = %s",
                [py(values[x], dt_[x]) for x in cols] + [pk_value])


# 7. Inline table editing (many rows, one transaction)
def save_inline_edits(rows):
    pk = pk_info()[0]

    def work(cur):
        for r in rows:
            _update_row(cur, r[pk], r)
        _log(cur, "UPDATE", "sale", ",".join(str(r[pk]) for r in rows), f"Inline edit of {len(rows)} row(s)")
        return len(rows)
    return _write(work)


# 8. Form-based full edit
def update_sale(pk_value, values):
    def work(cur):
        _update_row(cur, pk_value, values)
        _log(cur, "UPDATE", "sale", pk_value, f"Full edit: {values.get(COL['product'])}")
    return _write(work)


# 9a. Quick +/- quantity (recalculates Gross / Net / Profit)
def adjust_quantity(pk_value, delta, recalc=True):
    pk = pk_info()[0]

    def work(cur):
        cur.execute(f"SELECT * FROM {q(TABLE)} WHERE {q(pk)} = %s FOR UPDATE", (pk_value,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Row not found.")
        rec = dict(zip(cur.column_names, row))
        old = float(rec[COL["qty"]])
        new = old + float(delta)
        if new <= 0:
            raise ValueError(f"Quantity must stay above zero (current: {old:g}).")
        rec[COL["qty"]] = new
        upd = {COL["qty"]: new}
        if recalc:
            calc = apply_formulas(dict(rec))
            upd.update({COL[k]: calc[COL[k]] for k in ("gross", "net", "profit") if COL[k] in calc})
        _update_row(cur, pk_value, upd)
        _log(cur, "UPDATE", "sale", pk_value, f"Quantity {old:g} -> {new:g}")
        return new
    return _write(work)


# 9b. Quick Customer Type switch (Retail <-> Wholesale)
def set_customer_type(pk_value, new_type):
    def work(cur):
        _update_row(cur, pk_value, {COL["ctype"]: new_type})
        _log(cur, "UPDATE", "sale", pk_value, f"Customer Type -> {new_type}")
    return _write(work)


def save_targets(rows):
    def work(cur):
        n = 0
        for r in rows:
            cat = str(r["Category"]).strip()
            if not cat or pd.isna(r["Target_Profit"]):
                continue
            tgt = Decimal(str(round(float(r["Target_Profit"]), 2)))
            cur.execute(f"SELECT COUNT(*) FROM {q(TARGETS)} WHERE Category = %s", (cat,))
            if cur.fetchone()[0]:
                cur.execute(f"UPDATE {q(TARGETS)} SET Target_Profit = %s WHERE Category = %s", (tgt, cat))
            else:
                cur.execute(f"INSERT INTO {q(TARGETS)} (Category, Target_Profit) VALUES (%s, %s)", (cat, tgt))
            n += 1
        _log(cur, "UPDATE", "category_target", "bulk", f"Saved {n} target(s)")
        return n
    return _write(work)


# --------------------------------------------------------------------------
# DELETE
# --------------------------------------------------------------------------
# 10. Single record
def delete_sale(pk_value):
    pk = pk_info()[0]

    def work(cur):
        cur.execute(f"DELETE FROM {q(TABLE)} WHERE {q(pk)} = %s", (pk_value,))
        n = cur.rowcount
        _log(cur, "DELETE", "sale", pk_value, f"Deleted row {pk_value}")
        return n
    return _write(work)


# 11. Bulk delete (one transaction)
def bulk_delete_sales(ids):
    if not ids:
        raise ValueError("Select at least one row.")
    pk = pk_info()[0]

    def work(cur):
        cur.execute(f"DELETE FROM {q(TABLE)} WHERE {q(pk)} IN ({', '.join(['%s'] * len(ids))})", list(ids))
        n = cur.rowcount
        _log(cur, "DELETE", "sale", ",".join(map(str, ids)), f"Bulk deleted {n} row(s)")
        return n
    return _write(work)


# --------------------------------------------------------------------------
# Your 18 KPI queries (from dairy data.sql) - run from Reports tab
# --------------------------------------------------------------------------
_T = "gurunanak_dairy_data"
KPI_QUERIES = {
    "KPI 1: Overall Financial Summary": f"""SELECT COUNT(*) AS Total_Transactions, SUM(`Gross Revenue (Rs)`) AS Total_Gross_Revenue,
 SUM(`Discount (Rs)`) AS Total_Discount_Given, SUM(`Net Revenue (Rs)`) AS Total_Net_Revenue,
 SUM(`Cost of Goods (Rs)`) AS Total_COGS, SUM(`Operating Cost (Rs)`) AS Total_Operating_Cost,
 SUM(`Net Profit (Rs)`) AS Total_Net_Profit FROM {_T}""",
    "KPI 2: Overall Profit Margin (%)": f"""SELECT SUM(`Net Revenue (Rs)`) AS Net_Revenue, SUM(`Net Profit (Rs)`) AS Net_Profit,
 ROUND((SUM(`Net Profit (Rs)`) / SUM(`Net Revenue (Rs)`)) * 100, 2) AS Profit_Margin_Percent FROM {_T}""",
    "KPI 3: Category-Wise Performance": f"""SELECT Category, COUNT(*) AS Total_Orders, SUM(`Quantity Sold`) AS Total_Quantity,
 SUM(`Net Revenue (Rs)`) AS Category_Revenue, SUM(`Net Profit (Rs)`) AS Category_Profit
 FROM {_T} GROUP BY Category ORDER BY Category_Revenue DESC""",
    "KPI 4: Top 5 Best-Selling Products": f"""SELECT Product, Category, SUM(`Quantity Sold`) AS Total_Quantity_Sold,
 SUM(`Net Revenue (Rs)`) AS Total_Revenue FROM {_T} GROUP BY Product, Category ORDER BY Total_Revenue DESC LIMIT 5""",
    "KPI 5: Retail vs Wholesale": f"""SELECT `Customer Type`, COUNT(*) AS Total_Orders, SUM(`Net Revenue (Rs)`) AS Total_Revenue,
 SUM(`Discount (Rs)`) AS Total_Discount, ROUND(AVG(`Net Revenue (Rs)`), 2) AS Average_Order_Value
 FROM {_T} GROUP BY `Customer Type`""",
    "KPI 6: Peak Sales Days": f"""SELECT `Day of Week`, COUNT(*) AS Total_Sales_Count, SUM(`Net Revenue (Rs)`) AS Total_Revenue,
 SUM(`Net Profit (Rs)`) AS Total_Profit FROM {_T} GROUP BY `Day of Week` ORDER BY Total_Revenue DESC""",
    "KPI 7: High-Value Transactions (> Rs 500)": f"""SELECT Category, Product, `Customer Type`, `Quantity Sold`, `Net Revenue (Rs)`,
 `Net Profit (Rs)` FROM {_T} WHERE `Net Revenue (Rs)` > 500 ORDER BY `Net Revenue (Rs)` DESC""",
    "KPI 8: Products With Above-Average Profit": f"""SELECT Product, SUM(`Net Profit (Rs)`) AS Product_Total_Profit FROM {_T}
 GROUP BY Product HAVING SUM(`Net Profit (Rs)`) > (SELECT AVG(Product_Profit) FROM
 (SELECT SUM(`Net Profit (Rs)`) AS Product_Profit FROM {_T} GROUP BY Product) AS SubTable)
 ORDER BY Product_Total_Profit DESC""",
    "KPI 9: COGS vs Operating Cost Ratio": f"""SELECT SUM(`Net Revenue (Rs)`) AS Total_Revenue, SUM(`Cost of Goods (Rs)`) AS Total_COGS,
 ROUND((SUM(`Cost of Goods (Rs)`) / SUM(`Net Revenue (Rs)`)) * 100, 2) AS COGS_Percent_Of_Revenue,
 SUM(`Operating Cost (Rs)`) AS Total_Operating_Cost,
 ROUND((SUM(`Operating Cost (Rs)`) / SUM(`Net Revenue (Rs)`)) * 100, 2) AS Operating_Cost_Percent_Of_Revenue FROM {_T}""",
    "KPI 10: KPI Card Metrics": f"""SELECT COUNT(*) AS Total_Orders, SUM(`Quantity Sold`) AS Total_Volume_Sold,
 ROUND(AVG(`Quantity Sold`), 2) AS Average_Order_Quantity, ROUND(AVG(`Rate per Unit (Rs)`), 2) AS Average_Unit_Price FROM {_T}""",
    "KPI 11: Category Percentage Share": f"""SELECT Category, SUM(`Quantity Sold`) AS Total_Units,
 ROUND(SUM(`Quantity Sold`) * 100.0 / (SELECT SUM(`Quantity Sold`) FROM {_T}), 2) AS Volume_Share_Percent
 FROM {_T} GROUP BY Category ORDER BY Total_Units DESC""",
    "KPI 12: Profitability by Category": f"""SELECT Category, ROUND(AVG(`Rate per Unit (Rs)`), 2) AS Avg_Selling_Price,
 SUM(`Quantity Sold`) AS Total_Quantity FROM {_T} GROUP BY Category ORDER BY Total_Quantity DESC""",
    "KPI 13: Weekday vs Weekend": f"""SELECT CASE WHEN `Day of Week` IN ('Saturday', 'Sunday') THEN 'Weekend' ELSE 'Weekday' END AS Day_Type,
 COUNT(*) AS Total_Transactions, SUM(`Quantity Sold`) AS Total_Quantity_Sold FROM {_T}
 GROUP BY CASE WHEN `Day of Week` IN ('Saturday', 'Sunday') THEN 'Weekend' ELSE 'Weekday' END""",
    "KPI 14: Unit Measurement Distribution": f"""SELECT Unit, COUNT(*) AS Total_Products_Sold, SUM(`Quantity Sold`) AS Total_Volume
 FROM {_T} GROUP BY Unit ORDER BY Total_Volume DESC""",
    "KPI 15: Top 5 Most Frequently Ordered": f"""SELECT Product, Category, COUNT(*) AS Times_Ordered, SUM(`Quantity Sold`) AS Total_Quantity
 FROM {_T} GROUP BY Product, Category ORDER BY Times_Ordered DESC LIMIT 5""",
    "KPI 16: Bottom 5 Least Selling": f"""SELECT Product, Category, SUM(`Quantity Sold`) AS Total_Quantity FROM {_T}
 GROUP BY Product, Category ORDER BY Total_Quantity ASC LIMIT 5""",
    "KPI 17: Customer Type Volume Comparison": f"""SELECT `Customer Type`, COUNT(*) AS Transaction_Count, SUM(`Quantity Sold`) AS Total_Units_Sold,
 ROUND(AVG(`Quantity Sold`), 2) AS Avg_Units_Per_Order FROM {_T} GROUP BY `Customer Type`""",
    "KPI 18: Daily Average Volume by Day of Week": f"""SELECT `Day of Week`, ROUND(AVG(`Quantity Sold`), 2) AS Avg_Daily_Quantity,
 SUM(`Quantity Sold`) AS Total_Day_Quantity FROM {_T} GROUP BY `Day of Week` ORDER BY Total_Day_Quantity DESC""",
}


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def run_kpi(name):
    return query_df(KPI_QUERIES[name])