"""API routes for the dashboard."""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

from app.schemas.dashboard import (
    AssetStatusItem,
    AssetTimeseries,
    FacilitiesListResponse,
    FacilityItem,
    FacilitySummaryResponse,
    MetricKPI,
    TimeseriesPoint,
    TimeseriesResponse,
)
from app.services.dashboard import (
    fetch_assets_for_facility,
    fetch_facility,
    fetch_facilities_with_counts,
    fetch_kpis,
    fetch_timeseries,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
facilities_router = APIRouter(prefix="/facilities", tags=["Facilities"])


# ── Enum to validate metric_name in the query string ──


class MetricName(str, Enum):
    temperature = "temperature"
    pressure = "pressure"
    power_consumption = "power_consumption"
    production_output = "production_output"


# ── GET /facilities ─────────────────────────────────


@facilities_router.get(
    "",
    response_model=FacilitiesListResponse,
    summary="List all facilities",
)
async def list_facilities():
    """Return all facilities with asset counts."""
    rows = await fetch_facilities_with_counts()
    return FacilitiesListResponse(
        facilities=[
            FacilityItem(
                id=r["id"],
                name=r["name"],
                location=r["location"],
                type=r["type"],
                asset_count=r["asset_count"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    )


# ── GET /dashboard/summary/{facility_id} ───────────


@router.get(
    "/summary/{facility_id}",
    response_model=FacilitySummaryResponse,
    summary="Summary / KPIs for a facility",
)
async def get_facility_summary(
    facility_id: UUID,
    hours: int = Query(default=24, ge=1, le=48, description="Time window in hours"),
):
    """
    Return aggregated KPIs (avg temperature, pressure, total energy, etc.)
    and the status of each asset in the facility.
    """
    try:
        # Check if facility exists
        facility = await fetch_facility(facility_id)
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

        # Fetch assets and KPIs in parallel
        import asyncio
        assets_task = fetch_assets_for_facility(facility_id)
        kpis_task = fetch_kpis(facility_id, hours)
        assets, kpis = await asyncio.gather(assets_task, kpis_task)

        operational = sum(1 for a in assets if a["status"] == "operational")
        maintenance = sum(1 for a in assets if a["status"] == "maintenance")

        return FacilitySummaryResponse(
            facility_id=facility["id"],
            facility_name=facility["name"],
            location=facility["location"],
            facility_type=facility["type"],
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
                AssetStatusItem(
                    id=a["id"],
                    name=a["name"],
                    type=a["type"],
                    status=a["status"],
                )
                for a in assets
            ],
            period_hours=hours,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Summary endpoint failed for facility %s", facility_id)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── GET /dashboard/timeseries/{facility_id} ────────


@router.get(
    "/timeseries/{facility_id}",
    response_model=TimeseriesResponse,
    summary="Historical data for charts",
)
async def get_facility_timeseries(
    facility_id: UUID,
    metric: MetricName = Query(
        default=MetricName.temperature,
        description="Metric to query",
    ),
    hours: int = Query(default=24, ge=1, le=48, description="Time window in hours"),
    bucket_minutes: int = Query(
        default=5, ge=1, le=60, description="Aggregation bucket size in minutes"
    ),
):
    """
    Return time series for a metric, grouped by asset.
    Data is downsampled into N-minute buckets (average) for
    chart performance in Recharts.
    """
    try:
        facility = await fetch_facility(facility_id)
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

        # Determine unit from metric
        unit_map = {
            "temperature": "C",
            "pressure": "bar",
            "power_consumption": "kW",
            "production_output": "units/hr",
        }

        series_data = await fetch_timeseries(
            facility_id, metric.value, hours, bucket_minutes
        )

        now = datetime.now(timezone.utc)

        return TimeseriesResponse(
            facility_id=facility["id"],
            facility_name=facility["name"],
            metric_name=metric.value,
            unit=unit_map.get(metric.value, ""),
            start=now - timedelta(hours=hours),
            end=now,
            bucket_minutes=bucket_minutes,
            series=[
                AssetTimeseries(
                    asset_id=s["asset_id"],
                    asset_name=s["asset_name"],
                    data=[
                        TimeseriesPoint(timestamp=p["timestamp"], value=p["value"])
                        for p in s["data"]
                    ],
                )
                for s in series_data
            ],
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Timeseries endpoint failed for facility %s", facility_id)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Temporary debug endpoint ──────────

@router.get("/debug/{facility_id}")
async def debug_query(facility_id: UUID):
    """Temporary endpoint that returns raw error info for diagnosis."""
    import traceback as tb_mod
    from app.database import get_pool
    results = {}

    # 1. Test pool
    try:
        pool = await get_pool()
        results["pool"] = f"OK (size={pool.get_size()}, free={pool.get_idle_size()})"
    except Exception as e:
        results["pool"] = f"FAIL: {e}"
        return results

    # 2. Test facility fetch
    try:
        row = await pool.fetchrow("SELECT id, name FROM facilities WHERE id = $1", facility_id)
        results["facility"] = dict(row) if row else "NOT FOUND"
    except Exception as e:
        results["facility"] = f"FAIL: {e}\n{tb_mod.format_exc()}"

    # 3. Test simple count
    try:
        row = await pool.fetchrow(
            "SELECT COUNT(*) AS cnt FROM sensor_readings sr JOIN assets a ON a.id = sr.asset_id WHERE a.facility_id = $1",
            facility_id,
        )
        results["reading_count"] = row["cnt"] if row else 0
    except Exception as e:
        results["reading_count"] = f"FAIL: {e}\n{tb_mod.format_exc()}"

    # 4. Test the KPI query
    try:
        from datetime import timedelta as td
        since = datetime.now(timezone.utc) - td(hours=24)
        rows = await pool.fetch("""
            WITH latest AS (
                SELECT DISTINCT ON (sr.metric_name)
                    sr.metric_name,
                    sr.value AS current_value,
                    sr.unit
                FROM sensor_readings sr
                JOIN assets a ON a.id = sr.asset_id
                WHERE a.facility_id = $1
                  AND sr.timestamp >= $2
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
                WHERE a.facility_id = $1
                  AND sr.timestamp >= $2
                GROUP BY sr.metric_name
            )
            SELECT
                l.metric_name,
                l.current_value,
                l.unit,
                a.avg_value,
                a.min_value,
                a.max_value
            FROM latest l
            JOIN agg a ON a.metric_name = l.metric_name
            ORDER BY l.metric_name
        """, facility_id, since)
        results["kpis"] = [dict(r) for r in rows]
    except Exception as e:
        results["kpis"] = f"FAIL: {e}\n{tb_mod.format_exc()}"

    # 5. Test the timeseries query
    try:
        from datetime import timedelta as td
        since = datetime.now(timezone.utc) - td(hours=24)
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
        """, facility_id, "temperature", since, td(minutes=5))
        results["timeseries_count"] = len(rows)
    except Exception as e:
        results["timeseries"] = f"FAIL: {e}\n{tb_mod.format_exc()}"

    return results
