"""FastAPI application entry point."""

import asyncio
import logging
import math
import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import close_pool, get_pool
from app.events import broadcaster

logger = logging.getLogger("app.live")

# ── Background task: generates 1 reading per asset every 30s ──

INTERVAL_SECONDS = 30
_bg_task: asyncio.Task | None = None


async def _generate_live_readings():
    """Infinite loop that inserts a random reading per asset/metric."""
    metrics = [
        ("temperature",      "°C",       60, 120),
        ("pressure",         "bar",       1,  10),
        ("power_consumption","kW",      100, 500),
        ("production_output","units/hr",  50, 200),
    ]

    while True:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Fetch all asset IDs
                rows = await conn.fetch("SELECT id FROM assets")
                asset_ids = [r["id"] for r in rows]

                now = datetime.now(timezone.utc)
                records = []

                for aid in asset_ids:
                    t = now.timestamp()
                    seed = hash(str(aid)) % 1000 / 100.0
                    for name, unit, lo, hi in metrics:
                        mid = (lo + hi) / 2
                        amp = (hi - lo) / 3
                        base = mid + amp * math.sin(seed + t / 3600)
                        noise = random.gauss(0, (hi - lo) * 0.04)
                        value = round(max(lo, min(hi, base + noise)), 2)
                        records.append((uuid.uuid4(), aid, name, value, unit, now))

                await conn.copy_records_to_table(
                    "sensor_readings",
                    records=records,
                    columns=["id", "asset_id", "metric_name", "value", "unit", "timestamp"],
                )
                logger.info("Live: inserted %d readings for %d assets", len(records), len(asset_ids))
                print(f"[LIVE] Inserted {len(records)} readings for {len(asset_ids)} assets")
                
                # Get unique facility IDs for these assets
                facility_rows = await conn.fetch(
                    "SELECT DISTINCT facility_id FROM assets WHERE id = ANY($1)",
                    asset_ids
                )
                
                # Manage insights for each facility
                from app.services.dashboard import manage_insights
                for row in facility_rows:
                    facility_id = row["facility_id"]
                    await manage_insights(facility_id)
                    await broadcaster.broadcast_update(facility_id)
                    logger.info("Updated insights and broadcasted for facility %s", facility_id)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Live reading generation failed")

        await asyncio.sleep(INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _bg_task
    # Startup: launch background task
    _bg_task = asyncio.create_task(_generate_live_readings())
    logger.info("Background live-reading task started (every %ds)", INTERVAL_SECONDS)
    yield
    # Shutdown: cancel task and close the pool
    if _bg_task:
        _bg_task.cancel()
        try:
            await _bg_task
        except asyncio.CancelledError:
            pass
    await close_pool()


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── API routers (Phase 2) ──
from app.api.dashboard import router as dashboard_router
from app.api.dashboard import facilities_router

app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(facilities_router, prefix="/api/v1")
