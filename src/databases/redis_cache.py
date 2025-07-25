import os
import asyncio

from fastapi import Request, Response
from fastapi_redis_cache import FastApiRedisCache
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis.asyncio as aioredis
from src.databases.database_session import _ASYNC_SESSIONMAKER

LOCAL_REDIS_URL = "redis://127.0.0.1:6379"
redis_client = None

def redis_startup():
    global redis_client 
    redis_cache = FastApiRedisCache()
    redis_cache.init(
        host_url=os.environ.get("REDIS_URL", LOCAL_REDIS_URL),
        prefix="routeapi-cache",
        response_header="X-RouteAPI-Cache",
        ignore_arg_types=[Request, Response, Session]
    )
   
  #  redis_client = redis_cache.redis
    redis_url = os.environ.get("REDIS_URL", LOCAL_REDIS_URL)
    redis_client = aioredis.from_url(redis_url)
    asyncio.create_task(sync_redis_to_postgres(redis_client))

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

                    async with _ASYNC_SESSIONMAKER() as session:
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