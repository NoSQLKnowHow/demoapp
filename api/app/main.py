"""
Prism API - FastAPI application

Companion API for the Data Fundamentals presentation series.
Serves the CityPulse dataset through relational, JSON, graph,
and vector projections from Oracle AI Database 26ai.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_pool, close_pool
from app.routers import relational, json_views, graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    settings.validate()
    init_pool()
    yield
    # Shutdown
    close_pool()


app = FastAPI(
    title="Prism API",
    description=(
        "CityPulse data served through multiple projections: "
        "relational, JSON, graph, and vector. "
        "Companion to the Data Fundamentals presentation series."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow the React frontend (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(relational.router)
app.include_router(json_views.router)
app.include_router(graph.router)
# app.include_router(vector.router)
# app.include_router(ingest.router)
# app.include_router(prism.router)
# app.include_router(meta.router)


@app.get("/health", tags=["system"])
async def health_check():
    """Basic health check endpoint (no auth required)."""
    return {"status": "ok", "mode": settings.mode}
