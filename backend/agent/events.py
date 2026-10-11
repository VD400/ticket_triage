import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.from_url(
    os.environ["REDIS_URL"],
    decode_responses=True
)

def publish_ticket_event(ticket_id: int, event: dict):
    redis_client.publish(
        f"ticket:{ticket_id}",
        json.dumps(event)
    )
    



