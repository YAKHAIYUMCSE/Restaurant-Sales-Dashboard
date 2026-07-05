"""
FastAPI Backend — PRJ-053 Restaurant Sales Dashboard
PostgreSQL version (psycopg2 + pandas)
Run: uvicorn backend.main:app --reload --port 8000
"""
import os, random
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── DB connection ──────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/restaurant_db")


def get_con():
    return psycopg2.connect(DB_URL)


def get_df(query: str, params=None) -> pd.DataFrame:
    con = get_con()
    df  = pd.read_sql_query(query, con, params=params)
    con.close()
    return df


def scalar(query: str, params=None):
    con = get_con()
    cur = con.cursor()
    cur.execute(query, params or ())
    val = cur.fetchone()[0]
    con.close()
    return val


def date_clause(start, end, col="order_date"):
    """Return (where_fragment, params_list) for date filtering."""
    clauses, params = [], []
    if start:
        clauses.append(f"{col}::date >= %s")
        params.append(start)
    if end:
        clauses.append(f"{col}::date <= %s")
        params.append(end)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Restaurant Sales Dashboard API", version="3.0-pg")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ══════════════════════════════════════════════════════════════════
# WEEK 1 — Core Endpoints
# ══════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0-pg", "db": "postgresql",
            "timestamp": datetime.utcnow().isoformat()}


@app.get("/kpis")
def kpis(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)

    # Build completed clause
    if where:
        comp_where  = where + " AND status = 'Completed'"
        comp_params = params + []
    else:
        comp_where  = "WHERE status = 'Completed'"
        comp_params = []

    total_rev  = scalar(f"SELECT COALESCE(SUM(total_amount), 0) FROM orders {comp_where}", comp_params)
    total_ord  = scalar(f"SELECT COUNT(*) FROM orders {where}", params)
    comp_ord   = scalar(f"SELECT COUNT(*) FROM orders {comp_where}", comp_params)
    avg_ord    = round(float(total_rev) / int(comp_ord), 2) if comp_ord else 0
    uniq_cust  = scalar(f"SELECT COUNT(DISTINCT customer_id) FROM orders {where}", params)

    repeat_q   = f"""
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM orders {where}
            GROUP BY customer_id HAVING COUNT(*) > 1
        ) sub
    """
    repeat = scalar(repeat_q, params)

    if where:
        canc_where = where + " AND status = 'Cancelled'"
    else:
        canc_where = "WHERE status = 'Cancelled'"
    cancelled = scalar(f"SELECT COUNT(*) FROM orders {canc_where}", params)

    return {
        "total_revenue":    round(float(total_rev), 2),
        "total_orders":     int(total_ord),
        "completed_orders": int(comp_ord),
        "cancelled_orders": int(cancelled),
        "avg_order_value":  float(avg_ord),
        "unique_customers": int(uniq_cust),
        "repeat_customers": int(repeat),
    }


@app.get("/orders")
def orders(
    start:        Optional[str]   = None,
    end:          Optional[str]   = None,
    order_type:   Optional[str]   = None,
    payment_mode: Optional[str]   = None,
    status:       Optional[str]   = None,
    min_amount:   Optional[float] = None,
    max_amount:   Optional[float] = None,
    page:         int = Query(1,  ge=1),
    page_size:    int = Query(20, ge=1, le=100),
):
    clauses, params = [], []
    if start:        clauses.append("o.order_date::date >= %s");  params.append(start)
    if end:          clauses.append("o.order_date::date <= %s");  params.append(end)
    if order_type:   clauses.append("o.order_type = %s");          params.append(order_type)
    if payment_mode: clauses.append("o.payment_mode = %s");        params.append(payment_mode)
    if status:       clauses.append("o.status = %s");              params.append(status)
    if min_amount:   clauses.append("o.total_amount >= %s");       params.append(min_amount)
    if max_amount:   clauses.append("o.total_amount <= %s");       params.append(max_amount)

    where  = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    offset = (page - 1) * page_size
    total  = scalar(f"SELECT COUNT(*) FROM orders o {where}", params)

    rows = get_df(f"""
        SELECT o.order_id, c.name AS customer, o.order_date, o.order_type,
               o.payment_mode, o.total_amount, o.status
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        {where}
        ORDER BY o.order_date DESC
        LIMIT {page_size} OFFSET {offset}
    """, params)

    return {
        "total": int(total), "page": page, "page_size": page_size,
        "orders": rows.to_dict(orient="records"),
    }


@app.get("/bestsellers")
def bestsellers(
    start:    Optional[str] = None,
    end:      Optional[str] = None,
    top_n:    int = 10,
    category: Optional[str] = None,
):
    clauses = ["o.status = 'Completed'"]
    params  = []
    if start:    clauses.append("o.order_date::date >= %s"); params.append(start)
    if end:      clauses.append("o.order_date::date <= %s"); params.append(end)
    if category: clauses.append("m.category = %s");          params.append(category)
    where = "WHERE " + " AND ".join(clauses)

    return get_df(f"""
        SELECT m.name, m.category,
               SUM(oi.quantity)                                  AS total_qty,
               ROUND(SUM(oi.quantity * oi.unit_price)::numeric, 2) AS total_revenue,
               ROUND(SUM(oi.quantity * (oi.unit_price - m.cost))::numeric, 2) AS profit
        FROM order_items oi
        JOIN menu_items m ON oi.item_id = m.item_id
        JOIN orders     o ON oi.order_id = o.order_id
        {where}
        GROUP BY m.item_id, m.name, m.category
        ORDER BY total_qty DESC
        LIMIT {top_n}
    """, params).to_dict(orient="records")


@app.get("/peak-hours")
def peak_hours(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)
    return get_df(f"""
        SELECT EXTRACT(HOUR FROM order_date)::int AS hour,
               COUNT(*)                           AS order_count,
               ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM orders {where}
        GROUP BY hour
        ORDER BY hour
    """, params).to_dict(orient="records")


@app.get("/revenue-trend")
def revenue_trend(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)
    return get_df(f"""
        SELECT order_date::date AS day,
               COUNT(*)         AS order_count,
               ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM orders {where}
        GROUP BY day
        ORDER BY day
    """, params).to_dict(orient="records")


@app.get("/category-split")
def category_split(start: Optional[str] = None, end: Optional[str] = None):
    clauses = ["o.status = 'Completed'"]
    params  = []
    if start: clauses.append("o.order_date::date >= %s"); params.append(start)
    if end:   clauses.append("o.order_date::date <= %s"); params.append(end)
    where = "WHERE " + " AND ".join(clauses)
    return get_df(f"""
        SELECT m.category,
               SUM(oi.quantity) AS total_qty,
               ROUND(SUM(oi.quantity * oi.unit_price)::numeric, 2) AS revenue,
               ROUND(SUM(oi.quantity * (oi.unit_price - m.cost))::numeric, 2) AS profit
        FROM order_items oi
        JOIN menu_items m ON oi.item_id = m.item_id
        JOIN orders     o ON oi.order_id = o.order_id
        {where}
        GROUP BY m.category
        ORDER BY revenue DESC
    """, params).to_dict(orient="records")


@app.get("/order-type-split")
def order_type_split(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)
    return get_df(f"""
        SELECT order_type,
               COUNT(*) AS order_count,
               ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM orders {where}
        GROUP BY order_type
        ORDER BY order_count DESC
    """, params).to_dict(orient="records")


@app.get("/repeat-customers")
def repeat_customers(
    start: Optional[str] = None, end: Optional[str] = None, top_n: int = 10
):
    clauses, params = [], []
    if start: clauses.append("o.order_date::date >= %s"); params.append(start)
    if end:   clauses.append("o.order_date::date <= %s"); params.append(end)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return get_df(f"""
        SELECT c.name, c.phone, c.loyalty_pts,
               COUNT(o.order_id)                          AS visit_count,
               ROUND(SUM(o.total_amount)::numeric, 2)    AS total_spent,
               ROUND(AVG(o.total_amount)::numeric, 2)    AS avg_spent
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        {where}
        GROUP BY o.customer_id, c.name, c.phone, c.loyalty_pts
        HAVING COUNT(o.order_id) > 1
        ORDER BY visit_count DESC
        LIMIT {top_n}
    """, params).to_dict(orient="records")


# ══════════════════════════════════════════════════════════════════
# WEEK 2 — Advanced Analytics
# ══════════════════════════════════════════════════════════════════

@app.get("/menu-performance")
def menu_performance(start: Optional[str] = None, end: Optional[str] = None):
    clauses = ["o.status = 'Completed'"]
    params  = []
    if start: clauses.append("o.order_date::date >= %s"); params.append(start)
    if end:   clauses.append("o.order_date::date <= %s"); params.append(end)
    join_cond = " AND ".join(clauses)
    return get_df(f"""
        SELECT m.name, m.category, m.price, m.cost,
               COALESCE(SUM(oi.quantity), 0)                                   AS total_sold,
               ROUND(COALESCE(SUM(oi.quantity * oi.unit_price), 0)::numeric, 2) AS revenue,
               ROUND(COALESCE(SUM(oi.quantity * (oi.unit_price - m.cost)), 0)::numeric, 2) AS profit,
               ROUND(((m.price - m.cost) / m.price * 100)::numeric, 1)         AS margin_pct
        FROM menu_items m
        LEFT JOIN order_items oi ON m.item_id = oi.item_id
        LEFT JOIN orders o       ON oi.order_id = o.order_id AND {join_cond}
        GROUP BY m.item_id, m.name, m.category, m.price, m.cost
        ORDER BY profit DESC
    """, params).to_dict(orient="records")


@app.get("/weekly-trend")
def weekly_trend(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)
    return get_df(f"""
        SELECT TO_CHAR(order_date, 'IYYY-IW') AS week,
               COUNT(*)                        AS order_count,
               ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM orders {where}
        GROUP BY week
        ORDER BY week
    """, params).to_dict(orient="records")


@app.get("/payment-split")
def payment_split(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)
    return get_df(f"""
        SELECT payment_mode,
               COUNT(*) AS order_count,
               ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM orders {where}
        GROUP BY payment_mode
        ORDER BY revenue DESC
    """, params).to_dict(orient="records")


@app.get("/customer-profile/{customer_id}")
def customer_profile(customer_id: int):
    con = get_con()
    cust = pd.read_sql(
        "SELECT * FROM customers WHERE customer_id = %s",
        con, params=(customer_id,)
    )
    if cust.empty:
        raise HTTPException(404, "Customer not found")
    recent = pd.read_sql("""
        SELECT order_id, order_date, order_type, payment_mode, total_amount, status
        FROM orders
        WHERE customer_id = %s
        ORDER BY order_date DESC
        LIMIT 10
    """, con, params=(customer_id,))
    con.close()
    return {
        "customer":      cust.to_dict(orient="records")[0],
        "recent_orders": recent.to_dict(orient="records"),
        "total_orders":  len(recent),
        "total_spent":   round(float(recent["total_amount"].sum()), 2),
    }


@app.get("/revenue-forecast")
def revenue_forecast(days: int = 7):
    """7-day moving average forecast."""
    df = get_df("""
        SELECT order_date::date AS day,
               ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM orders
        WHERE status = 'Completed'
        GROUP BY day
        ORDER BY day
    """)
    if df.empty:
        return []
    df["ma7"]     = df["revenue"].rolling(7, min_periods=1).mean()
    last_avg      = df["ma7"].iloc[-1]
    last_date     = pd.to_datetime(df["day"].iloc[-1])
    forecast      = []
    for i in range(1, days + 1):
        d = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
        forecast.append({
            "day":      d,
            "forecast": round(float(last_avg) * random.uniform(0.9, 1.1), 2),
            "type":     "forecast",
        })
    return forecast


@app.get("/top-customers")
def top_customers(
    start: Optional[str] = None, end: Optional[str] = None, top_n: int = 10
):
    clauses, params = [], []
    if start: clauses.append("o.order_date::date >= %s"); params.append(start)
    if end:   clauses.append("o.order_date::date <= %s"); params.append(end)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return get_df(f"""
        SELECT c.name, c.phone, c.loyalty_pts,
               COUNT(o.order_id)                       AS order_count,
               ROUND(SUM(o.total_amount)::numeric, 2)  AS total_spent
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        {where}
        GROUP BY o.customer_id, c.name, c.phone, c.loyalty_pts
        ORDER BY total_spent DESC
        LIMIT {top_n}
    """, params).to_dict(orient="records")


@app.get("/daily-comparison")
def daily_comparison(start: Optional[str] = None, end: Optional[str] = None):
    where, params = date_clause(start, end)
    return get_df(f"""
        SELECT TO_CHAR(order_date, 'Day') AS day_name,
               EXTRACT(DOW FROM order_date)::int AS day_num,
               COUNT(*) AS order_count,
               ROUND(AVG(total_amount)::numeric, 2) AS avg_revenue
        FROM orders {where}
        GROUP BY day_num, day_name
        ORDER BY day_num
    """, params).to_dict(orient="records")


# ══════════════════════════════════════════════════════════════════
# WEEK 3 — Reports & Export
# ══════════════════════════════════════════════════════════════════

@app.get("/summary-report")
def summary_report(start: Optional[str] = None, end: Optional[str] = None):
    return {
        "period":        {"start": start, "end": end},
        "kpis":          kpis(start, end),
        "bestsellers":   bestsellers(start, end, top_n=5),
        "categories":    category_split(start, end),
        "order_types":   order_type_split(start, end),
        "payments":      payment_split(start, end),
        "top_customers": repeat_customers(start, end, top_n=5),
        "generated_at":  datetime.utcnow().isoformat(),
    }


@app.get("/menu-items")
def menu_items():
    return get_df("SELECT * FROM menu_items ORDER BY category, name").to_dict(orient="records")


@app.get("/staff")
def staff():
    return get_df("SELECT * FROM staff ORDER BY role").to_dict(orient="records")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
