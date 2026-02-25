"""API routes for the dashboard."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from app.schemas.dashboard import (
    AssetStatusItem,
    AssetTimeseries,
    FacilitiesListResponse,
    FacilityItem,
    FacilitySummaryResponse,
    InsightItem,
    MetricKPI,
    TimeseriesPoint,
    TimeseriesResponse,
)
from app.services.dashboard import (
    fetch_assets_for_facility,
    fetch_facility,
    fetch_facilities_with_counts,
    fetch_insights,
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

        # Fetch assets, KPIs, and insights in parallel
        import asyncio
        assets_task = fetch_assets_for_facility(facility_id)
        kpis_task = fetch_kpis(facility_id, hours)
        insights_task = fetch_insights(facility_id)
        assets, kpis, insights = await asyncio.gather(assets_task, kpis_task, insights_task)

        operational = sum(1 for a in assets if a["status"] == "operational")
        maintenance = sum(1 for a in assets if a["status"] == "maintenance")
        
        # Count active alerts (high and medium severity)
        active_alerts = sum(1 for i in insights if i["severity"] in ("high", "medium"))

        return FacilitySummaryResponse(
            facility_id=facility["id"],
            facility_name=facility["name"],
            location=facility["location"],
            facility_type=facility["type"],
            total_assets=len(assets),
            operational_count=operational,
            maintenance_count=maintenance,
            active_alerts_count=active_alerts,
            kpis=[
                MetricKPI(
                    metric_name=k["metric_name"],
                    current_value=float(k["current_value"]),
                    avg_value=float(k["avg_value"]),
                    min_value=float(k["min_value"]),
                    max_value=float(k["max_value"]),
                    p50_value=float(k["p50_value"]),
                    p90_value=float(k["p90_value"]),
                    p95_value=float(k["p95_value"]),
                    unit=k["unit"],
                )
                for k in kpis
            ],
            insights=[
                InsightItem(
                    severity=i["severity"],
                    title=i["title"],
                    description=i["description"],
                    detected_at=i["detected_at"],
                )
                for i in insights
            ],
            assets=[
                AssetStatusItem(
                    id=a["id"],
                    name=a["name"],
                    type=a["type"],
                    status=a["status"],
                    temperature=float(a["temperature"]) if a["temperature"] is not None else None,
                    temperature_unit=a["temperature_unit"],
                    temperature_range=a["temperature_range"],
                    pressure=float(a["pressure"]) if a["pressure"] is not None else None,
                    pressure_unit=a["pressure_unit"],
                    pressure_range=a["pressure_range"],
                    power=float(a["power"]) if a["power"] is not None else None,
                    power_unit=a["power_unit"],
                    power_range=a["power_range"],
                    production=float(a["production"]) if a["production"] is not None else None,
                    production_unit=a["production_unit"],
                    production_range=a["production_range"],
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


# ── GET /dashboard/stream/{facility_id} ────────────


@router.get(
    "/stream/{facility_id}",
    summary="Server-Sent Events stream for live dashboard updates",
)
async def stream_facility_summary(
    request: Request,
    facility_id: UUID,
    hours: int = Query(default=24, ge=1, le=48, description="Time window in hours"),
):
    """
    Stream live dashboard updates using Server-Sent Events (SSE).
    Sends summary data immediately when new sensor readings are inserted.
    Sends keep-alive pings every 15 seconds if no data updates.
    """
    from app.events import broadcaster
    
    async def event_generator():
        """Generate SSE events when facility data updates."""
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE stream for facility %s", facility_id)
                    break
                
                # Wait for facility update event (15 second timeout for keep-alive)
                update_received = await broadcaster.wait_for_update(facility_id, timeout=15.0)
                
                if update_received:
                    # Fetch fresh summary data (reuse existing service functions)
                    try:
                        facility = await fetch_facility(facility_id)
                        if not facility:
                            yield f"event: error\ndata: {json.dumps({'error': 'Facility not found'})}\n\n"
                            break
                        
                        assets_task = fetch_assets_for_facility(facility_id)
                        kpis_task = fetch_kpis(facility_id, hours)
                        insights_task = fetch_insights(facility_id)
                        assets, kpis, insights = await asyncio.gather(assets_task, kpis_task, insights_task)
                        
                        operational = sum(1 for a in assets if a["status"] == "operational")
                        maintenance = sum(1 for a in assets if a["status"] == "maintenance")
                        
                        # Count active alerts (high and medium severity)
                        active_alerts = sum(1 for i in insights if i["severity"] in ("high", "medium"))
                        
                        summary_data = {
                            "facility_id": str(facility["id"]),
                            "facility_name": facility["name"],
                            "location": facility["location"],
                            "facility_type": facility["type"],
                            "total_assets": len(assets),
                            "operational_count": operational,
                            "maintenance_count": maintenance,
                            "active_alerts_count": active_alerts,
                            "kpis": [
                                {
                                    "metric_name": k["metric_name"],
                                    "current_value": float(k["current_value"]),
                                    "avg_value": float(k["avg_value"]),
                                    "min_value": float(k["min_value"]),
                                    "max_value": float(k["max_value"]),
                                    "unit": k["unit"],
                                }
                                for k in kpis
                            ],
                            "insights": [
                                {
                                    "severity": i["severity"],
                                    "title": i["title"],
                                    "description": i["description"],
                                    "detected_at": i["detected_at"].isoformat(),
                                }
                                for i in insights
                            ],
                            "assets": [
                                {
                                    "id": str(a["id"]),
                                    "name": a["name"],
                                    "type": a["type"],
                                    "status": a["status"],
                                    "temperature": float(a["temperature"]) if a["temperature"] is not None else None,
                                    "temperature_unit": a["temperature_unit"],
                                    "temperature_range": a["temperature_range"],
                                    "pressure": float(a["pressure"]) if a["pressure"] is not None else None,
                                    "pressure_unit": a["pressure_unit"],
                                    "pressure_range": a["pressure_range"],
                                    "power": float(a["power"]) if a["power"] is not None else None,
                                    "power_unit": a["power_unit"],
                                    "power_range": a["power_range"],
                                    "production": float(a["production"]) if a["production"] is not None else None,
                                    "production_unit": a["production_unit"],
                                    "production_range": a["production_range"],
                                }
                                for a in assets
                            ],
                            "period_hours": hours,
                        }
                        
                        # Send SSE event
                        yield f"event: summary\ndata: {json.dumps(summary_data)}\n\n"
                        logger.debug("Sent SSE update for facility %s", facility_id)
                        
                    except Exception as e:
                        logger.exception("Error fetching summary for SSE stream")
                        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                else:
                    # Timeout - send keep-alive ping
                    yield ": ping\n\n"
                    
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled for facility %s", facility_id)
        except Exception:
            logger.exception("SSE stream error for facility %s", facility_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
