import os
from arq.connections import RedisSettings, ArqRedis
from arq import create_pool
from dotenv import load_dotenv
from fastapi import Request

load_dotenv()

def redis_settings()->RedisSettings:
    return RedisSettings.from_dsn(os.environ["REDIS_URL"])

async def get_redis() -> ArqRedis:
    return await create_pool(redis_settings())
    
    
async def get_redis_pool(request: Request)->ArqRedis:
    return request.app.state.redis
