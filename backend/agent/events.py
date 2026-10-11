import os
import json
import redis
import logging
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def publish_ticket_event(ticket_id: int, event: dict):
    # Database history is authoritative; a transient Redis outage must not
    # turn a committed event into a failed worker job.
    try:
        redis_client.publish(f"ticket:{ticket_id}", json.dumps(event))
        redis_client.publish("tickets:updates", json.dumps({"ticket_id": ticket_id}))
    except redis.RedisError:
        logging.getLogger(__name__).warning(
            "Live notification unavailable for ticket %s", ticket_id
        )


def publish_persisted_events(events):
    """Call only after the transaction containing these events commits."""
    for event in events:
        publish_ticket_event(
            event.ticket_id,
            {
                "id": event.id,
                "ticket_id": event.ticket_id,
                "event_type": event.event_type.value,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            },
        )
