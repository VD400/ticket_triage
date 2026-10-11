from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from arq import create_pool

from agent.queue import redis_settings
from auth.router import router as auth_router
from customers.router import router as customers_router
from tickets.router import router as tickets_router
import tickets.websocket_routes
from settings import cors_origins, validate_hosted_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_hosted_settings()
    # startup — one pool, shared for the app's whole life
    app.state.redis = await create_pool(redis_settings())
    yield
    # shutdown — closed exactly once, here
    await app.state.redis.close()


app = FastAPI(title="AI Ticket Triage Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(tickets_router)


@app.get("/health", include_in_schema=False)
async def health():
    """Render readiness: verify both dependencies without exposing connection data."""
    import asyncio
    from fastapi import HTTPException
    from sqlalchemy import text
    from database import engine

    def database_ready():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(app.state.redis.ping(), timeout=5)
        await asyncio.wait_for(asyncio.to_thread(database_ready), timeout=5)
    except Exception:
        raise HTTPException(status_code=503, detail="A required service is unavailable") from None
    return {"status": "ok"}
