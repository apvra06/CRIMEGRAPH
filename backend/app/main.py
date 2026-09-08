import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import close_driver
from app.routers import graph, analytics, ai, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("crime_analyst.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Crime Analyst REST API Service...")
    yield
    logger.info("Shutting down Crime Analyst REST API Service...")
    close_driver()


app = FastAPI(
    title="Crime Network Analyst API",
    description="REST API backend for AI-powered criminal network analysis (Case NCRB-2026-0847)",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "Crime Network Analyst API",
        "case_id": "NCRB-2026-0847",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }

