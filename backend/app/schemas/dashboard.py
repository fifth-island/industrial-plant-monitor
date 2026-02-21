"""Pydantic schemas for the dashboard endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Modelos auxiliares ──────────────────────────────


class AssetStatusItem(BaseModel):
    """Status de um asset individual."""
    id: UUID
    name: str
    type: str
    status: str = Field(description="operational | maintenance")


class MetricKPI(BaseModel):
    """Aggregated KPI for a metric over the last N hours."""
    metric_name: str
    current_value: float = Field(description="Latest recorded value")
    avg_value: float
    min_value: float
    max_value: float
    unit: str


# ── Response: Summary ───────────────────────────────


class FacilitySummaryResponse(BaseModel):
    """Response for GET /dashboard/summary/{facility_id}."""
    facility_id: UUID
    facility_name: str
    location: str
    facility_type: str
    total_assets: int
    operational_count: int
    maintenance_count: int
    kpis: list[MetricKPI]
    assets: list[AssetStatusItem]
    period_hours: int = Field(description="KPI time window in hours")


# ── Response: Timeseries ────────────────────────────


class TimeseriesPoint(BaseModel):
    """A single chart point (timestamp + bucket average value)."""
    timestamp: datetime
    value: float


class AssetTimeseries(BaseModel):
    """Time series for a single asset and metric."""
    asset_id: UUID
    asset_name: str
    data: list[TimeseriesPoint]


class TimeseriesResponse(BaseModel):
    """Response for GET /dashboard/timeseries/{facility_id}."""
    facility_id: UUID
    facility_name: str
    metric_name: str
    unit: str
    start: datetime
    end: datetime
    bucket_minutes: int = Field(description="Aggregation bucket size in minutes")
    series: list[AssetTimeseries]


# ── Response: Facilities list ───────────────────────


class FacilityItem(BaseModel):
    """A single item in the facilities list."""
    id: UUID
    name: str
    location: str
    type: str
    asset_count: int
    created_at: datetime


class FacilitiesListResponse(BaseModel):
    """Response for GET /facilities."""
    facilities: list[FacilityItem]
