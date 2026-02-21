"""Service layer — SQL queries for the dashboard.

Uses asyncpg directly (pool) for heavy aggregation queries.
Supabase PostgREST does not support GROUP BY / window functions,
so we use raw SQL here.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.database import get_pool


async def fetch_facility(facility_id: UUID) -> dict | None:
    """Fetch a facility by ID. Returns dict or None."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, name, location, type FROM facilities WHERE id = $1",
        facility_id,
    )
    return dict(row) if row else None


async def fetch_facilities_with_counts() -> list[dict]:
    """List all facilities with asset counts."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT
            f.id,
            f.name,
            f.location,
            f.type,
            f.created_at,
            COUNT(a.id)::int AS asset_count
        FROM facilities f
        LEFT JOIN assets a ON a.facility_id = f.id
        GROUP BY f.id
        ORDER BY f.name
    """)
    return [dict(r) for r in rows]


async def fetch_assets_for_facility(facility_id: UUID) -> list[dict]:
    """Return the assets belonging to a facility."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, name, type, status FROM assets WHERE facility_id = $1 ORDER BY name",
        facility_id,
    )
    return [dict(r) for r in rows]


async def fetch_kpis(facility_id: UUID, hours: int = 24) -> list[dict]:
    """
    Calculate aggregated KPIs (avg, min, max, current) for each metric
    across all assets of a facility in the last `hours` hours.

    current_value = most recent recorded value.
    """
    pool = await get_pool()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

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

    return [dict(r) for r in rows]


async def fetch_timeseries(
    facility_id: UUID,
    metric_name: str,
    hours: int = 24,
    bucket_minutes: int = 5,
) -> list[dict]:
    """
    Return time series grouped by asset and time bucket.

    Downsamples using date_bin to reduce data points.
    E.g.: 24h with 5min bucket = 288 points per asset (instead of 2880).
    """
    pool = await get_pool()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Usa date_bin (Postgres 14+) para bucketing preciso
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
    """, facility_id, metric_name, since, timedelta(minutes=bucket_minutes))

    # Reorganize by asset
    series_map: dict[UUID, dict] = {}
    for r in rows:
        aid = r["asset_id"]
        if aid not in series_map:
            series_map[aid] = {
                "asset_id": aid,
                "asset_name": r["asset_name"],
                "data": [],
            }
        series_map[aid]["data"].append({
            "timestamp": r["bucket"],
            "value": float(r["avg_value"]),
        })

    return list(series_map.values())
