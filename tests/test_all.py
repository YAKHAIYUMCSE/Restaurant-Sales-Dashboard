"""
Automated Tests — PRJ-053 Restaurant Sales Dashboard (PostgreSQL)
==================================================================

Covers:
  - Health check
  - Week 1 core endpoints (KPIs, orders, bestsellers, peak hours,
    revenue trend, category split, order-type split, repeat customers)
  - Filter / query-param validation (date range, order type, payment
    mode, amount range, pagination)
  - Week 2 analytics endpoints (menu performance, weekly trend,
    payment split, customer profile, revenue forecast, top customers,
    daily comparison)
  - Week 3 endpoints (summary report, menu items, staff)
  - Error handling for invalid input (bad customer id, bad page, etc.)

Run:
    # from the project root, with PostgreSQL running and seeded
    pip install pytest
    python data/seed_data.py
    pytest tests/test_all.py -v

Notes:
  These tests hit the FastAPI app directly via TestClient (no live
  uvicorn server needed), but they DO require a running, seeded
  PostgreSQL database, since the endpoints read/write through
  psycopg2 rather than a mock/in-memory layer.
"""
import os
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

# Make `backend` importable when running pytest from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402

client = TestClient(app)


# ══════════════════════════════════════════════════════════════════
# Fixtures / helpers
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def date_range():
    """A safe date window that should have seeded data (last 30 days of the 90-day seed)."""
    end = date(2025, 5, 1)
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()


def assert_ok(resp):
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


# ══════════════════════════════════════════════════════════════════
# Health check
# ══════════════════════════════════════════════════════════════════

def test_health():
    data = assert_ok(client.get("/health"))
    assert data["status"] == "ok"
    assert data["db"] == "postgresql"
    assert "timestamp" in data


# ══════════════════════════════════════════════════════════════════
# Week 1 — Core endpoints
# ══════════════════════════════════════════════════════════════════

def test_kpis_no_filter():
    data = assert_ok(client.get("/kpis"))
    for key in ("total_revenue", "total_orders", "completed_orders",
                "cancelled_orders", "avg_order_value", "unique_customers",
                "repeat_customers"):
        assert key in data
    assert data["total_orders"] >= 0


def test_kpis_with_date_range(date_range):
    start, end = date_range
    data = assert_ok(client.get("/kpis", params={"start": start, "end": end}))
    assert data["total_orders"] >= 0
    assert data["avg_order_value"] >= 0


def test_orders_default_pagination():
    data = assert_ok(client.get("/orders"))
    assert "total" in data and "orders" in data
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["orders"]) <= 20


def test_orders_with_filters(date_range):
    start, end = date_range
    data = assert_ok(client.get("/orders", params={
        "start": start, "end": end,
        "order_type": "Dine-in",
        "payment_mode": "UPI",
        "min_amount": 50,
        "max_amount": 5000,
        "page": 1, "page_size": 10,
    }))
    assert data["page_size"] == 10
    for row in data["orders"]:
        assert row["order_type"] == "Dine-in"
        assert row["payment_mode"] == "UPI"


def test_orders_invalid_page_rejected():
    # page must be >= 1
    resp = client.get("/orders", params={"page": 0})
    assert resp.status_code == 422


def test_orders_page_size_upper_bound_rejected():
    # page_size must be <= 100
    resp = client.get("/orders", params={"page_size": 500})
    assert resp.status_code == 422


def test_bestsellers_default():
    data = assert_ok(client.get("/bestsellers"))
    assert isinstance(data, list)
    assert len(data) <= 10
    if data:
        assert "name" in data[0] and "total_qty" in data[0]


def test_bestsellers_top_n_and_category():
    data = assert_ok(client.get("/bestsellers", params={"top_n": 3, "category": "Desserts"}))
    assert len(data) <= 3
    for row in data:
        assert row["category"] == "Desserts"


def test_peak_hours():
    data = assert_ok(client.get("/peak-hours"))
    assert isinstance(data, list)
    for row in data:
        assert 0 <= row["hour"] <= 23


def test_revenue_trend():
    data = assert_ok(client.get("/revenue-trend"))
    assert isinstance(data, list)


def test_category_split():
    data = assert_ok(client.get("/category-split"))
    assert isinstance(data, list)
    for row in data:
        assert "category" in row and "revenue" in row


def test_order_type_split():
    data = assert_ok(client.get("/order-type-split"))
    assert isinstance(data, list)
    valid_types = {"Dine-in", "Takeaway", "Delivery"}
    for row in data:
        assert row["order_type"] in valid_types


def test_repeat_customers():
    data = assert_ok(client.get("/repeat-customers", params={"top_n": 5}))
    assert isinstance(data, list)
    assert len(data) <= 5
    for row in data:
        assert row["visit_count"] > 1


# ══════════════════════════════════════════════════════════════════
# Week 2 — Advanced analytics
# ══════════════════════════════════════════════════════════════════

def test_menu_performance():
    data = assert_ok(client.get("/menu-performance"))
    assert isinstance(data, list)
    assert len(data) > 0
    row = data[0]
    for key in ("name", "category", "price", "cost", "total_sold", "revenue", "profit", "margin_pct"):
        assert key in row


def test_weekly_trend():
    data = assert_ok(client.get("/weekly-trend"))
    assert isinstance(data, list)


def test_payment_split():
    data = assert_ok(client.get("/payment-split"))
    assert isinstance(data, list)
    valid_modes = {"Cash", "UPI", "Card", "Online"}
    for row in data:
        assert row["payment_mode"] in valid_modes


def test_customer_profile_valid_id():
    data = assert_ok(client.get("/customer-profile/1"))
    assert "customer" in data
    assert "recent_orders" in data
    assert data["customer"]["customer_id"] == 1


def test_customer_profile_invalid_id_returns_404():
    resp = client.get("/customer-profile/999999")
    assert resp.status_code == 404


def test_revenue_forecast_default():
    data = assert_ok(client.get("/revenue-forecast"))
    assert isinstance(data, list)
    assert len(data) == 7
    for row in data:
        assert row["type"] == "forecast"
        assert row["forecast"] >= 0


def test_revenue_forecast_custom_days():
    data = assert_ok(client.get("/revenue-forecast", params={"days": 3}))
    assert len(data) == 3


def test_top_customers():
    data = assert_ok(client.get("/top-customers", params={"top_n": 5}))
    assert isinstance(data, list)
    assert len(data) <= 5
    amounts = [row["total_spent"] for row in data]
    assert amounts == sorted(amounts, reverse=True)  # sorted descending


def test_daily_comparison():
    data = assert_ok(client.get("/daily-comparison"))
    assert isinstance(data, list)
    for row in data:
        assert 0 <= row["day_num"] <= 6


# ══════════════════════════════════════════════════════════════════
# Week 3 — Reports & export
# ══════════════════════════════════════════════════════════════════

def test_summary_report(date_range):
    start, end = date_range
    data = assert_ok(client.get("/summary-report", params={"start": start, "end": end}))
    for key in ("period", "kpis", "bestsellers", "categories",
                "order_types", "payments", "top_customers", "generated_at"):
        assert key in data
    assert data["period"]["start"] == start
    assert data["period"]["end"] == end


def test_menu_items():
    data = assert_ok(client.get("/menu-items"))
    assert isinstance(data, list)
    assert len(data) == 22  # seeded menu size


def test_staff():
    data = assert_ok(client.get("/staff"))
    assert isinstance(data, list)
    assert len(data) == 10  # seeded staff size
    for row in data:
        assert row["role"] in {"Manager", "Chef", "Waiter", "Cashier"}


# ══════════════════════════════════════════════════════════════════
# Cross-cutting: CORS headers present (dashboard runs on a different port)
# ══════════════════════════════════════════════════════════════════

def test_cors_headers_present():
    resp = client.get("/health", headers={"Origin": "http://localhost:8501"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
