from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
from .router import router
import os
from auth.jwtToken import decode_access_token
from database import SessionLocal
from models import User 
from models.ticket_event import TicketEvent
from schemas.ticket_event import TicketEventResponse

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
    
    past_events = db.query(TicketEvent).filter(TicketEvent.ticket_id==ticket_id).order_by(TicketEvent.created_at.asc()).all()
    history = [
        TicketEventResponse.model_validate(event).model_dump(
            mode="json"
        )
        for event in past_events
    ]
    
    await websocket.send_json({
        "type": "history",
        "events": history})
    
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
    


