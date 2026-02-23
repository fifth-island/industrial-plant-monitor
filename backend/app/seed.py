"""
Seed script — populates PostgreSQL with realistic data.

3 facilities, 16 assets, 48h of sensor readings (~368k rows).
Uses asyncpg with COPY protocol for bulk insert performance.

Usage:
    cd backend
    python -m app.seed
"""

import asyncio
import uuid
import math
import random
from datetime import datetime, timedelta, timezone
from app.database import get_pool, close_pool

# ──────────────────────────────────────────────
# Fixed facility and asset definitions
# ──────────────────────────────────────────────

FACILITIES = [
    {
        "id": uuid.uuid4(),
        "name": "Power Station Alpha",
        "location": "Houston, TX",
        "type": "power_station",
        "assets": [
            {"name": "Turbine A", "type": "turbine"},
            {"name": "Turbine B", "type": "turbine"},
            {"name": "Boiler #1", "type": "boiler"},
            {"name": "Generator G1", "type": "generator"},
            {"name": "Cooling Tower CT1", "type": "cooling_tower"},
        ],
    },
    {
        "id": uuid.uuid4(),
        "name": "Chemical Plant Beta",
        "location": "Rotterdam, NL",
        "type": "chemical_plant",
        "assets": [
            {"name": "Reactor R1", "type": "reactor"},
            {"name": "Reactor R2", "type": "reactor"},
            {"name": "Compressor C1", "type": "compressor"},
            {"name": "Distillation Column D1", "type": "distillation_column"},
            {"name": "Heat Exchanger HX1", "type": "heat_exchanger"},
            {"name": "Pump P1", "type": "pump"},
        ],
    },
    {
        "id": uuid.uuid4(),
        "name": "Manufacturing Gamma",
        "location": "São Paulo, BR",
        "type": "manufacturing",
        "assets": [
            {"name": "CNC Machine M1", "type": "cnc_machine"},
            {"name": "CNC Machine M2", "type": "cnc_machine"},
            {"name": "Assembly Robot AR1", "type": "robot"},
            {"name": "Conveyor Belt CB1", "type": "conveyor"},
            {"name": "Furnace F1", "type": "furnace"},
        ],
    },
]

# Metrics and their units
METRICS = [
    ("temperature", "°C"),
    ("pressure", "bar"),
    ("power_consumption", "kW"),
    ("production_output", "units/hr"),
]

# Operational range defaults by asset type
# Each asset type has different acceptable ranges
ASSET_TYPE_RANGES = {
    "turbine": {
        "temperature": (60, 115),
        "pressure": (1, 10),
        "power_consumption": (100, 500),
        "production_output": (50, 200),
    },
    "boiler": {
        "temperature": (65, 125),
        "pressure": (2, 10),
        "power_consumption": (150, 500),
        "production_output": (50, 200),
    },
    "generator": {
        "temperature": (60, 110),
        "pressure": (1, 9),
        "power_consumption": (100, 500),
        "production_output": (60, 200),
    },
    "cooling_tower": {
        "temperature": (50, 100),
        "pressure": (1, 8),
        "power_consumption": (100, 400),
        "production_output": (50, 180),
    },
    "reactor": {
        "temperature": (70, 130),
        "pressure": (2, 10),
        "power_consumption": (150, 500),
        "production_output": (50, 200),
    },
    "compressor": {
        "temperature": (60, 115),
        "pressure": (3, 10),
        "power_consumption": (150, 500),
        "production_output": (50, 200),
    },
    "distillation_column": {
        "temperature": (65, 120),
        "pressure": (1, 9),
        "power_consumption": (120, 480),
        "production_output": (50, 200),
    },
    "heat_exchanger": {
        "temperature": (60, 115),
        "pressure": (1, 9),
        "power_consumption": (100, 450),
        "production_output": (50, 200),
    },
    "pump": {
        "temperature": (55, 105),
        "pressure": (2, 10),
        "power_consumption": (100, 400),
        "production_output": (50, 180),
    },
    "cnc_machine": {
        "temperature": (60, 110),
        "pressure": (1, 8),
        "power_consumption": (120, 480),
        "production_output": (60, 200),
    },
    "robot": {
        "temperature": (55, 105),
        "pressure": (1, 7),
        "power_consumption": (100, 450),
        "production_output": (50, 190),
    },
    "conveyor": {
        "temperature": (50, 100),
        "pressure": (1, 6),
        "power_consumption": (80, 350),
        "production_output": (50, 180),
    },
    "furnace": {
        "temperature": (70, 130),
        "pressure": (1, 9),
        "power_consumption": (200, 500),
        "production_output": (50, 200),
    },
}

# Data generation settings
HOURS_OF_DATA = 48
INTERVAL_SECONDS = 30
BATCH_SIZE = 1000


# ──────────────────────────────────────────────
# Realistic time-series generators
# ──────────────────────────────────────────────

def generate_temperature(t: float, seed: float) -> float:
    """60-120°C with gradual drift + noise."""
    base = 85 + 20 * math.sin(seed + t / 3600)
    noise = random.gauss(0, 2.5)
    return round(max(60, min(120, base + noise)), 2)


def generate_pressure(t: float, seed: float) -> float:
    """1.0-10.0 bar with slow wave."""
    base = 5.5 + 3.0 * math.sin(seed + t / 7200)
    noise = random.gauss(0, 0.3)
    return round(max(1.0, min(10.0, base + noise)), 2)


def generate_power(t: float, seed: float) -> float:
    """100-500 kW with daily load curve."""
    hour_of_day = (t / 3600) % 24
    # Peak during business hours (8h-18h)
    daily_factor = 0.6 + 0.4 * math.exp(-((hour_of_day - 13) ** 2) / 20)
    base = 300 * daily_factor + 50 * math.sin(seed + t / 1800)
    noise = random.gauss(0, 15)
    return round(max(100, min(500, base + noise)), 2)


def generate_production(t: float, seed: float, power: float) -> float:
    """50-200 units/hr correlated with power + noise."""
    # Correlates with power: more power → more production
    ratio = (power - 100) / 400  # 0..1
    base = 50 + 150 * ratio
    noise = random.gauss(0, 8)
    return round(max(50, min(200, base + noise)), 2)


GENERATORS = {
    "temperature": generate_temperature,
    "pressure": generate_pressure,
    "power_consumption": generate_power,
}


# ──────────────────────────────────────────────
# Main seed routine
# ──────────────────────────────────────────────

async def seed():
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Clear existing data (reverse FK order)
        print("Clearing existing data...")
        await conn.execute("DELETE FROM sensor_readings")
        await conn.execute("DELETE FROM operational_insights")
        await conn.execute("DELETE FROM asset_operational_ranges")
        await conn.execute("DELETE FROM assets")
        await conn.execute("DELETE FROM facilities")

        # ── Insert facilities ──
        print("\nInserting facilities...")
        for fac in FACILITIES:
            await conn.execute(
                "INSERT INTO facilities (id, name, location, type) VALUES ($1, $2, $3, $4)",
                fac["id"], fac["name"], fac["location"], fac["type"],
            )
            print(f"  [OK] {fac['name']}")

        # ── Insert assets (initially all operational) ──
        print("\nInserting assets...")
        all_assets = []  # (asset_id, asset_name, asset_type, facility_name)
        for fac in FACILITIES:
            for asset_def in fac["assets"]:
                asset_id = uuid.uuid4()
                # All start as operational - will update based on ranges later
                await conn.execute(
                    "INSERT INTO assets (id, facility_id, name, type, status) VALUES ($1, $2, $3, $4, $5)",
                    asset_id, fac["id"], asset_def["name"], asset_def["type"], "operational",
                )
                all_assets.append((asset_id, asset_def["name"], asset_def["type"], fac["name"]))
                print(f"  [OK] {asset_def['name']} ({fac['name']}) - {asset_def['type']}")

        # ── Insert operational ranges per asset ──
        print("\nInserting operational ranges...")
        for asset_id, asset_name, asset_type, fac_name in all_assets:
            ranges = ASSET_TYPE_RANGES.get(asset_type, ASSET_TYPE_RANGES["turbine"])
            for metric_name, unit in METRICS:
                min_val, max_val = ranges[metric_name]
                await conn.execute(
                    "INSERT INTO asset_operational_ranges (asset_id, metric_name, min_value, max_value, unit) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    asset_id, metric_name, min_val, max_val, unit,
                )
            print(f"  [OK] {asset_name} ({fac_name}) - 4 ranges configured")

        # ── Generate sensor readings ──
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=HOURS_OF_DATA)
        total_points = int(HOURS_OF_DATA * 3600 / INTERVAL_SECONDS)  # 5760

        total_readings = len(all_assets) * len(METRICS) * total_points
        print(f"\nGenerating {total_readings:,} sensor readings ({HOURS_OF_DATA}h, interval {INTERVAL_SECONDS}s)...")
        print(f"  Assets: {len(all_assets)}, Metrics: {len(METRICS)}, Points per series: {total_points}")
        print(f"  Using COPY protocol (fast bulk insert)...\n")

        inserted = 0

        for asset_idx, (asset_id, asset_name, asset_type, fac_name) in enumerate(all_assets):
            seed_val = random.uniform(0, 2 * math.pi)  # Unique seed per asset

            # Generate all records for this asset in memory
            records = []
            for point_idx in range(total_points):
                t = point_idx * INTERVAL_SECONDS
                ts = start_time + timedelta(seconds=t)

                # Generate power first (production depends on it)
                power_val = generate_power(t, seed_val)

                for metric_name, unit in METRICS:
                    if metric_name == "temperature":
                        value = generate_temperature(t, seed_val)
                    elif metric_name == "pressure":
                        value = generate_pressure(t, seed_val)
                    elif metric_name == "power_consumption":
                        value = power_val
                    else:  # production_output
                        value = generate_production(t, seed_val, power_val)

                    records.append((uuid.uuid4(), asset_id, metric_name, value, unit, ts))

            # Bulk insert via COPY protocol — much faster than executemany
            await conn.copy_records_to_table(
                "sensor_readings",
                records=records,
                columns=["id", "asset_id", "metric_name", "value", "unit", "timestamp"],
            )
            inserted += len(records)
            pct = inserted / total_readings * 100
            print(f"  [OK] {asset_name} ({fac_name}) - {len(records):,} readings  [{pct:.0f}%]")

        # ── Evaluate asset status based on latest readings vs ranges ──
        print("\nEvaluating asset status against operational ranges...")
        assets_in_maintenance = []
        
        for asset_id, asset_name, asset_type, fac_name in all_assets:
            # Get latest value for each metric
            latest_values = {}
            for metric_name, unit in METRICS:
                row = await conn.fetchrow(
                    "SELECT value FROM sensor_readings "
                    "WHERE asset_id = $1 AND metric_name = $2 "
                    "ORDER BY timestamp DESC LIMIT 1",
                    asset_id, metric_name
                )
                if row:
                    latest_values[metric_name] = row['value']
            
            # Get operational ranges for this asset
            ranges = {}
            range_rows = await conn.fetch(
                "SELECT metric_name, min_value, max_value FROM asset_operational_ranges WHERE asset_id = $1",
                asset_id
            )
            for r in range_rows:
                ranges[r['metric_name']] = (r['min_value'], r['max_value'])
            
            # Check if any metric is out of range
            is_out_of_range = False
            for metric_name, value in latest_values.items():
                if metric_name in ranges:
                    min_val, max_val = ranges[metric_name]
                    if value < min_val or value > max_val:
                        is_out_of_range = True
                        break
            
            if is_out_of_range:
                assets_in_maintenance.append((asset_id, asset_name, fac_name, latest_values, ranges))
        
        # Enforce ~12% maintenance ratio
        total_assets = len(all_assets)
        target_maintenance = int(total_assets * 0.12)
        current_maintenance = len(assets_in_maintenance)
        
        print(f"  Initial evaluation: {current_maintenance}/{total_assets} assets out of range")
        print(f"  Target maintenance: {target_maintenance} assets (~12%)")
        
        # If too many in maintenance, randomly normalize some
        if current_maintenance > target_maintenance:
            excess = current_maintenance - target_maintenance
            print(f"  Normalizing {excess} assets to stay within acceptable ranges...")
            
            # Randomly select assets to normalize
            to_normalize = random.sample(assets_in_maintenance, excess)
            
            for asset_id, asset_name, fac_name, latest_values, ranges in to_normalize:
                # Adjust out-of-range readings to be within acceptable limits
                for metric_name, value in latest_values.items():
                    if metric_name in ranges:
                        min_val, max_val = ranges[metric_name]
                        if value < min_val or value > max_val:
                            # Normalize to midpoint of range with small variation
                            normalized_value = (min_val + max_val) / 2 + random.uniform(-5, 5)
                            normalized_value = max(min_val, min(max_val, normalized_value))
                            
                            # Update the latest reading
                            await conn.execute(
                                "UPDATE sensor_readings SET value = $1 "
                                "WHERE asset_id = $2 AND metric_name = $3 "
                                "AND timestamp = (SELECT MAX(timestamp) FROM sensor_readings WHERE asset_id = $2 AND metric_name = $3)",
                                normalized_value, asset_id, metric_name
                            )
                print(f"  [NORMALIZED] {asset_name} ({fac_name})")
            
            # Remove normalized assets from maintenance list
            assets_in_maintenance = [a for a in assets_in_maintenance if a not in to_normalize]
        
        # Update asset status based on final evaluation
        operational_count = 0
        maintenance_count = 0
        
        for asset_id, asset_name, asset_type, fac_name in all_assets:
            if any(a[0] == asset_id for a in assets_in_maintenance):
                await conn.execute(
                    "UPDATE assets SET status = 'maintenance', updated_at = now() WHERE id = $1",
                    asset_id
                )
                maintenance_count += 1
                print(f"  [MAINTENANCE] {asset_name} ({fac_name})")
            else:
                # Keep as operational (already set)
                operational_count += 1
        
        print(f"\nFinal status distribution:")
        print(f"  Operational: {operational_count}/{total_assets} ({operational_count/total_assets*100:.1f}%)")
        print(f"  Maintenance: {maintenance_count}/{total_assets} ({maintenance_count/total_assets*100:.1f}%)")

        print(f"\n{'='*50}")
        print(f"Seed complete!")
        print(f"  Facilities:      {len(FACILITIES)}")
        print(f"  Assets:          {len(all_assets)}")
        print(f"  Sensor readings: {inserted:,}")
        print(f"{'='*50}")

    await close_pool()


async def main():
    print("=" * 50)
    print("SEED SCRIPT - Plant Monitor Dashboard")
    print("=" * 50)
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
