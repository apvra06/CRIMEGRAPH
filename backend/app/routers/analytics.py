from typing import List
from fastapi import APIRouter

from app.schemas import CaseOverviewStats, LeadershipItem, IntermediaryItem, AnomalyItem
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/case-stats", response_model=CaseOverviewStats)
def get_stats():
    return analytics_service.get_case_overview()


@router.get("/leadership", response_model=List[LeadershipItem])
def get_leadership():
    return analytics_service.get_cell_leadership()


@router.get("/intermediaries", response_model=List[IntermediaryItem])
def get_intermediaries():
    return analytics_service.get_known_intermediaries()


@router.get("/anomalies", response_model=List[AnomalyItem])
def get_anomalies():
    return analytics_service.get_active_anomalies()

