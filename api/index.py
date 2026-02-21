"""
Vercel Serverless Function — FastAPI app that serves the dashboard API.

This single file replaces the full FastAPI backend for Vercel deployment.
It connects to Supabase PostgreSQL via asyncpg on every request
(no persistent pool, since serverless functions are short-lived).
"""

import os
import asyncpg
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── FastAPI app ─────────────────────────────────────

app = FastAPI(title="Plant Monitor Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Database helper ─────────────────────────────────

_pool: asyncpg.Pool | None = None


def _get_db_url() -> str:
    url = os.environ["SUPABASE_DB_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def get_pool() -> asyncpg.Pool:
    """Reuse pool across warm invocations; create on cold start."""
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(
            _get_db_url(),
            min_size=1,
            max_size=3,
            command_timeout=10,
        )
    return _pool


# ── Pydantic schemas ───────────────────────────────


class FacilityItem(BaseModel):
    id: UUID
    name: str
    location: str
    type: str
    asset_count: int
    created_at: datetime


class FacilitiesListResponse(BaseModel):
    facilities: list[FacilityItem]


class AssetStatusItem(BaseModel):
    id: UUID
    name: str
    type: str
    status: str


class MetricKPI(BaseModel):
    metric_name: str
    current_value: float
    avg_value: float
    min_value: float
    max_value: float
    unit: str


class FacilitySummaryResponse(BaseModel):
    facility_id: UUID
    facility_name: str
    location: str
    facility_type: str
    total_assets: int
    operational_count: int
    maintenance_count: int
    kpis: list[MetricKPI]
    assets: list[AssetStatusItem]
    period_hours: int


class TimeseriesPoint(BaseModel):
    timestamp: datetime
    value: float


class AssetTimeseries(BaseModel):
    asset_id: UUID
    asset_name: str
    data: list[TimeseriesPoint]


class TimeseriesResponse(BaseModel):
    facility_id: UUID
    facility_name: str
    metric_name: str
    unit: str
    start: datetime
    end: datetime
    bucket_minutes: int
    series: list[AssetTimeseries]


class MetricName(str, Enum):
    temperature = "temperature"
    pressure = "pressure"
    power_consumption = "power_consumption"
    production_output = "production_output"


# ── Endpoints ──────────────────────────────────────


@app.get("/api/v1/facilities", response_model=FacilitiesListResponse)
async def list_facilities():
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT
            f.id, f.name, f.location, f.type, f.created_at,
            COUNT(a.id)::int AS asset_count
        FROM facilities f
        LEFT JOIN assets a ON a.facility_id = f.id
        GROUP BY f.id
        ORDER BY f.name
    """)
    return FacilitiesListResponse(
        facilities=[
            FacilityItem(
                id=r["id"], name=r["name"], location=r["location"],
                type=r["type"], asset_count=r["asset_count"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    )


@app.get("/api/v1/dashboard/summary/{facility_id}", response_model=FacilitySummaryResponse)
async def get_facility_summary(
    facility_id: UUID,
    hours: int = Query(default=24, ge=1, le=48),
):
    pool = await get_pool()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Fetch facility
    fac = await pool.fetchrow(
        "SELECT id, name, location, type FROM facilities WHERE id = $1",
        facility_id,
    )
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Fetch assets
    assets = await pool.fetch(
        "SELECT id, name, type, status FROM assets WHERE facility_id = $1 ORDER BY name",
        facility_id,
    )

    # Fetch KPIs
    kpis = await pool.fetch("""
        WITH latest AS (
            SELECT DISTINCT ON (sr.metric_name)
                sr.metric_name, sr.value AS current_value, sr.unit
            FROM sensor_readings sr
            JOIN assets a ON a.id = sr.asset_id
            WHERE a.facility_id = $1 AND sr.timestamp >= $2
            ORDER BY sr.metric_name, sr.timestamp DESC
        ),
        agg AS (
            SELECT
                sr.metric_name,
                ROUND(AVG(sr.value)::numeric, 2) AS avg_value,
                ROUND(MIN(sr.value)::numeric, 2) AS min_value,
                ROUND(MAX(sr.value)::numeric, 2) AS max_value
            FROM sensor_readings sr
            JOIN assets a ON a.id = sr.asset_id
            WHERE a.facility_id = $1 AND sr.timestamp >= $2
            GROUP BY sr.metric_name
        )
        SELECT l.metric_name, l.current_value, l.unit,
               a.avg_value, a.min_value, a.max_value
        FROM latest l JOIN agg a ON a.metric_name = l.metric_name
        ORDER BY l.metric_name
    """, facility_id, since)

    operational = sum(1 for a in assets if a["status"] == "operational")
    maintenance = sum(1 for a in assets if a["status"] == "maintenance")

    return FacilitySummaryResponse(
        facility_id=fac["id"],
        facility_name=fac["name"],
        location=fac["location"],
        facility_type=fac["type"],
        total_assets=len(assets),
        operational_count=operational,
        maintenance_count=maintenance,
        kpis=[
            MetricKPI(
                metric_name=k["metric_name"],
                current_value=float(k["current_value"]),
                avg_value=float(k["avg_value"]),
                min_value=float(k["min_value"]),
                max_value=float(k["max_value"]),
                unit=k["unit"],
            )
            for k in kpis
        ],
        assets=[
            AssetStatusItem(id=a["id"], name=a["name"], type=a["type"], status=a["status"])
            for a in assets
        ],
        period_hours=hours,
    )


@app.get("/api/v1/dashboard/timeseries/{facility_id}", response_model=TimeseriesResponse)
async def get_facility_timeseries(
    facility_id: UUID,
    metric: MetricName = Query(default=MetricName.temperature),
    hours: int = Query(default=24, ge=1, le=48),
    bucket_minutes: int = Query(default=5, ge=1, le=60),
):
    pool = await get_pool()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Fetch facility
    fac = await pool.fetchrow(
        "SELECT id, name, location, type FROM facilities WHERE id = $1",
        facility_id,
    )
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")

    unit_map = {
        "temperature": "C",
        "pressure": "bar",
        "power_consumption": "kW",
        "production_output": "units/hr",
    }

    rows = await pool.fetch("""
        SELECT
            a.id   AS asset_id,
            a.name AS asset_name,
            date_bin($4::interval, sr.timestamp, $3) AS bucket,
            ROUND(AVG(sr.value)::numeric, 2) AS avg_value
        FROM sensor_readings sr
        JOIN assets a ON a.id = sr.asset_id
        WHERE a.facility_id = $1
          AND sr.metric_name = $2
          AND sr.timestamp >= $3
        GROUP BY a.id, a.name, bucket
        ORDER BY a.name, bucket
    """, facility_id, metric.value, since, timedelta(minutes=bucket_minutes))

    # Reorganize by asset
    series_map: dict[UUID, dict] = {}
    for r in rows:
        aid = r["asset_id"]
        if aid not in series_map:
            series_map[aid] = {"asset_id": aid, "asset_name": r["asset_name"], "data": []}
        series_map[aid]["data"].append({"timestamp": r["bucket"], "value": float(r["avg_value"])})

    now = datetime.now(timezone.utc)

    return TimeseriesResponse(
        facility_id=fac["id"],
        facility_name=fac["name"],
        metric_name=metric.value,
        unit=unit_map.get(metric.value, ""),
        start=now - timedelta(hours=hours),
        end=now,
        bucket_minutes=bucket_minutes,
        series=[
            AssetTimeseries(
                asset_id=s["asset_id"],
                asset_name=s["asset_name"],
                data=[TimeseriesPoint(timestamp=p["timestamp"], value=p["value"]) for p in s["data"]],
            )
            for s in series_map.values()
        ],
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
