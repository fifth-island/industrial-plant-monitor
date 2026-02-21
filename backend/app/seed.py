"""
Seed script — populates Supabase with realistic data.

3 facilities, ~15 assets, 48h of sensor readings (~345k rows).
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

        # ── Insert assets ──
        print("\nInserting assets...")
        all_assets = []  # (asset_id, asset_name, facility_name)
        for fac in FACILITIES:
            for asset_def in fac["assets"]:
                asset_id = uuid.uuid4()
                # Random: ~1 in 8 assets in maintenance
                status = "maintenance" if random.random() < 0.12 else "operational"
                await conn.execute(
                    "INSERT INTO assets (id, facility_id, name, type, status) VALUES ($1, $2, $3, $4, $5)",
                    asset_id, fac["id"], asset_def["name"], asset_def["type"], status,
                )
                all_assets.append((asset_id, asset_def["name"], fac["name"]))
                print(f"  [OK] {asset_def['name']} ({fac['name']}) - {status}")

        # ── Generate sensor readings ──
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=HOURS_OF_DATA)
        total_points = int(HOURS_OF_DATA * 3600 / INTERVAL_SECONDS)  # 5760

        total_readings = len(all_assets) * len(METRICS) * total_points
        print(f"\nGenerating {total_readings:,} sensor readings ({HOURS_OF_DATA}h, interval {INTERVAL_SECONDS}s)...")
        print(f"  Assets: {len(all_assets)}, Metrics: {len(METRICS)}, Points per series: {total_points}")
        print(f"  Using COPY protocol (fast bulk insert)...\n")

        inserted = 0

        for asset_idx, (asset_id, asset_name, fac_name) in enumerate(all_assets):
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
