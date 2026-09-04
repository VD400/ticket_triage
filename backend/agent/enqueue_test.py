import asyncio
from agent.queue import get_redis

async def main():
    redis = await get_redis()
    job = await redis.enqueue_job(
        "process_ticket",
        5
    )
    print("Job queued!")
    print("Job ID:", job.job_id)
    await redis.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
    