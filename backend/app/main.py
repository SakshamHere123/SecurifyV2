from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.db import models
from app.api import health, scan, policy, auth

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(scan.router, tags=["scan"])
app.include_router(policy.router, tags=["policy"])
app.include_router(auth.router, tags=["auth"])


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)