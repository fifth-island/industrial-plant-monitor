# 🏭 Plant Monitor Dashboard

Real-time industrial monitoring dashboard that tracks equipment health across multiple facilities. Operators can observe live sensor data — **temperature**, **pressure**, **power consumption**, and **production output** — for every asset in the plant, with automatic KPI aggregation and interactive time-series charting.

![Stack](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/React_19-61DAFB?logo=react&logoColor=black)
![Stack](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Stack](https://img.shields.io/badge/Ant_Design-0170FE?logo=antdesign&logoColor=white)
![Stack](https://img.shields.io/badge/Supabase-3FCF8E?logo=supabase&logoColor=white)
![Stack](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [1. Supabase Setup](#1-supabase-setup)
  - [2. Backend](#2-backend)
  - [3. Frontend](#3-frontend)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Data Generation](#data-generation)
- [Design Decisions](#design-decisions)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Facility Support** | Switch between facilities (Power Station, Chemical Plant, Manufacturing) via a global selector |
| **Real-Time KPI Cards** | Aggregated avg/min/max/current for temperature, pressure, power, and production output |
| **Assets Overview** | Quick operational vs. maintenance count badges + detailed asset status table |
| **Interactive Time-Series Chart** | Select metric, time window (12h / 24h / 48h), and bucket size; multi-asset line chart (Recharts) |
| **Live Data Generation** | Background task inserts 64 readings (16 assets × 4 metrics) every 30 seconds via `COPY` protocol |
| **Seed Data** | One-command seeding of ~368k realistic sensor readings spanning 48 hours |
| **Swagger / OpenAPI Docs** | Auto-generated at `/docs` — fully typed request/response schemas |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 + TypeScript | SPA framework |
| **UI Library** | Ant Design 6 | Layout, cards, tables, selectors |
| **Charting** | Recharts 3 | Time-series `LineChart` with tooltips |
| **State** | React Context + hooks | Facility selection, data fetching |
| **HTTP Client** | Axios | API consumption with proxy |
| **Backend** | FastAPI (Python) | Async REST API |
| **Validation** | Pydantic v2 | Request/response schemas |
| **Database** | Supabase (PostgreSQL) | Cloud-hosted relational DB |
| **DB Driver** | asyncpg | Direct connection for aggregation & bulk inserts |
| **REST Client** | postgrest | Lightweight Supabase REST client |
| **Bundler** | Vite 6 | Dev server with HMR + API proxy |

---

## Architecture

```
┌──────────────┐  every 30s    ┌─────────────────────────┐
│  Background  │───────────────▶│     Supabase            │
│  Task        │  COPY protocol │  (hosted PostgreSQL)    │
│  (FastAPI)   │  64 readings   └───────────┬─────────────┘
└──────────────┘                            │
                                            │ asyncpg pool
                                            │ (min=2, max=5)
┌──────────────┐    /api/v1     ┌───────────▼─────────────┐
│  React SPA   │◀──────────────▶│     FastAPI Backend     │
│  :5173       │   JSON         │     :8000               │
│  (Vite proxy)│                │  3 endpoints + /health  │
└──────────────┘                └─────────────────────────┘
```

- The **Vite dev server** proxies `/api` requests to `localhost:8000`, so no CORS issues in development.
- **asyncpg** is used for all heavy operations (KPI aggregation with CTEs, time-series bucketing with `date_bin`, bulk `COPY` inserts).
- The **background task** runs inside FastAPI's lifespan — no separate process or cron needed.

---

## Project Structure

```
plant-monitor-dashboard/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, lifespan, background task
│   │   ├── config.py            # Settings (pydantic-settings, .env)
│   │   ├── database.py          # asyncpg pool + PostgREST client
│   │   ├── seed.py              # Seed script (3 facilities, 16 assets, 368k rows)
│   │   ├── test_db.py           # DB connection smoke test
│   │   ├── api/
│   │   │   └── dashboard.py     # Route handlers (3 endpoints)
│   │   ├── models/
│   │   │   ├── facility.py      # SQLAlchemy model
│   │   │   ├── asset.py
│   │   │   └── sensor_reading.py
│   │   ├── schemas/
│   │   │   └── dashboard.py     # Pydantic response schemas
│   │   └── services/
│   │       └── dashboard.py     # SQL queries (asyncpg)
│   ├── requirements.txt
│   ├── .env.example             # Template for Supabase credentials
│   └── .env                     # (git-ignored) actual credentials
│
├── frontend/
│   ├── public/                  # Favicons, web manifest
│   ├── src/
│   │   ├── main.tsx             # React entry point
│   │   ├── App.tsx              # Ant Design ConfigProvider + routing
│   │   ├── types.ts             # TypeScript interfaces + metric constants
│   │   ├── index.css            # Minimal reset
│   │   ├── context/
│   │   │   └── FacilityContext.tsx   # Global facility selection state
│   │   ├── services/
│   │   │   └── api.ts           # Axios client (fetchFacilities, fetchSummary, fetchTimeseries)
│   │   ├── layout/
│   │   │   └── AppLayout.tsx    # Ant Design Layout (header, content, footer)
│   │   ├── components/
│   │   │   ├── FacilitySelector/    # Dropdown with location + asset count
│   │   │   ├── KpiCards/            # 4 KPI Statistic cards + asset table
│   │   │   └── TimeseriesChart/     # Recharts LineChart with selectors
│   │   └── pages/
│   │       └── DashboardPage.tsx    # Combines KpiCards + TimeseriesChart
│   ├── index.html
│   ├── vite.config.ts           # Vite config with /api proxy
│   ├── package.json
│   └── tsconfig.json
│
├── supabase/
│   └── migrations/
│       ├── 001_create_tables.sql    # Tables + indexes
│       └── 002_rls_policies.sql     # Row-level security
│
├── DESIGN_PLAN.md               # Detailed architecture & design document
├── .gitignore
└── README.md                    # ← You are here
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18+ | Frontend tooling |
| **npm** | 9+ | Package management |
| **Supabase account** | Free tier | Cloud PostgreSQL database |

> **No Docker required.** The database runs on Supabase's cloud infrastructure, and both backend and frontend run natively on your machine.

---

## Getting Started

### 1. Supabase Setup

1. Create a free project at [supabase.com](https://supabase.com)
2. Open the **SQL Editor** in the Supabase Dashboard
3. Run the migration files **in order**:
   - Copy and execute `supabase/migrations/001_create_tables.sql` — creates `facilities`, `assets`, `sensor_readings` tables and performance indexes
   - Copy and execute `supabase/migrations/002_rls_policies.sql` — enables RLS with permissive policies for the service role
4. Collect your credentials from **Project Settings**:
   - **API → Project URL** → `SUPABASE_URL`
   - **API → service_role key** → `SUPABASE_SERVICE_KEY`
   - **Database → Connection string (URI, Transaction mode, port 6543)** → `SUPABASE_DB_URL`

### 2. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

Edit `backend/.env` with your Supabase credentials:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_DB_URL=postgresql+asyncpg://postgres.your-project-ref:your-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

Seed the database (one-time — inserts ~368k rows in ~30s via COPY protocol):

```bash
python -m app.seed
```

Start the API server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000** — interactive docs at **/docs**.

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open **http://localhost:5173** to access the dashboard.

> The Vite dev server automatically proxies all `/api` requests to `localhost:8000`, so there are no CORS issues during development.

---

## API Reference

All endpoints are prefixed with `/api/v1`.

### `GET /api/v1/facilities`

List all facilities with their asset counts.

**Response:**

```json
{
  "facilities": [
    {
      "id": "uuid",
      "name": "Power Station Alpha",
      "location": "Houston, TX",
      "type": "power_station",
      "asset_count": 5,
      "created_at": "2026-02-19T10:00:00Z"
    }
  ]
}
```

### `GET /api/v1/dashboard/summary/{facility_id}`

Aggregated KPIs and asset status for a facility.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `hours` | `int` (1–48) | `24` | Time window for KPI aggregation |

**Response:**

```json
{
  "facility_id": "uuid",
  "facility_name": "Power Station Alpha",
  "location": "Houston, TX",
  "facility_type": "power_station",
  "total_assets": 5,
  "operational_count": 4,
  "maintenance_count": 1,
  "kpis": [
    {
      "metric_name": "temperature",
      "current_value": 92.1,
      "avg_value": 87.5,
      "min_value": 61.2,
      "max_value": 118.3,
      "unit": "°C"
    }
  ],
  "assets": [
    { "id": "uuid", "name": "Turbine A", "type": "turbine", "status": "operational" }
  ],
  "period_hours": 24
}
```

### `GET /api/v1/dashboard/timeseries/{facility_id}`

Time-series data for a metric, grouped by asset. Downsampled into N-minute buckets.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `metric` | `enum` | `temperature` | One of: `temperature`, `pressure`, `power_consumption`, `production_output` |
| `hours` | `int` (1–48) | `24` | Time window |
| `bucket_minutes` | `int` (1–60) | `5` | Aggregation bucket size |

**Response:**

```json
{
  "facility_id": "uuid",
  "facility_name": "Power Station Alpha",
  "metric_name": "temperature",
  "unit": "C",
  "start": "2026-02-18T10:00:00Z",
  "end": "2026-02-19T10:00:00Z",
  "bucket_minutes": 5,
  "series": [
    {
      "asset_id": "uuid",
      "asset_name": "Turbine A",
      "data": [
        { "timestamp": "2026-02-19T09:55:00Z", "value": 91.7 },
        { "timestamp": "2026-02-19T10:00:00Z", "value": 92.3 }
      ]
    }
  ]
}
```

### `GET /health`

Simple health check — returns `{"status": "ok"}`.

---

## Database Schema

Three tables with proper indexing for time-series query performance:

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│  facilities  │ 1───* │     assets       │ 1───* │  sensor_readings     │
├──────────────┤       ├──────────────────┤       ├──────────────────────┤
│ id (PK, UUID)│       │ id (PK, UUID)    │       │ id (PK, UUID)        │
│ name         │       │ facility_id (FK) │       │ asset_id (FK)        │
│ location     │       │ name             │       │ metric_name          │
│ type         │       │ type             │       │ value (FLOAT)        │
│ created_at   │       │ status           │       │ unit                 │
│ updated_at   │       │ created_at       │       │ timestamp (TIMESTAMPTZ) │
└──────────────┘       │ updated_at       │       │ created_at           │
                       └──────────────────┘       └──────────────────────┘
```

**Key indexes:**

| Index | Columns | Purpose |
|-------|---------|---------|
| `ix_readings_asset_metric_ts` | `(asset_id, metric_name, timestamp DESC)` | Fast filtered time-range queries |
| `ix_readings_timestamp` | `(timestamp DESC)` | Dashboard "latest" queries |
| `ix_assets_facility` | `(facility_id)` | Fast facility → assets joins |

---

## Data Generation

### Seed Script (`python -m app.seed`)

Populates the database with realistic industrial data:

- **3 facilities**: Power Station Alpha (Houston), Chemical Plant Beta (Rotterdam), Manufacturing Gamma (Nagoya)
- **16 assets**: Turbines, boilers, reactors, compressors, generators, etc.
- **4 metrics per asset** with physics-inspired generators:
  - 🌡️ **Temperature** (60–120°C) — gradual drift + Gaussian noise
  - ⚙️ **Pressure** (1–10 bar) — slow sinusoidal wave
  - ⚡ **Power Consumption** (100–500 kW) — daily load curve peaking at business hours
  - 📦 **Production Output** (50–200 units/hr) — correlated with power consumption
- **48 hours** of data at **30-second intervals** → **~368,640 rows**
- Uses asyncpg **COPY protocol** for fast bulk insertion (~30s total)

### Live Background Task

While the API server is running, a background task automatically inserts **64 new readings** (16 assets × 4 metrics) every **30 seconds**, keeping the dashboard data fresh and simulating a live plant environment.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Supabase** over local Docker/PostgreSQL | Offloads DB compute to the cloud — keeps the local environment lightweight and avoids running Docker + Postgres locally, which would consume significant resources on a 16 GB RAM machine |
| **asyncpg direct connection** for queries | Supabase REST (PostgREST) does not support `GROUP BY`, `CTE`, or `date_bin` — raw SQL via asyncpg allows full PostgreSQL feature access for aggregation |
| **COPY protocol** for bulk inserts | ~10x faster than `executemany` for seeding 368k rows |
| **postgrest** package (not `supabase-py` SDK) | The full Supabase SDK pulls in heavy dependencies; `postgrest` is lighter and sufficient |
| **No Docker or Alembic** | Migrations are plain SQL files run in the Supabase SQL Editor; no ORM migration tooling needed |
| **SQLAlchemy models kept** | Serve as code-level schema documentation alongside the SQL migrations |
| **Vite proxy** instead of CORS for dev | Cleaner dev experience — the frontend calls `/api/v1/...` directly |
| **Single-page dashboard** | Focused demo — one page covering all monitoring use cases |
| **Polling** instead of WebSockets | Simpler to implement; meets the spec requirements |
| **Context API** for state | Lightweight global state for facility selection — no need for Redux/Zustand in a single-page app |

---

## Future Enhancements

- **Supabase Realtime** — subscribe to `sensor_readings` inserts for push-based updates (replace polling)
- **Alert System** — configurable thresholds that trigger notifications when metrics exceed safe ranges
- **Historical Comparison** — overlay current data with previous period (day-over-day, week-over-week)
- **Asset Detail View** — drill-down page per asset with full metric history
- **Export to CSV/PDF** — download reports for compliance and auditing
- **Authentication** — Supabase Auth for role-based access (operators, managers, admins)
- **Dark Mode** — Ant Design theme toggle

---

## License

This project was built as a technical demonstration. All rights reserved.
