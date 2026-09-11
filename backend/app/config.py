import os
from pathlib import Path

# Environment variables
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# CORS
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_MOCK_DIR = PROJECT_ROOT / "data" / "mock"
NLP_SERVICE_DIR = PROJECT_ROOT / "nlp-service"