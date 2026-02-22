"""FastAPI application entry point."""

import asyncio
import logging
import math
import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import close_pool, get_pool

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

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Live reading generation failed")

        await asyncio.sleep(INTERVAL_SECONDS)


# ── Background task: self-ping to prevent Render free-tier from sleeping ──

SELF_PING_INTERVAL = 780  # 13 minutes (Render sleeps after 15 min inactivity)
_self_ping_task: asyncio.Task | None = None


async def _self_ping():
    """Ping our own /health endpoint to keep the Render instance awake."""
    # Detect the public URL from the RENDER_EXTERNAL_URL env var that Render sets,
    # or fall back to localhost for local development.
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
    url = f"{base_url}/health"
    logger.info("Self-ping target: %s (every %ds)", url, SELF_PING_INTERVAL)

    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            await asyncio.sleep(SELF_PING_INTERVAL)
            try:
                r = await client.get(url)
                logger.info("Self-ping: %s → %d", url, r.status_code)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Self-ping failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _bg_task, _self_ping_task
    # Startup: launch background tasks
    _bg_task = asyncio.create_task(_generate_live_readings())
    _self_ping_task = asyncio.create_task(_self_ping())
    logger.info("Background live-reading task started (every %ds)", INTERVAL_SECONDS)
    logger.info("Self-ping keep-alive task started (every %ds)", SELF_PING_INTERVAL)
    yield
    # Shutdown: cancel tasks and close the pool
    for task in (_bg_task, _self_ping_task):
        if task:
            task.cancel()
            try:
                await task
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
