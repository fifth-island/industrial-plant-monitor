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
    """
    Return assets with their latest sensor readings for temperature, pressure, power, and production.
    Includes current value and min/max ranges for each metric from asset_operational_ranges table.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT
            a.id,
            a.name,
            a.type,
            a.status,
            MAX(CASE WHEN sr.metric_name = 'temperature' THEN sr.value END) AS temperature,
            MAX(CASE WHEN sr.metric_name = 'temperature' THEN sr.unit END) AS temperature_unit,
            MAX(CASE WHEN sr.metric_name = 'pressure' THEN sr.value END) AS pressure,
            MAX(CASE WHEN sr.metric_name = 'pressure' THEN sr.unit END) AS pressure_unit,
            MAX(CASE WHEN sr.metric_name = 'power_consumption' THEN sr.value END) AS power,
            MAX(CASE WHEN sr.metric_name = 'power_consumption' THEN sr.unit END) AS power_unit,
            MAX(CASE WHEN sr.metric_name = 'production_output' THEN sr.value END) AS production,
            MAX(CASE WHEN sr.metric_name = 'production_output' THEN sr.unit END) AS production_unit
        FROM assets a
        LEFT JOIN LATERAL (
            SELECT metric_name, value, unit
            FROM sensor_readings
            WHERE asset_id = a.id
              AND metric_name IN ('temperature', 'pressure', 'power_consumption', 'production_output')
            ORDER BY timestamp DESC
            LIMIT 4
        ) sr ON true
        WHERE a.facility_id = $1
        GROUP BY a.id, a.name, a.type, a.status
        ORDER BY a.name
    """, facility_id)
    
    # Fetch operational ranges for all assets in this facility
    range_rows = await pool.fetch("""
        SELECT aor.asset_id, aor.metric_name, aor.min_value, aor.max_value
        FROM asset_operational_ranges aor
        JOIN assets a ON a.id = aor.asset_id
        WHERE a.facility_id = $1
    """, facility_id)
    
    # Group ranges by asset_id
    ranges_by_asset = {}
    for r in range_rows:
        asset_id = r['asset_id']
        if asset_id not in ranges_by_asset:
            ranges_by_asset[asset_id] = {}
        ranges_by_asset[asset_id][r['metric_name']] = {
            'min': r['min_value'],
            'max': r['max_value']
        }
    
    # Build asset response with ranges from database
    assets = []
    for r in rows:
        asset = dict(r)
        asset_id = asset['id']
        asset_ranges = ranges_by_asset.get(asset_id, {})
        
        # Add ranges (with fallback to None if not configured)
        asset['temperature_range'] = asset_ranges.get('temperature')
        asset['pressure_range'] = asset_ranges.get('pressure')
        asset['power_range'] = asset_ranges.get('power_consumption')
        asset['production_range'] = asset_ranges.get('production_output')
        
        assets.append(asset)
    
    return assets


async def manage_insights(facility_id: UUID) -> None:
    """
    Analyze current sensor data and manage insights in database:
    - Create new insights when issues detected
    - Resolve existing insights when conditions clear
    - Update descriptions for ongoing issues (via upsert)
    """
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    
    # Get current readings and 1-hour-ago readings for trend analysis
    recent_window = now - timedelta(minutes=60)
    trend_window = now - timedelta(minutes=90)  # 60-90 min ago for comparison
    
    # Fetch current values per asset for detailed analysis
    rows = await pool.fetch("""
        WITH current_readings AS (
            SELECT DISTINCT ON (a.id, sr.metric_name)
                a.id as asset_id,
                a.name as asset_name,
                sr.metric_name,
                sr.value as current_value,
                sr.unit
            FROM sensor_readings sr
            JOIN assets a ON a.id = sr.asset_id
            WHERE a.facility_id = $1
              AND sr.timestamp >= $2
            ORDER BY a.id, sr.metric_name, sr.timestamp DESC
        ),
        trend_readings AS (
            SELECT
                a.id as asset_id,
                sr.metric_name,
                ROUND(AVG(sr.value)::numeric, 2) as trend_value
            FROM sensor_readings sr
            JOIN assets a ON a.id = sr.asset_id
            WHERE a.facility_id = $1
              AND sr.timestamp BETWEEN $3 AND $2
            GROUP BY a.id, sr.metric_name
        )
        SELECT
            c.asset_id,
            c.asset_name,
            c.metric_name,
            c.current_value,
            c.unit,
            t.trend_value
        FROM current_readings c
        LEFT JOIN trend_readings t ON t.asset_id = c.asset_id AND t.metric_name = c.metric_name
    """, facility_id, recent_window, trend_window)
    
    # Group by asset for asset-level analysis
    assets_data = {}
    for r in rows:
        aid = r['asset_id']
        if aid not in assets_data:
            assets_data[aid] = {'asset_id': aid, 'asset_name': r['asset_name'], 'metrics': {}}
        metric = dict(r)
        metric['current_value'] = float(metric['current_value'])
        if metric['trend_value'] is not None:
            metric['trend_value'] = float(metric['trend_value'])
        assets_data[aid]['metrics'][r['metric_name']] = metric
    
    # Fetch operational ranges for all assets in this facility
    range_rows = await pool.fetch("""
        SELECT aor.asset_id, aor.metric_name, aor.min_value, aor.max_value, aor.unit
        FROM asset_operational_ranges aor
        JOIN assets a ON a.id = aor.asset_id
        WHERE a.facility_id = $1
    """, facility_id)
    
    # Group ranges by asset_id
    ranges_by_asset = {}
    for r in range_rows:
        aid = r['asset_id']
        if aid not in ranges_by_asset:
            ranges_by_asset[aid] = {}
        ranges_by_asset[aid][r['metric_name']] = {
            'min': float(r['min_value']),
            'max': float(r['max_value']),
            'unit': r['unit']
        }
    
    detected_issues = []
    assets_to_update_status = {}  # Track which assets need status updates
    
    # Check each asset for issues
    for asset_id, asset_data in assets_data.items():
        metrics = asset_data['metrics']
        asset_name = asset_data['asset_name']
        asset_ranges = ranges_by_asset.get(asset_id, {})
        
        # Track if any metric is out of range for this asset
        any_out_of_range = False
        
        # Check temperature
        if 'temperature' in metrics and 'temperature' in asset_ranges:
            temp = metrics['temperature']
            temp_range = asset_ranges['temperature']
            current = temp['current_value']
            
            # Out of range = maintenance
            if current < temp_range['min'] or current > temp_range['max']:
                any_out_of_range = True
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'temperature',
                    'threshold_type': 'out_of_range',
                    'severity': 'high',
                    'title': 'Temperature Out of Range',
                    'description': f"{asset_name}: Temperature at {current:.1f}{temp['unit']} - outside acceptable range ({temp_range['min']:.0f}-{temp_range['max']:.0f}{temp['unit']})"
                })
            # 90-100% of max or 0-110% of min = warning
            elif current >= temp_range['max'] * 0.9 or current <= temp_range['min'] * 1.1:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'temperature',
                    'threshold_type': 'approaching_limit',
                    'severity': 'medium',
                    'title': 'Temperature Approaching Limit',
                    'description': f"{asset_name}: Temperature at {current:.1f}{temp['unit']} - approaching range limit"
                })
            # 75-90% of max = low severity
            elif current >= temp_range['max'] * 0.75:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'temperature',
                    'threshold_type': 'elevated',
                    'severity': 'low',
                    'title': 'Elevated Temperature',
                    'description': f"{asset_name}: Temperature at {current:.1f}{temp['unit']} - monitor closely"
                })
            
            # Check temperature trend
            if temp['trend_value'] and current > temp['trend_value'] + 10:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'temperature',
                    'threshold_type': 'rising_trend',
                    'severity': 'medium',
                    'title': 'Rising Temperature Trend',
                    'description': f"{asset_name}: Temperature increased {current - temp['trend_value']:.1f}{temp['unit']} in last hour"
                })
        
        # Check pressure
        if 'pressure' in metrics and 'pressure' in asset_ranges:
            pressure = metrics['pressure']
            pressure_range = asset_ranges['pressure']
            current = pressure['current_value']
            
            # Out of range = maintenance
            if current < pressure_range['min'] or current > pressure_range['max']:
                any_out_of_range = True
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'pressure',
                    'threshold_type': 'out_of_range',
                    'severity': 'high',
                    'title': 'Pressure Out of Range',
                    'description': f"{asset_name}: Pressure at {current:.1f}{pressure['unit']} - outside acceptable range ({pressure_range['min']:.0f}-{pressure_range['max']:.0f}{pressure['unit']})"
                })
            # Approaching limits
            elif current >= pressure_range['max'] * 0.9 or current <= pressure_range['min'] * 1.1:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'pressure',
                    'threshold_type': 'approaching_limit',
                    'severity': 'medium',
                    'title': 'Pressure Approaching Limit',
                    'description': f"{asset_name}: Pressure at {current:.1f}{pressure['unit']} - monitor closely"
                })
        
        # Check power consumption
        if 'power_consumption' in metrics and 'power_consumption' in asset_ranges:
            power = metrics['power_consumption']
            power_range = asset_ranges['power_consumption']
            current = power['current_value']
            
            # Out of range = maintenance
            if current < power_range['min'] or current > power_range['max']:
                any_out_of_range = True
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'power_consumption',
                    'threshold_type': 'out_of_range',
                    'severity': 'high',
                    'title': 'Power Out of Range',
                    'description': f"{asset_name}: Power at {current:.0f}{power['unit']} - outside acceptable range ({power_range['min']:.0f}-{power_range['max']:.0f}{power['unit']})"
                })
            # Approaching limits
            elif current >= power_range['max'] * 0.9:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'power_consumption',
                    'threshold_type': 'approaching_limit',
                    'severity': 'medium',
                    'title': 'High Power Consumption',
                    'description': f"{asset_name}: Power at {current:.0f}{power['unit']} - approaching maximum"
                })
        
        # Check production output
        if 'production_output' in metrics and 'production_output' in asset_ranges:
            prod = metrics['production_output']
            prod_range = asset_ranges['production_output']
            current = prod['current_value']
            
            # Out of range = maintenance
            if current < prod_range['min'] or current > prod_range['max']:
                any_out_of_range = True
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'production_output',
                    'threshold_type': 'out_of_range',
                    'severity': 'high',
                    'title': 'Production Out of Range',
                    'description': f"{asset_name}: Output at {current:.0f}{prod['unit']} - outside acceptable range ({prod_range['min']:.0f}-{prod_range['max']:.0f}{prod['unit']})"
                })
            # Below 110% of minimum
            elif current <= prod_range['min'] * 1.1:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'production_output',
                    'threshold_type': 'low_production',
                    'severity': 'medium',
                    'title': 'Production Below Target',
                    'description': f"{asset_name}: Output at {current:.0f}{prod['unit']} - below optimal range"
                })
            
            # Check production drop trend
            if prod['trend_value'] and current < prod['trend_value'] - 20:
                detected_issues.append({
                    'asset_id': asset_id,
                    'metric_name': 'production_output',
                    'threshold_type': 'declining_production',
                    'severity': 'medium',
                    'title': 'Production Declining',
                    'description': f"{asset_name}: Output dropped {prod['trend_value'] - current:.0f}{prod['unit']} in last hour"
                })
        
        # Determine required status for this asset
        if any_out_of_range:
            assets_to_update_status[asset_id] = 'maintenance'
        else:
            assets_to_update_status[asset_id] = 'operational'
    
    # Update asset status based on range violations
    for asset_id, new_status in assets_to_update_status.items():
        await pool.execute("""
            UPDATE assets
            SET status = $1, updated_at = now()
            WHERE id = $2 AND status != $1
        """, new_status, asset_id)
    
    # Upsert detected issues (insert or update if already exists)
    for issue in detected_issues:
        await pool.execute("""
            INSERT INTO operational_insights (
                facility_id, asset_id, metric_name, threshold_type, severity, title, description, is_active, detected_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, true, now())
            ON CONFLICT (facility_id, metric_name, threshold_type, COALESCE(asset_id, '00000000-0000-0000-0000-000000000000'::uuid))
                WHERE is_active = true
            DO UPDATE SET
                description = EXCLUDED.description,
                updated_at = now()
        """, facility_id, issue.get('asset_id'), issue['metric_name'], issue['threshold_type'], 
             issue['severity'], issue['title'], issue['description'])
    
    # Resolve insights that are no longer detected
    detected_types = {(i.get('asset_id'), i['metric_name'], i['threshold_type']) for i in detected_issues}
    active_insights = await pool.fetch("""
        SELECT asset_id, metric_name, threshold_type
        FROM operational_insights
        WHERE facility_id = $1 AND is_active = true
    """, facility_id)
    
    for insight in active_insights:
        if (insight['asset_id'], insight['metric_name'], insight['threshold_type']) not in detected_types:
            await pool.execute("""
                UPDATE operational_insights
                SET is_active = false, resolved_at = now()
                WHERE facility_id = $1 
                  AND COALESCE(asset_id, '00000000-0000-0000-0000-000000000000'::uuid) = COALESCE($2, '00000000-0000-0000-0000-000000000000'::uuid)
                  AND metric_name = $3 
                  AND threshold_type = $4 
                  AND is_active = true
            """, facility_id, insight['asset_id'], insight['metric_name'], insight['threshold_type'])


async def fetch_insights(facility_id: UUID) -> list[dict]:
    """
    Fetch active operational insights from database.
    Returns only active (unresolved) insights, ordered by severity and detection time.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT
            oi.severity,
            oi.title,
            oi.description,
            oi.detected_at,
            a.name as asset_name
        FROM operational_insights oi
        LEFT JOIN assets a ON a.id = oi.asset_id
        WHERE oi.facility_id = $1 AND oi.is_active = true
        ORDER BY
            CASE oi.severity
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            oi.detected_at DESC
    """, facility_id)
    
    return [dict(r) for r in rows]


async def fetch_kpis(facility_id: UUID, hours: int = 24) -> list[dict]:
    """
    Calculate facility-wide KPIs for power and production (SUM), plus efficiency.
    Power and production are summed across all operational assets.
    Efficiency = total_production / total_power.
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
              AND sr.metric_name IN ('power_consumption', 'production_output')
            ORDER BY sr.metric_name, sr.timestamp DESC
        ),
        totals AS (
            SELECT
                sr.metric_name,
                ROUND(SUM(sr.value)::numeric, 2) AS total_value,
                ROUND(MIN(sr.value)::numeric, 2) AS min_value,
                ROUND(MAX(sr.value)::numeric, 2) AS max_value,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sr.value)::numeric, 2) AS p50_value,
                ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY sr.value)::numeric, 2) AS p90_value,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY sr.value)::numeric, 2) AS p95_value
            FROM sensor_readings sr
            JOIN assets a ON a.id = sr.asset_id
            WHERE a.facility_id = $1
              AND sr.timestamp >= $2
              AND sr.metric_name IN ('power_consumption', 'production_output')
            GROUP BY sr.metric_name
        )
        SELECT
            t.metric_name,
            t.total_value AS current_value,
            l.unit,
            t.total_value AS avg_value,
            t.min_value,
            t.max_value
        FROM totals t
        JOIN latest l ON l.metric_name = t.metric_name
        ORDER BY t.metric_name
    """, facility_id, since)

    kpis = [dict(r) for r in rows]
    
    # Calculate efficiency if we have both power and production
    power_kpi = next((k for k in kpis if k['metric_name'] == 'power_consumption'), None)
    production_kpi = next((k for k in kpis if k['metric_name'] == 'production_output'), None)
    
    if power_kpi and production_kpi and float(power_kpi['current_value']) > 0:
        efficiency = round((float(production_kpi['current_value']) / float(power_kpi['current_value'])) * 100, 2)
        kpis.append({
            'metric_name': 'efficiency',
            'current_value': efficiency,
            'avg_value': efficiency,
            'min_value': efficiency,
            'max_value': efficiency,
            'p50_value': efficiency,
            'p90_value': efficiency,
            'p95_value': efficiency,
            'unit': '%'
        })
    
    return kpis


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
