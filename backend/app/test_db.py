"""
Integration test: inserts a test facility into Supabase via asyncpg,
then runs a SELECT to confirm the connection is working.
Removes the test facility at the end.
"""

import asyncio
import uuid
from app.database import get_pool, close_pool


async def main():
    print("Connecting to Supabase via asyncpg pool...")
    pool = await get_pool()

    test_id = uuid.uuid4()
    test_name = "Test Facility"

    # INSERT
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO facilities (id, name, location, type)
            VALUES ($1, $2, $3, $4)
            """,
            test_id,
            test_name,
            "São Paulo, Brasil",
            "power_station",
        )
        print(f"INSERT OK — id={test_id}")

        # SELECT
        row = await conn.fetchrow(
            "SELECT id, name, location, type, created_at FROM facilities WHERE id = $1",
            test_id,
        )
        print(f"SELECT OK — {dict(row)}")

        # CLEANUP
        await conn.execute("DELETE FROM facilities WHERE id = $1", test_id)
        print(f"DELETE OK — test facility removed")

    await close_pool()
    print("\nAll working! asyncpg <-> Supabase OK.")


if __name__ == "__main__":
    asyncio.run(main())
