"""API routes for the dashboard."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

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
