"""Pydantic schemas for the dashboard endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Modelos auxiliares ──────────────────────────────


class AssetStatusItem(BaseModel):
    """Status and metrics for an individual asset."""
    id: UUID
    name: str
    type: str
    status: str = Field(description="operational | maintenance")
    # Temperature
    temperature: float | None = None
    temperature_unit: str | None = None
    temperature_range: dict | None = None
    # Pressure
    pressure: float | None = None
    pressure_unit: str | None = None
    pressure_range: dict | None = None
    # Power
    power: float | None = None
    power_unit: str | None = None
    power_range: dict | None = None
    # Production
    production: float | None = None
    production_unit: str | None = None
    production_range: dict | None = None


class MetricKPI(BaseModel):
    """Aggregated KPI for a metric over the last N hours."""
    metric_name: str
    current_value: float = Field(description="Latest recorded value")
    avg_value: float
    min_value: float
    max_value: float
    unit: str


class InsightItem(BaseModel):
    """Operational insight based on sensor data analysis."""
    severity: str = Field(description="ok | low | medium | high")
    title: str
    description: str
    detected_at: datetime = Field(description="Timestamp when insight was detected")
    asset_name: str | None = None


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
    active_alerts_count: int = Field(description="Number of high/medium severity alerts")
    kpis: list[MetricKPI]
    insights: list[InsightItem]
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
