from fastapi import FastAPI
from auth.router import router as auth_router
from customers.router import router as customers_router
from tickets.router import router as tickets_router

app = FastAPI(title="AI Ticket Triage Platform")
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(tickets_router)


