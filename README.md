# 🏭 Plant Monitor Dashboard

Real-time industrial monitoring dashboard that tracks equipment health across multiple facilities. Operators can observe live sensor data — **temperature**, **pressure**, **power consumption**, and **production output** — for every asset in the plant, with automatic KPI aggregation, interactive time-series charting, and operational insights.

![Stack](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/React_19-61DAFB?logo=react&logoColor=black)
![Stack](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Stack](https://img.shields.io/badge/Ant_Design-0170FE?logo=antdesign&logoColor=white)
![Stack](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Stack](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [1. Start PostgreSQL](#1-start-postgresql)
  - [2. Backend](#2-backend)
  - [3. Frontend](#3-frontend)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Data Generation](#data-generation)
- [Design Decisions](#design-decisions)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Facility Support** | Switch between facilities (Power Station, Chemical Plant, Manufacturing) via a global selector |
| **Real-Time KPI Cards** | Aggregated avg/min/max/current for temperature, pressure, power, and production output |
| **Operational Insights** | Automatic alerts when sensor readings exceed per-asset operational ranges, with severity levels (low/medium/high) |
| **Assets Overview** | Operational vs. maintenance count badges + detailed asset status table with live metric values and threshold ranges |
| **Interactive Time-Series Chart** | Select metric, time window (12h / 24h / 48h), and bucket size; multi-asset line chart (Recharts) |
| **Server-Sent Events (SSE)** | Real-time push updates — no polling needed; dashboard refreshes automatically when new readings arrive |
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
| **Backend** | FastAPI (Python) | Async REST API + SSE streaming |
| **Validation** | Pydantic v2 | Request/response schemas |
| **Database** | PostgreSQL 16 | Relational DB via Docker |
| **DB Driver** | asyncpg | Direct connection for aggregation & bulk inserts |
| **Bundler** | Vite 6 | Dev server with HMR + API proxy |

---

## Architecture

```mermaid
flowchart LR
    subgraph Docker
        DB[(PostgreSQL 16<br/>port 5433)]
    end

    subgraph FastAPI ["FastAPI Backend :8001"]
        API["REST API<br/>/api/v1"]
        SSE["SSE Stream<br/>/stream"]
        BG["Background Task<br/>every 30s"]
    end

    subgraph Frontend ["React SPA :5173"]
        UI["Dashboard UI<br/>Ant Design + Recharts"]
    end

    BG -- "COPY protocol<br/>64 readings" --> DB
    BG -. "broadcast<br/>update" .-> SSE
    DB -- "asyncpg pool<br/>(min=2, max=10)" --> API
    DB -- "asyncpg pool" --> SSE
    UI -- "JSON requests" --> API
    SSE -- "Server-Sent Events" --> UI
```

- The **Vite dev server** proxies `/api` requests to `localhost:8001`, so no CORS issues in development.
- **asyncpg** is used for all heavy operations (KPI aggregation with CTEs, time-series bucketing with `date_bin`, bulk `COPY` inserts).
- The **background task** runs inside FastAPI's lifespan — no separate process or cron needed.
- **SSE streaming** pushes dashboard updates to connected clients immediately after new readings are inserted.
- **Operational insights** are computed automatically after each batch of readings, checking values against per-asset operational ranges.

### Backend Internal Architecture

```mermaid
flowchart TB
    subgraph Lifespan ["main.py — Lifespan"]
        START([App Startup]) --> POOL["Create asyncpg Pool<br/>(database.py)"]
        POOL --> BG["Launch Background Task"]
        STOP([App Shutdown]) --> CANCEL["Cancel Task + Close Pool"]
    end

    subgraph BackgroundLoop ["Background Task — every 30s"]
        direction TB
        FETCH_ASSETS["Fetch all asset IDs<br/>+ facility IDs"] --> GENERATE["Generate 64 readings<br/>(16 assets × 4 metrics)"]
        GENERATE --> COPY["COPY to sensor_readings<br/>(bulk insert)"]
        COPY --> RELEASE["Release connection"]
        RELEASE --> INSIGHTS["manage_insights()<br/>per facility"]
        INSIGHTS --> BROADCAST["broadcaster.broadcast_update()<br/>per facility"]
        BROADCAST --> SLEEP["asyncio.sleep(30)"]
        SLEEP --> FETCH_ASSETS
    end

    subgraph Routes ["api/dashboard.py — Route Handlers"]
        R1["GET /facilities"]
        R2["GET /summary/&lbrace;id&rbrace;"]
        R3["GET /timeseries/&lbrace;id&rbrace;"]
        R4["GET /stream/&lbrace;id&rbrace; (SSE)"]
    end

    subgraph Services ["services/dashboard.py — Query Layer"]
        S1["fetch_facilities_with_counts()"]
        S2["fetch_facility() + fetch_kpis()<br/>+ fetch_assets_for_facility()<br/>+ fetch_insights()"]
        S3["fetch_timeseries()"]
        S4["manage_insights()<br/>threshold checks + upsert"]
    end

    subgraph Events ["events.py — SSE Broadcaster"]
        COND["asyncio.Condition<br/>per facility_id"]
    end

    R1 --> S1
    R2 --> S2
    R3 --> S3
    R4 -- "wait_for_update()" --> COND
    COND -- "notify_all()" --> R4
    BROADCAST --> COND
    INSIGHTS --> S4

    S1 & S2 & S3 & S4 --> POOL
```

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
│   │   ├── database.py          # asyncpg connection pool
│   │   ├── events.py            # SSE broadcaster (asyncio Condition per facility)
│   │   ├── seed.py              # Seed script (3 facilities, 16 assets, 368k rows)
│   │   ├── api/
│   │   │   └── dashboard.py     # Route handlers (REST + SSE stream)
│   │   ├── schemas/
│   │   │   └── dashboard.py     # Pydantic response schemas
│   │   └── services/
│   │       └── dashboard.py     # SQL queries (asyncpg) + insight management
│   ├── requirements.txt
│   ├── .env.example             # Template for DATABASE_URL
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
│   │   │   └── api.ts           # Axios client + SSE helpers
│   │   ├── layout/
│   │   │   └── AppLayout.tsx    # Ant Design Layout (header, content, footer)
│   │   ├── components/
│   │   │   ├── FacilitySelector/    # Dropdown with location + asset count
│   │   │   ├── KpiCards/            # KPI Statistic cards + asset table
│   │   │   ├── TimeseriesChart/     # Recharts LineChart with selectors
│   │   │   └── OperationalInsights/ # Alert list with severity filtering
│   │   └── pages/
│   │       └── DashboardPage.tsx    # Combines KpiCards + Insights + Chart
│   ├── index.html
│   ├── vite.config.ts           # Vite config with /api proxy → :8001
│   ├── package.json
│   └── tsconfig.json
│
├── db/
│   └── init.sql                 # Full schema (auto-runs on first docker compose up)
│
├── migrations/                  # Incremental SQL migration history
│   ├── 001_create_tables.sql
│   ├── 003_create_insights_table.sql
│   └── 004_asset_operational_ranges.sql
│
├── docker-compose.yml           # PostgreSQL 16 Alpine
├── .gitignore
└── README.md                    # ← You are here
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** | 20+ | PostgreSQL container |
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18+ | Frontend tooling |
| **npm** | 9+ | Package management |

---

## Getting Started

### 1. Start PostgreSQL

```bash
docker compose up -d
```

This starts a PostgreSQL 16 container on **port 5433** (to avoid conflicts with any local PostgreSQL on 5432). The schema is automatically created from `db/init.sql` on first run.

### 2. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Configure — defaults work out of the box with docker-compose
cp .env.example .env

# Seed the database (~368k rows, takes ~30s via COPY protocol)
python -m app.seed

# Start the API server
uvicorn app.main:app --reload --port 8001
```

The API is now running at **http://localhost:8001** — interactive docs at **/docs**.

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open **http://localhost:5173** to access the dashboard.

> The Vite dev server proxies `/api` requests to `localhost:8001`, so there are no CORS issues during development.

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

Aggregated KPIs, asset status (with live metrics and operational ranges), and operational insights.

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
  "active_alerts_count": 2,
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
  "insights": [
    {
      "severity": "high",
      "title": "Temperature exceeds safe range",
      "description": "Turbine A temperature at 118.3°C (max: 115°C)",
      "detected_at": "2026-02-19T10:00:00Z"
    }
  ],
  "assets": [
    {
      "id": "uuid",
      "name": "Turbine A",
      "type": "turbine",
      "status": "operational",
      "temperature": 92.1,
      "temperature_unit": "°C",
      "temperature_range": { "min": 60, "max": 115 },
      "pressure": 5.2,
      "pressure_unit": "bar",
      "pressure_range": { "min": 1, "max": 10 }
    }
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

### `GET /api/v1/dashboard/stream/{facility_id}`

Server-Sent Events stream for live dashboard updates. Pushes a `summary` event whenever new readings are inserted by the background task.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `hours` | `int` (1–48) | `24` | Time window for KPI aggregation |

### `GET /health`

Simple health check — returns `{"status": "ok"}`.

---

## Database Schema

Five tables with proper indexing for time-series query performance:

```mermaid
erDiagram
    facilities ||--o{ assets : "has"
    assets ||--o{ sensor_readings : "produces"
    assets ||--o{ operational_insights : "triggers"
    assets ||--o{ asset_operational_ranges : "has"
    facilities ||--o{ operational_insights : "belongs to"

    facilities {
        uuid id PK
        varchar name
        varchar location
        varchar type
        timestamptz created_at
        timestamptz updated_at
    }

    assets {
        uuid id PK
        uuid facility_id FK
        varchar name
        varchar type
        varchar status
        timestamptz created_at
        timestamptz updated_at
    }

    sensor_readings {
        uuid id PK
        uuid asset_id FK
        varchar metric_name
        float value
        varchar unit
        timestamptz timestamp
        timestamptz created_at
    }

    operational_insights {
        uuid id PK
        uuid facility_id FK
        uuid asset_id FK "nullable"
        varchar severity
        varchar title
        text description
        varchar metric_name
        varchar threshold_type
        timestamptz detected_at
        timestamptz resolved_at
        boolean is_active
    }

    asset_operational_ranges {
        uuid id PK
        uuid asset_id FK
        varchar metric_name
        float min_value
        float max_value
        varchar unit
    }
```

**Key indexes:**

| Index | Columns | Purpose |
|-------|---------|---------|
| `ix_readings_asset_metric_ts` | `(asset_id, metric_name, timestamp DESC)` | Fast filtered time-range queries |
| `ix_readings_timestamp` | `(timestamp DESC)` | Dashboard "latest" queries |
| `ix_assets_facility` | `(facility_id)` | Fast facility → assets joins |
| `ix_insights_facility_active` | `(facility_id, is_active, detected_at DESC)` | Active insight lookup |
| `ix_insights_active_unique` | Composite + partial `WHERE is_active` | Prevent duplicate active insights |
| `ix_operational_ranges_asset` | `(asset_id)` | Fast range lookups during checks |

The canonical schema lives in `db/init.sql` (auto-executed by Docker on first start). Incremental migration history is in `migrations/`.

---

## Data Generation

### Seed Script (`python -m app.seed`)

Populates the database with realistic industrial data:

- **3 facilities**: Power Station Alpha (Houston), Chemical Plant Beta (Rotterdam), Manufacturing Gamma (São Paulo)
- **16 assets**: Turbines, boilers, reactors, compressors, generators, etc.
- **Per-asset operational ranges**: Each asset type has specific min/max thresholds for all 4 metrics
- **4 metrics per asset** with physics-inspired generators:
  - 🌡️ **Temperature** (60–120°C) — gradual drift + Gaussian noise
  - ⚙️ **Pressure** (1–10 bar) — slow sinusoidal wave
  - ⚡ **Power Consumption** (100–500 kW) — daily load curve peaking at business hours
  - 📦 **Production Output** (50–200 units/hr) — correlated with power consumption
- **48 hours** of data at **30-second intervals** → **~368,640 rows**
- Uses asyncpg **COPY protocol** for fast bulk insertion (~30s total)

### Live Background Task

While the API server is running, a background task automatically inserts **64 new readings** (16 assets × 4 metrics) every **30 seconds**, keeping the dashboard data fresh and simulating a live plant environment. After each batch, operational insights are recalculated and SSE events are broadcast to connected clients.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Docker PostgreSQL** over cloud-hosted DB | Self-contained setup — no external accounts or credentials needed; `docker compose up` and go |
| **asyncpg direct connection** for queries | Full PostgreSQL feature access for aggregation (CTEs, `date_bin`, window functions) |
| **COPY protocol** for bulk inserts | ~10x faster than `executemany` for seeding 368k rows |
| **SSE** over WebSockets | Simpler unidirectional push; `EventSource` API is built into browsers |
| **Per-asset operational ranges** | Different equipment types have different safe operating thresholds |
| **Vite proxy** instead of CORS for dev | Cleaner dev experience — the frontend calls `/api/v1/...` directly |
| **Single-page dashboard** | Focused demo — one page covering all monitoring use cases |
| **Context API** for state | Lightweight global state for facility selection — no need for Redux/Zustand in a single-page app |

---

## License

This project was built as a technical demonstration. All rights reserved.
