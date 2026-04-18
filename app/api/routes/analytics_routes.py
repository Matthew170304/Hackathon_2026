from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.analytics_schemas import (
    PowerBIIncidentRecord,
    RiskCluster,
    SiteRiskRoadmap,
    StrategicRecommendation,
)
from app.services.analytics import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/powerbi/incidents", response_model=list[PowerBIIncidentRecord])
async def powerbi_incidents(
    year: int | None = None,
    location: str | None = None,
    min_risk_score: int | None = None,
    session: Session = Depends(get_db_session),
) -> list[PowerBIIncidentRecord]:
    return AnalyticsService(session).list_powerbi_incidents(
        year=year,
        location=location,
        min_risk_score=min_risk_score,
    )


@router.get("/risk-clusters", response_model=list[RiskCluster])
async def risk_clusters(
    year: int = Query(2025),
    min_incident_count: int = Query(3, ge=1),
    session: Session = Depends(get_db_session),
) -> list[RiskCluster]:
    return AnalyticsService(session).find_high_risk_clusters(
        year=year,
        min_incident_count=min_incident_count,
    )


@router.get("/roadmap", response_model=SiteRiskRoadmap)
async def roadmap(
    year: int = Query(2025),
    site: str | None = None,
    session: Session = Depends(get_db_session),
) -> SiteRiskRoadmap:
    return AnalyticsService(session).generate_site_roadmap(year=year, site=site)


@router.get("/strategic-recommendation", response_model=StrategicRecommendation)
async def strategic_recommendation(
    date_from: date,
    date_to: date,
    location: str | None = None,
    session: Session = Depends(get_db_session),
) -> StrategicRecommendation:
    return await AnalyticsService(session).generate_strategic_recommendation(
        date_from=date_from,
        date_to=date_to,
        location=location,
    )
