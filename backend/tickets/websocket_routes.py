from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
from .router import router, get_ticket_events
import os
from auth.jwtToken import decode_access_token
from database import SessionLocal
from models import User

@router.websocket("/{ticket_id}/stream")
async def ticket_stream(websocket: WebSocket, ticket_id: int):
    token = websocket.query_params.get("token")
    payload = decode_access_token(token) if token else None
    if payload is None:
        await websocket.close(code=1008)
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id==int(payload.get("sub"))).first()
    finally:
        db.close()
    
    if user is None or not user.is_active:
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    redis_client = redis.from_url(
        os.environ["REDIS_URL"],
        decode_responses=True
    )
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"ticket:{ticket_id}")
    
    past_events = get_ticket_events(ticket_id)
    websocket.send_json(past_events)
    
    try:
        async for message in pubsub.listen():
            if message["type"] != 'message':
                continue
            await websocket.send_text(message['data'])
    except WebSocketDisconnect:
        print(f"Client disconnected from ticket {ticket_id}")
    finally:
        await pubsub.unsubscribe(
            f"ticket:{ticket_id}"
        )
        await pubsub.close()
        await redis_client.close()
    


