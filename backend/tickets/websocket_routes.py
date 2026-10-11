"""Authenticated notifications with persisted history and clean disconnects."""

import asyncio
import os

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from .router import router
from auth.jwtToken import decode_access_token
from database import SessionLocal
from models import User, Ticket
from models.ticket_event import TicketEvent
from schemas.ticket_event import TicketEventResponse


def authorized(websocket):
    token = websocket.query_params.get("token")
    payload = decode_access_token(token) if token else None
    if payload is None:
        return False
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return False
    with SessionLocal() as db:
        user = db.get(User, user_id)
        return user is not None and user.is_active


async def stream(websocket, channel, ticket_id=None):
    if not await asyncio.to_thread(authorized, websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    redis_client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    pubsub = redis_client.pubsub()
    receive_task = None
    publish_task = None
    try:
        # Subscribe before taking the snapshot; frontend deduplicates any overlap.
        await pubsub.subscribe(channel)
        if ticket_id is not None:

            def history():
                with SessionLocal() as db:
                    if db.get(Ticket, ticket_id) is None:
                        return None
                    events = (
                        db.query(TicketEvent)
                        .filter(TicketEvent.ticket_id == ticket_id)
                        .order_by(TicketEvent.created_at.asc(), TicketEvent.id.asc())
                        .all()
                    )
                    return [
                        TicketEventResponse.model_validate(event).model_dump(
                            mode="json"
                        )
                        for event in events
                    ]

            events = await asyncio.to_thread(history)
            if events is None:
                await websocket.close(code=1008)
                return
            await websocket.send_json({"type": "history", "events": events})
        else:
            await websocket.send_json({"type": "ready"})

        async def forward():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])

        async def receive():
            while True:
                await websocket.receive_text()

        publish_task = asyncio.create_task(forward())
        receive_task = asyncio.create_task(receive())
        done, _ = await asyncio.wait(
            [publish_task, receive_task], return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    finally:
        tasks = [task for task in (publish_task, receive_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await pubsub.aclose()
        await redis_client.aclose()


@router.websocket("/updates/stream")
async def dashboard_stream(websocket: WebSocket):
    # Only ticket IDs are broadcast here; records are read through the role-filtered API.
    await stream(websocket, "tickets:updates")


@router.websocket("/{ticket_id}/stream")
async def ticket_stream(websocket: WebSocket, ticket_id: int):
    await stream(websocket, f"ticket:{ticket_id}", ticket_id)
