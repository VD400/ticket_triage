from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from arq import create_pool

from agent.queue import redis_settings
from auth.router import router as auth_router
from customers.router import router as customers_router
from tickets.router import router as tickets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — one pool, shared for the app's whole life
    app.state.redis = await create_pool(redis_settings())
    yield
    # shutdown — closed exactly once, here
    await app.state.redis.close()


app = FastAPI(title="AI Ticket Triage Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(tickets_router)