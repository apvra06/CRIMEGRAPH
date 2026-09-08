from fastapi import APIRouter
from app.config import NEO4J_URI
from app.database import check_connection
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    connected = check_connection()
    return HealthResponse(
        status="ok",
        neo4j_connected=connected,
        neo4j_uri=NEO4J_URI,
        mode="live" if connected else "mock_resilient"
    )

