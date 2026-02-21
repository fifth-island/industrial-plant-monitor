# Industrial Dashboard App — Design Plan

## 1. Project Overview

Build a **plant monitoring dashboard** for industrial facilities (power stations, chemical plants, manufacturing). The system tracks equipment (assets) that continuously report sensor data — temperature, pressure, power consumption, and production output — and presents it to plant operators via a real-time web dashboard.

### Tech Stack (aligned with CVector's stack)

| Layer        | Technology                                  |
|--------------|---------------------------------------------|
| Frontend     | React 18 + TypeScript                       |
| UI Library   | Ant Design 5                                |
| Charting     | Recharts                                    |
| Backend      | FastAPI (Python 3.11+)                      |
| Database     | Supabase (hosted PostgreSQL)                |
| DB Client    | supabase-py + asyncpg (direct connection)   |
| ORM          | SQLAlchemy 2.0 (models only, no Alembic)    |
| Migrations   | Supabase SQL migrations (via Dashboard/CLI) |
| Data Seeding | Faker + custom time-series generator        |
| Dev Tooling  | Local dev servers (no Docker required)      |

> **Why Supabase?** Running Docker + PostgreSQL locally on an 8 GB RAM / 5th-gen i5 machine causes severe performance issues. Supabase provides a **free-tier hosted PostgreSQL** instance with built-in auth, REST API, and dashboard — offloading all database compute to the cloud and keeping the local machine lightweight.

---

## 2. Database Schema Design

### 2.1 Entity-Relationship Diagram

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

### 2.2 Supabase SQL Migration

All tables are created via the **Supabase SQL Editor** or CLI migrations. The migration file lives in the repo for version control:

```sql
-- supabase/migrations/001_create_tables.sql

-- Enable UUID extension (Supabase enables this by default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Facilities
CREATE TABLE facilities (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    location    VARCHAR(255) NOT NULL,
    type        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Assets
CREATE TABLE assets (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id  UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    type         VARCHAR(100) NOT NULL,
    status       VARCHAR(50)  NOT NULL DEFAULT 'operational',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Sensor Readings
CREATE TABLE sensor_readings (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id     UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    metric_name  VARCHAR(100)     NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(50)      NOT NULL,
    timestamp    TIMESTAMPTZ      NOT NULL,
    created_at   TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX ix_readings_asset_metric_ts ON sensor_readings (asset_id, metric_name, timestamp DESC);
CREATE INDEX ix_readings_timestamp        ON sensor_readings (timestamp DESC);
CREATE INDEX ix_assets_facility           ON assets (facility_id);
```

### 2.3 Table Definitions

#### `facilities`

| Column      | Type                     | Constraints           | Description                          |
|-------------|--------------------------|------------------------|--------------------------------------|
| id          | UUID                     | PK, default uuid4      | Unique facility identifier           |
| name        | VARCHAR(255)             | NOT NULL               | Human-readable facility name         |
| location    | VARCHAR(255)             | NOT NULL               | Physical location / address          |
| type        | VARCHAR(100)             | NOT NULL               | e.g., "power_station", "chemical_plant", "manufacturing" |
| created_at  | TIMESTAMPTZ              | NOT NULL, default now  | Record creation timestamp            |
| updated_at  | TIMESTAMPTZ              | NOT NULL, default now  | Last update timestamp                |

#### `assets`

| Column       | Type                    | Constraints                    | Description                       |
|--------------|-------------------------|--------------------------------|-----------------------------------|
| id           | UUID                    | PK, default uuid4              | Unique asset identifier           |
| facility_id  | UUID                    | FK → facilities.id, NOT NULL   | Parent facility                   |
| name         | VARCHAR(255)            | NOT NULL                       | e.g., "Turbine A", "Boiler #3"   |
| type         | VARCHAR(100)            | NOT NULL                       | e.g., "turbine", "boiler", "compressor" |
| status       | VARCHAR(50)             | NOT NULL, default 'operational'| "operational", "maintenance", "offline" |
| created_at   | TIMESTAMPTZ             | NOT NULL, default now          | Record creation timestamp         |
| updated_at   | TIMESTAMPTZ             | NOT NULL, default now          | Last update timestamp             |

#### `sensor_readings`

| Column       | Type                    | Constraints                    | Description                                |
|--------------|-------------------------|--------------------------------|--------------------------------------------|
| id           | UUID                    | PK, default uuid4              | Unique reading identifier                  |
| asset_id     | UUID                    | FK → assets.id, NOT NULL       | Source asset                               |
| metric_name  | VARCHAR(100)            | NOT NULL                       | "temperature", "pressure", "power_consumption", "production_output" |
| value        | DOUBLE PRECISION        | NOT NULL                       | Numeric sensor value                       |
| unit         | VARCHAR(50)             | NOT NULL                       | "°C", "bar", "kW", "units/hr"             |
| timestamp    | TIMESTAMPTZ             | NOT NULL                       | When the reading was taken                 |
| created_at   | TIMESTAMPTZ             | NOT NULL, default now          | Record insertion time                      |

**Indexes (critical for query performance):**

| Index Name                               | Columns                                     | Purpose                              |
|------------------------------------------|---------------------------------------------|--------------------------------------|
| ix_readings_asset_metric_ts              | (asset_id, metric_name, timestamp DESC)     | Fast filtered time-range queries     |
| ix_readings_timestamp                    | (timestamp DESC)                            | Dashboard "latest" queries           |
| ix_assets_facility                       | (facility_id)                               | Fast join from facility → assets     |

### 2.4 Row-Level Security (RLS)

Supabase enables RLS by default. For this project (no user auth), we add permissive policies so the backend service role can read/write freely:

```sql
-- supabase/migrations/002_rls_policies.sql

ALTER TABLE facilities      ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;

-- Allow full access via the service_role key (used by the backend)
CREATE POLICY "service_role_all" ON facilities      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON assets          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON sensor_readings FOR ALL USING (true) WITH CHECK (true);

-- Allow anonymous read access (for potential direct frontend queries)
CREATE POLICY "anon_read" ON facilities      FOR SELECT USING (true);
CREATE POLICY "anon_read" ON assets          FOR SELECT USING (true);
CREATE POLICY "anon_read" ON sensor_readings FOR SELECT USING (true);
```

### 2.5 Seed Data Strategy

Generate realistic sample data:
- **3 facilities** (Power Station Alpha, Chemical Plant Beta, Manufacturing Gamma)
- **4-6 assets per facility** with varied types
- **Sensor readings**: 48 hours of historical data, one reading per metric per asset every **30 seconds**
  - Temperature: 60-120°C with gradual drift + noise
  - Pressure: 1.0-10.0 bar with slow wave pattern
  - Power consumption: 100-500 kW with daily load curve
  - Production output: 50-200 units/hr tracking power loosely

Total seed data: ~3 facilities × 5 assets × 4 metrics × 5,760 readings (48h @ 30s) ≈ **345,600 rows** — enough to feel realistic.

The seed script runs locally and inserts data into the remote Supabase database via the **direct PostgreSQL connection string** (using `asyncpg` for bulk inserts) or via the **supabase-py** client for smaller tables.

A **background task** in the FastAPI app will continue generating new readings every 30 seconds while the app is running, inserting them into Supabase to provide live data for the dashboard.

---

## 3. Backend API Design

### 3.1 Framework: FastAPI

FastAPI is chosen because:
- CVector uses it
- Auto-generates OpenAPI/Swagger docs
- Async support for DB queries
- Pydantic v2 for request/response validation

### 3.2 Supabase Integration

The backend connects to Supabase in two ways:

1. **`supabase-py` client** — for simple CRUD operations (facilities, assets). Uses the Supabase REST API under the hood with the `service_role` key.
2. **Direct `asyncpg` connection** — for high-performance bulk inserts (seeding) and complex aggregation queries (dashboard summary, time-series). Connects via the Supabase **direct connection string** (bypasses the REST layer).

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase project config
    SUPABASE_URL: str          # e.g., "https://xxxx.supabase.co"
    SUPABASE_SERVICE_KEY: str  # service_role secret key
    SUPABASE_DB_URL: str       # e.g., "postgresql+asyncpg://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

    class Config:
        env_file = ".env"
```

### 3.3 API Endpoints

#### Facilities

| Method | Path                          | Description                               | Query Params |
|--------|-------------------------------|-------------------------------------------|--------------|
| GET    | `/api/v1/facilities`          | List all facilities                       | —            |
| GET    | `/api/v1/facilities/{id}`     | Single facility with its assets           | —            |

#### Sensor Readings

| Method | Path                                  | Description                               | Query Params                                      |
|--------|---------------------------------------|-------------------------------------------|---------------------------------------------------|
| GET    | `/api/v1/readings`                    | Filtered sensor readings                  | `facility_id`, `asset_id`, `metric_name`, `start_time`, `end_time`, `limit`, `offset` |
| GET    | `/api/v1/readings/latest`             | Latest reading per asset/metric combo     | `facility_id`, `asset_id`, `metric_name`          |

#### Dashboard Summary

| Method | Path                                          | Description                                                   | Query Params    |
|--------|-----------------------------------------------|---------------------------------------------------------------|-----------------|
| GET    | `/api/v1/dashboard/summary/{facility_id}`     | Aggregated current plant status: latest values per metric, totals for power consumption & output rate | —               |
| GET    | `/api/v1/dashboard/timeseries/{facility_id}`  | Time-series data for charting (aggregated by facility)        | `metric_name`, `start_time`, `end_time`, `interval` (e.g., "1m", "5m", "1h") |

### 3.4 Response Schemas

#### `GET /api/v1/facilities/{id}` Response

```json
{
  "id": "uuid",
  "name": "Power Station Alpha",
  "location": "Houston, TX",
  "type": "power_station",
  "assets": [
    {
      "id": "uuid",
      "name": "Turbine A",
      "type": "turbine",
      "status": "operational"
    }
  ]
}
```

#### `GET /api/v1/dashboard/summary/{facility_id}` Response

```json
{
  "facility_id": "uuid",
  "facility_name": "Power Station Alpha",
  "timestamp": "2026-02-19T12:00:00Z",
  "metrics": {
    "total_power_consumption": { "value": 1250.5, "unit": "kW" },
    "total_production_output": { "value": 620.3, "unit": "units/hr" },
    "avg_temperature": { "value": 87.2, "unit": "°C" },
    "avg_pressure": { "value": 4.8, "unit": "bar" }
  },
  "asset_statuses": {
    "operational": 4,
    "maintenance": 1,
    "offline": 0
  },
  "asset_details": [
    {
      "asset_id": "uuid",
      "asset_name": "Turbine A",
      "status": "operational",
      "latest_readings": {
        "temperature": { "value": 92.1, "unit": "°C", "timestamp": "..." },
        "pressure": { "value": 5.2, "unit": "bar", "timestamp": "..." },
        "power_consumption": { "value": 310.0, "unit": "kW", "timestamp": "..." },
        "production_output": { "value": 155.0, "unit": "units/hr", "timestamp": "..." }
      }
    }
  ]
}
```

#### `GET /api/v1/dashboard/timeseries/{facility_id}` Response

```json
{
  "facility_id": "uuid",
  "metric_name": "power_consumption",
  "interval": "5m",
  "data": [
    { "timestamp": "2026-02-19T10:00:00Z", "value": 1230.5 },
    { "timestamp": "2026-02-19T10:05:00Z", "value": 1245.2 }
  ]
}
```

### 3.5 Backend Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app entry point, CORS, lifespan
│   ├── config.py             # Settings via pydantic-settings (Supabase creds)
│   ├── database.py           # asyncpg pool + supabase-py client init
│   ├── models/               # SQLAlchemy ORM models (for schema reference)
│   │   ├── __init__.py
│   │   ├── facility.py
│   │   ├── asset.py
│   │   └── sensor_reading.py
│   ├── schemas/              # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── facility.py
│   │   ├── asset.py
│   │   ├── reading.py
│   │   └── dashboard.py
│   ├── api/                  # Route handlers
│   │   ├── __init__.py
│   │   ├── facilities.py
│   │   ├── readings.py
│   │   └── dashboard.py
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── facility_service.py
│   │   ├── reading_service.py
│   │   └── dashboard_service.py
│   └── seed.py               # Data seeding script (inserts into Supabase)
├── requirements.txt
└── .env.example              # Template for Supabase credentials
```

> **Notable changes from Docker-based plan:**
> - No `alembic/` directory — migrations are managed via Supabase SQL Editor or CLI
> - No `Dockerfile` — the backend runs natively with `uvicorn`
> - `database.py` initializes both a `supabase-py` client and an `asyncpg` connection pool
> - `.env.example` replaces hardcoded Docker `DATABASE_URL` with Supabase credentials

---

## 4. Frontend Design

### 4.1 Page Layout

Single-page dashboard with the following sections (top to bottom):

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER — App Name + Facility Selector (Ant Design Select)     │
├─────────────────────────────────────────────────────────────────┤
│  KPI CARDS ROW (Ant Design Statistic cards)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Total Power│ │Total     │ │  Avg     │ │  Avg     │          │
│  │1,250 kW  │ │Output    │ │  Temp    │ │ Pressure │          │
│  │          │ │620 u/hr  │ │  87°C    │ │ 4.8 bar  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  ASSET STATUS OVERVIEW                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Operational: 4  │  Maintenance: 1  │  Offline: 0       │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  TIME-SERIES CHART (Recharts LineChart)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Metric Selector Tabs: Power | Temp | Pressure | Output│   │
│  │  Time Range: 30m | 1h | 2h | 6h | 24h                 │   │
│  │                                                         │   │
│  │  📈 Line chart with tooltip + grid                      │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  ASSET DETAILS TABLE (Ant Design Table)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Asset    │ Status  │ Temp │ Pressure │ Power  │ Output  │   │
│  │ Turbine A│ 🟢 Op  │ 92°C │ 5.2 bar  │ 310 kW │ 155 u/h│   │
│  │ Boiler #3│ 🟡 Mnt │ 78°C │ 3.1 bar  │ 220 kW │ 0 u/h  │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  FOOTER — Last refreshed: 12:00:05 • Auto-refresh: 10s        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Auto-Refresh Strategy

- **Polling** every **10 seconds** using `setInterval` + `useEffect`
- Summary endpoint provides all KPI + asset data in one call
- Time-series endpoint called separately (only when chart is visible)
- Visual "last updated" indicator in footer
- Optional: subtle pulse animation on value changes

### 4.3 Frontend Project Structure

```
frontend/
├── public/
├── src/
│   ├── index.tsx
│   ├── App.tsx                     # Root layout + facility selector
│   ├── api/                        # API client layer
│   │   ├── client.ts               # Axios instance with base URL
│   │   ├── facilities.ts           # Facility API calls
│   │   ├── readings.ts             # Readings API calls
│   │   └── dashboard.ts            # Dashboard API calls
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.tsx        # Header with facility selector
│   │   │   └── AppFooter.tsx        # Footer with refresh indicator
│   │   ├── dashboard/
│   │   │   ├── KpiCards.tsx          # Statistic cards row
│   │   │   ├── AssetStatusBar.tsx    # Operational/Maintenance/Offline counts
│   │   │   ├── TimeSeriesChart.tsx   # Recharts line chart + controls
│   │   │   └── AssetDetailsTable.tsx # Ant Design table with latest readings
│   │   └── common/
│   │       ├── StatusBadge.tsx       # Color-coded status indicator
│   │       └── LoadingOverlay.tsx    # Loading state component
│   ├── hooks/
│   │   ├── useDashboardSummary.ts   # Polling hook for summary data
│   │   ├── useTimeSeries.ts         # Hook for time-series data
│   │   └── useFacilities.ts         # Hook to load facility list
│   ├── types/                       # TypeScript type definitions
│   │   ├── facility.ts
│   │   ├── asset.ts
│   │   ├── reading.ts
│   │   └── dashboard.ts
│   └── utils/
│       ├── formatters.ts            # Number/date formatting helpers
│       └── constants.ts             # Metric names, colors, units
├── package.json
├── tsconfig.json
└── vite.config.ts                   # Vite bundler config
```

---

## 5. Local Development Setup (No Docker Required)

### 5.1 Supabase Project Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com) (free tier)
2. From the Supabase Dashboard, navigate to **Project Settings → API** and note:
   - **Project URL** (`SUPABASE_URL`)
   - **`service_role` key** (`SUPABASE_SERVICE_KEY`) — keep this secret
3. Navigate to **Project Settings → Database** and note:
   - **Connection string** (`SUPABASE_DB_URL`) — for direct asyncpg access
4. Open the **SQL Editor** and run the migration files from `supabase/migrations/` to create tables, indexes, and RLS policies

### 5.2 Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# .env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...  # service_role key
SUPABASE_DB_URL=postgresql+asyncpg://postgres.your-project-ref:your-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### 5.3 Getting Started (README instructions)

```bash
# Clone
git clone <repo-url>
cd plant-dashboard

# ------- Supabase Setup -------
# 1. Create a free project at https://supabase.com
# 2. Run the SQL migrations in the Supabase SQL Editor:
#    - supabase/migrations/001_create_tables.sql
#    - supabase/migrations/002_rls_policies.sql

# ------- Backend -------
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Copy .env.example to .env and fill in your Supabase credentials
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# Seed the database (one-time)
python -m app.seed

# Start the API server
uvicorn app.main:app --reload --port 8000

# ------- Frontend -------
cd ../frontend
npm install
npm run dev

# Access
# Dashboard: http://localhost:5173
# API docs:  http://localhost:8000/docs
```

### 5.4 Requirements

```
# backend/requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
supabase>=2.3.0
asyncpg>=0.29.0
sqlalchemy>=2.0.25
faker>=22.0.0
python-dotenv>=1.0.0
httpx>=0.26.0
```

---

## 6. Implementation Plan (Sequenced)

### Phase 1: Supabase & Schema (Day 1)
- [ ] Create Supabase project (free tier)
- [ ] Initialize project structure (backend + frontend directories)
- [ ] Write SQL migration files for tables, indexes, and RLS policies
- [ ] Run migrations in Supabase SQL Editor
- [ ] Set up `database.py` with asyncpg pool + supabase-py client
- [ ] Define SQLAlchemy models (for code-level schema reference)
- [ ] Write and run seed script (3 facilities, ~15 assets, 48h of readings)

### Phase 2: Backend API (Day 2)
- [ ] FastAPI app skeleton with CORS middleware
- [ ] `GET /api/v1/facilities` and `GET /api/v1/facilities/{id}`
- [ ] `GET /api/v1/readings` with filtering + pagination
- [ ] `GET /api/v1/readings/latest`
- [ ] `GET /api/v1/dashboard/summary/{facility_id}` — aggregated metrics
- [ ] `GET /api/v1/dashboard/timeseries/{facility_id}` — bucketed time-series
- [ ] Background task: generate new sensor readings every 30s (insert into Supabase)

### Phase 3: Frontend Dashboard (Days 3-4)
- [ ] Vite + React + TypeScript + Ant Design setup
- [ ] API client layer (Axios)
- [ ] AppHeader with facility selector dropdown
- [ ] KPI Statistic cards (total power, output, avg temp, avg pressure)
- [ ] Asset status summary bar
- [ ] Time-series line chart (Recharts) with metric/time-range selectors
- [ ] Asset details table with latest readings per asset
- [ ] Auto-refresh polling (10s interval)
- [ ] Footer with last-refreshed timestamp

### Phase 4: Polish & Documentation (Days 5-6)
- [ ] README with Supabase setup + local dev instructions
- [ ] `.env.example` template for onboarding
- [ ] Error handling & loading states
- [ ] Responsive layout adjustments
- [ ] Code cleanup, type safety review
- [ ] Push to GitHub

---

## 7. Key Design Decisions & Rationale

| Decision                                  | Rationale                                                       |
|-------------------------------------------|-----------------------------------------------------------------|
| **Supabase** over local PostgreSQL/Docker | Offloads DB compute to the cloud; 8 GB RAM + i5 machine cannot comfortably run Docker + Postgres locally |
| **Supabase free tier**                    | 500 MB DB, 50k monthly active users, unlimited API requests — more than enough for a demo project |
| **Direct asyncpg** for heavy queries      | Supabase REST API has overhead; direct PostgreSQL connection is faster for aggregation + bulk inserts |
| **supabase-py** for simple CRUD           | Convenient, typed client for straightforward reads/writes on facilities and assets |
| **SQL migrations over Alembic**           | Supabase manages the DB; raw SQL migrations run in the SQL Editor or Supabase CLI — no need for Alembic's complexity |
| **SQLAlchemy models kept**                | Serve as code-level documentation of the schema; could be used for local testing later |
| **UUID primary keys**                     | Safe for distributed systems, no sequential ID leakage          |
| **Composite index on readings**           | (asset_id, metric_name, timestamp DESC) is the primary query pattern |
| **30-second reading interval**            | Realistic for industrial sensors; enough data density for charts |
| **Facility-level aggregation**            | Dashboard summary aggregates across all assets in a facility    |
| **Polling over WebSockets**               | Simpler to implement; instructions say "polling is fine"        |
| **10s poll interval**                     | Frequent enough for monitoring, light enough on the server      |
| **Recharts** for charting                 | React-native, composable, good time-series support, lightweight |
| **Ant Design** for UI                     | CVector's stack; rich component library (Statistic, Table, Select) |
| **No Docker**                             | Eliminates ~2-3 GB RAM overhead; backend + frontend run natively with minimal resource usage |
| **Vite** over CRA                         | Faster dev server, modern defaults, smaller bundle              |

---

## 8. Data Flow Diagram

```
┌──────────┐  every 30s   ┌──────────────────────┐
│ Seed /   │──────────────▶│  Supabase            │
│ Generator│  INSERT       │  (hosted PostgreSQL)  │
└──────────┘  (asyncpg)   └──────────┬────────────┘
                                     │ asyncpg / supabase-py
                                     ▼
┌──────────┐   HTTP GET    ┌──────────────┐
│  React   │◀─────────────▶│   FastAPI    │
│Dashboard │  JSON resp    │   Backend    │
└──────────┘  every 10s    │   (local)    │
   (poll)                  └──────────────┘
```

---

## 9. Risk & Mitigation

| Risk                                      | Mitigation                                                           |
|-------------------------------------------|----------------------------------------------------------------------|
| Large readings table slows queries        | Composite index; time-bounded queries; LIMIT defaults                |
| Supabase free tier DB size limit (500 MB) | Seed only 48h of data; add a cleanup job to prune old readings       |
| Supabase connection limits (free tier)    | Use connection pooling (Supabase Pooler on port 6543); limit pool size to 5 |
| Network latency to Supabase               | Direct asyncpg connection (not REST); choose nearest Supabase region |
| Seed script takes too long remotely       | Bulk INSERT with `executemany`; batch 1000 rows per insert           |
| CORS issues in dev                        | FastAPI CORSMiddleware with localhost origins                        |
| `.env` secrets leaked to Git              | `.gitignore` includes `.env`; provide `.env.example` with placeholders |
| Supabase project goes idle (free tier)   | Free projects pause after 1 week of inactivity; reactivate from dashboard |

---

## 10. Supabase-Specific Considerations

### 10.1 Connection Pooling

Supabase provides two connection endpoints:
- **Direct connection** (port 5432) — for migrations and admin tasks
- **Connection pooler** (port 6543, via Supavisor) — for application connections

The backend should use the **pooler endpoint** for all runtime queries to stay within free-tier connection limits (max ~15 direct connections).

### 10.2 Monitoring & Dashboard

Supabase provides a built-in **Table Editor** and **SQL Editor** that can be used to:
- Inspect seed data visually
- Run ad-hoc queries during development
- Monitor table sizes and row counts

### 10.3 Future Enhancements (Post-MVP)

- **Supabase Realtime**: Subscribe to `sensor_readings` inserts from the frontend, replacing polling with push-based updates
- **Supabase Edge Functions**: Move the reading generator to a Supabase Edge Function (Deno) running on a cron schedule, eliminating the need for the local background task
- **Supabase Auth**: Add user authentication for operators with role-based access to specific facilities

---

*This design plan is the blueprint for the full implementation. Each phase is designed to produce a working, testable increment so that even partial completion demonstrates complete features. No Docker or local PostgreSQL installation is required — all database compute runs on Supabase's free-tier cloud infrastructure.*
