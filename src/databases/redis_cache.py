import os
import asyncio
import redis.asyncio as aioredis

from typing import Optional
from sqlalchemy import text
from src.databases.database_session import _NUMBERING_ASYNC_SESSIONMAKER


LOCAL_REDIS_URL = "redis://redis:6379"
redis_client = None

# Function to initialize Redis and set up periodic sync with Postgres ---------------------------------------
def redis_startup():
    global redis_client 

    # Set up periodic sync with Postgres
    redis_url = os.environ.get("REDIS_URL", LOCAL_REDIS_URL)
    redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    asyncio.create_task(sync_redis_to_postgres(redis_client))

# Async function to sync Redis data to Postgres -------------------------------------------------------------
async def sync_redis_to_postgres(redis_client):
    while True:
        await asyncio.sleep(60) # Every minute

        pg_timezone = os.getenv("PG_TIMEZONE", "UTC")

        # Acquire a global lock for the sync operation
        global_lock_key = "lock:epcalls_sync"
        got_global_lock = await redis_client.set(global_lock_key, "1", nx=True, ex=15)
        if got_global_lock:
            try:
                async for key in redis_client.scan_iter(match="epcalls:*"):
                    key_str = key.decode() if isinstance(key, bytes) else key
                    uid = int(key_str.split(":")[1])
                    data = await redis_client.hgetall(key)
                    if not data:
                        continue

                    async with _NUMBERING_ASYNC_SESSIONMAKER() as session:
                        for endpointid, count in data.items():
                            count = int(count)
                            if count > 0:
                                endpointid = int(endpointid)
                                await redis_client.hincrby(key_str, endpointid, -count)
                                await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))
                                await session.execute(text("""
                                    INSERT INTO endpoint_stats (userid, endpointid, count)
                                    VALUES (:userid, :endpointid, :count)
                                """), {"userid": uid, "endpointid": endpointid, "count": count})
                           
                                await session.commit()
   
            finally:
                await redis_client.delete(global_lock_key)

# Async function to get a value from Redis cache ---------------------------------------------------
async def get_cache(key: str) -> Optional[str]:
    return await redis_client.get(key)

# Async function to set a value in Redis cache with expiration -------------------------------------
async def set_cache(key: str, value: str, expire: int = 600):
    await redis_client.set(key, value, ex=expire)
          