import asyncpg
from postgrest import AsyncPostgrestClient
from app.config import get_settings

# ---------- Supabase PostgREST client ----------

_postgrest_client: AsyncPostgrestClient | None = None


def get_postgrest() -> AsyncPostgrestClient:
    """Get or create the PostgREST client (uses Supabase REST API with service_role key)."""
    global _postgrest_client
    if _postgrest_client is None:
        settings = get_settings()
        _postgrest_client = AsyncPostgrestClient(
            f"{settings.SUPABASE_URL}/rest/v1",
            headers={
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            },
        )
    return _postgrest_client


# ---------- Direct asyncpg connection pool ----------

_pool: asyncpg.Pool | None = None


def _get_raw_pg_url() -> str:
    """Convert SQLAlchemy-style URL to plain postgres:// for asyncpg."""
    settings = get_settings()
    url = settings.SUPABASE_DB_URL
    # asyncpg needs postgresql:// not postgresql+asyncpg://
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            _get_raw_pg_url(),
            min_size=2,
            max_size=5,  # Stay within Supabase free-tier connection limits
            # Supabase uses PgBouncer in transaction mode, which does not
            # support prepared statements. Disable the statement cache.
            statement_cache_size=0,
        )
    return _pool


async def close_pool() -> None:
    """Close the asyncpg pool (call on app shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
