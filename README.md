# 🍽️ PRJ-053 — Restaurant Sales Dashboard

**Student:** Ya Khaiyum.A PDKV | **Reg No:** 411623104047  
**Stack:** FastAPI · Streamlit · **PostgreSQL** · Pandas · Plotly
 
---

## 📁 Project Structure

``` 
prj053_pg/
├── backend/
│   └── main.py          # FastAPI — 18 API endpoints (PostgreSQL)
├── frontend/
│   └── app.py           # Streamlit — 5-tab dashboard
├── data/
│   └── seed_data.py     # Generates sample data into PostgreSQL
├── tests/
│   └── test_all.py      # Automated tests
├── requirements.txt
└── README.md
```
---

## 🐘 PostgreSQL Setup

### Option A — Local PostgreSQL:

```bash
# 1. Create the database
psql -U postgres -c "CREATE DATABASE restaurant_db;"

# 2. Set the connection URL (optional — defaults to localhost)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/restaurant_db"
```

### Option B — Docker (easiest):

```bash
docker run -d \
  --name pg_restaurant \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=restaurant_db \
  -p 5432:5432 \
  postgres:15
```

---

## 🚀 Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed the PostgreSQL database
python data/seed_data.py

# 3. Terminal 1 — Start Backend
cd backend
uvicorn main:app --reload --port 8000

# 4. Terminal 2 — Start Frontend
cd frontend
streamlit run app.py
```

- Dashboard → http://localhost:8501  
- API Docs  → http://localhost:8000/docs

---

## 🧪 Running Tests

An automated test suite (`tests/test_all.py`) covers all 19 API endpoints,
query-param filters, pagination limits, and error handling (invalid IDs,
out-of-range params). It uses FastAPI's `TestClient`, so no separate
uvicorn server is needed — but PostgreSQL must be running and seeded first.

```bash
# with PostgreSQL running and seeded (see above)
pytest tests/test_all.py -v
```

All 27 tests pass against a freshly seeded database.

---

## ✅ All 3 Weeks Completed

### Week 1 — Core Implementation
- PostgreSQL DB with 5 tables + indexes
- 1600+ sample orders, 200 customers, 22 menu items
- 9 FastAPI endpoints
- KPI cards, charts, filters, CSV export

### Week 2 — Advanced Analytics
- Menu performance with profit/margin analysis
- Weekly trend, daily comparison (day-of-week)
- Revenue forecast (7-day moving average)
- Customer profiles, top spenders

### Week 3 — Polish & Reports
- 5-tab dark UI (Streamlit + Plotly)
- Summary report endpoint
- Combined filters (date + type + payment + amount range)
- CSV export for Orders, KPIs, Bestsellers

---

## 📊 API Endpoints (18 total)

| Endpoint | Description |
|---|---|
| GET /health | Health check |
| GET /kpis | KPI summary |
| GET /orders | Orders with filters + pagination |
| GET /bestsellers | Top-N items |
| GET /peak-hours | Hourly analysis |
| GET /revenue-trend | Daily revenue |
| GET /category-split | Category revenue |
| GET /order-type-split | Dine-in/Takeaway/Delivery |
| GET /repeat-customers | Loyal customers |
| GET /menu-performance | Item profit/margin |
| GET /weekly-trend | Week-by-week |
| GET /payment-split | Payment mode analysis |
| GET /customer-profile/{id} | Individual profile |
| GET /revenue-forecast | 7-day forecast |
| GET /top-customers | Top spenders |
| GET /daily-comparison | Day-of-week analysis |
| GET /summary-report | Full report |
| GET /menu-items | Menu catalogue |

---
## 🔑 Environment Variable

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/restaurant_db` |
