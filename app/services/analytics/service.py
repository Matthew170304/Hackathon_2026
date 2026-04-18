from collections import defaultdict
from datetime import date
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.incident_repository import IncidentRepository
from app.schemas.analytics_schemas import (
    HiddenRiskHypothesis,
    ObservedProblem,
    PowerBIIncidentRecord,
    RiskCluster,
    RoadmapAction,
    SiteRiskRoadmap,
    StrategicAction,
    StrategicRecommendation,
)


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.repository = IncidentRepository(session)

    def list_powerbi_incidents(
        self,
        year: int | None = None,
        location: str | None = None,
        min_risk_score: int | None = None,
    ) -> list[PowerBIIncidentRecord]:
        processed = self.repository.list_processed_incidents(
            year=year,
            location=location,
            min_risk_score=min_risk_score,
        )
        records = []
        for item in processed:
            incident = item.incident
            occurred_at = incident.occurred_at if incident else None
            records.append(
                PowerBIIncidentRecord(
                    incident_id=item.incident_id,
                    external_case_id=incident.external_case_id if incident else None,
                    year=occurred_at.year if occurred_at else None,
                    month=occurred_at.month if occurred_at else None,
                    country=incident.country if incident else None,
                    site=incident.site if incident else None,
                    location=incident.location if incident else None,
                    activity=incident.activity if incident else None,
                    hazard_category=item.hazard_category,
                    cause_category=item.cause_category,
                    severity_level=item.severity_level,
                    recurrence_frequency=item.recurrence_frequency,
                    risk_score=item.risk_score,
                    risk_level_label=item.risk_level_label,
                    recommendation_summary=item.recommendation_summary,
                    needs_human_review=item.needs_human_review,
                )
            )
        return records

    def find_high_risk_clusters(
        self,
        year: int,
        min_incident_count: int = 3,
    ) -> list[RiskCluster]:
        grouped: dict[tuple, list] = defaultdict(list)
        for item in self.repository.list_processed_incidents(year=year):
            incident = item.incident
            key = (
                incident.country if incident else None,
                incident.site if incident else None,
                incident.activity if incident else None,
                item.hazard_category,
                item.cause_category,
            )
            grouped[key].append(item)

        clusters = []
        for key, items in grouped.items():
            if len(items) < min_incident_count:
                continue
            scores = [item.risk_score or 0 for item in items]
            clusters.append(
                RiskCluster(
                    country=key[0],
                    site=key[1],
                    activity=key[2],
                    hazard_category=key[3],
                    cause_category=key[4],
                    incident_count=len(items),
                    average_risk_score=round(sum(scores) / len(scores), 2),
                    max_risk_score=max(scores),
                    critical_count=sum(1 for item in items if (item.risk_score or 0) > 100),
                )
            )

        return sorted(
            clusters,
            key=lambda cluster: (
                cluster.critical_count,
                cluster.max_risk_score,
                cluster.average_risk_score,
                cluster.incident_count,
            ),
            reverse=True,
        )

    def generate_site_roadmap(
        self,
        year: int,
        site: str | None = None,
    ) -> SiteRiskRoadmap:
        clusters = self.find_high_risk_clusters(year=year, min_incident_count=1)
        if site is not None:
            clusters = [cluster for cluster in clusters if cluster.site == site]

        actions = []
        for cluster in clusters[:10]:
            timeframe = "7 days" if cluster.max_risk_score > 100 else "30 days" if cluster.max_risk_score > 40 else "90 days"
            actions.append(
                RoadmapAction(
                    timeframe=timeframe,
                    owner_type=self._owner(cluster.hazard_category),
                    action=f"Reduce {cluster.hazard_category} linked to {cluster.cause_category}.",
                    reason=f"{cluster.incident_count} incident(s), max risk {cluster.max_risk_score}, average risk {cluster.average_risk_score}.",
                    expected_impact="Lower recurrence and improve prevention focus for the highest-risk cluster.",
                )
            )

        return SiteRiskRoadmap(year=year, site=site, actions=actions)

    async def generate_strategic_recommendation(
        self,
        date_from: date,
        date_to: date,
        location: str | None = None,
    ) -> StrategicRecommendation:
        records = self._records_for_period(
            date_from=date_from,
            date_to=date_to,
            location=location,
        )
        fallback = self._build_fallback_strategic_recommendation(
            date_from=date_from,
            date_to=date_to,
            location=location,
            records=records,
        )

        ai_result = await self._try_generate_ai_strategic_recommendation(
            date_from=date_from,
            date_to=date_to,
            location=location,
            records=records,
        )
        return ai_result or fallback

    def _records_for_period(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
    ):
        location_filter = location.lower() if location else None
        records = []
        for item in self.repository.list_processed_incidents():
            incident = item.incident
            if incident is None or incident.occurred_at is None:
                continue

            occurred_on = incident.occurred_at.date()
            if occurred_on < date_from or occurred_on > date_to:
                continue

            if location_filter and location_filter not in " ".join(
                value or ""
                for value in (incident.location, incident.country, incident.site)
            ).lower():
                continue

            records.append(item)

        return records

    def _build_fallback_strategic_recommendation(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
        records,
    ) -> StrategicRecommendation:
        hazard_counts = self._count_by(records, "hazard_category")
        cause_counts = self._count_by(records, "cause_category")
        top_hazards = sorted(hazard_counts.items(), key=lambda item: item[1], reverse=True)[:5]

        observed_problems = [
            ObservedProblem(
                problem=f"{hazard} linked to {self._top_related_cause(records, hazard)}",
                evidence=f"{count} observed incident(s) in the selected period.",
                incident_count=count,
                risk_signal=self._risk_signal(records, hazard),
            )
            for hazard, count in top_hazards
        ]

        return StrategicRecommendation(
            period_start=date_from.isoformat(),
            period_end=date_to.isoformat(),
            location_filter=location,
            incident_count=len(records),
            ai_generated=False,
            executive_summary=(
                f"{len(records)} processed incident(s) were analyzed. "
                "The strongest observed patterns should be treated as a reporting signal, "
                "not a complete map of all safety risk."
            ),
            observed_problem_summary=self._format_counts("Observed hazard pattern", hazard_counts),
            observability_bias_note=(
                "People tend to report visible, easy-to-notice hazards more often than weak signals, "
                "rare events, process drift, fatigue, normalization of deviation, and issues in low-reporting teams. "
                "Low counts must not be read as low risk without targeted verification."
            ),
            most_observed_problems=observed_problems,
            hidden_risk_hypotheses=[
                HiddenRiskHypothesis(
                    hypothesis="Low-frequency high-severity hazards may be underrepresented.",
                    why_it_may_be_underreported="They are rare, may happen outside routine observation, or may be normalized until a serious event occurs.",
                    how_to_check="Run focused EHS walks, maintenance inspections, and supervisor interviews for high-energy hazards.",
                ),
                HiddenRiskHypothesis(
                    hypothesis="Sites or teams with few reports may have reporting barriers, not fewer hazards.",
                    why_it_may_be_underreported="Observation-based data depends on employee willingness, time, language, and local reporting habits.",
                    how_to_check="Compare reporting rate per headcount/shift and ask teams what stops them from reporting weak signals.",
                ),
            ],
            recommended_actions=self._strategic_actions(records, hazard_counts, cause_counts),
        )

    async def _try_generate_ai_strategic_recommendation(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
        records,
    ) -> StrategicRecommendation | None:
        settings = get_settings()
        if settings.ai_provider.lower() != "openai" or not settings.openai_api_key:
            return None

        try:
            from openai import AsyncOpenAI
        except ImportError:
            return None

        context = self._build_ai_context(records)
        system_prompt = (
            "You are a senior EHS prevention strategist. Analyze observation-based safety reports. "
            "Do not assume low report count means low risk. Explicitly account for observability bias, "
            "underreporting, low-frequency high-severity hazards, reporting culture, and weak signals. "
            "Return concise JSON only."
        )
        user_prompt = (
            f"Period: {date_from.isoformat()} to {date_to.isoformat()}\n"
            f"Location filter: {location or 'all'}\n"
            f"Processed incidents:\n{context}"
        )

        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.responses.create(
                model=settings.hazard_ai_model,
                temperature=0.1,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "strict": True,
                        "name": "strategic_recommendation",
                        "schema": _STRATEGIC_RECOMMENDATION_SCHEMA,
                    }
                },
            )
            raw_text = getattr(response, "output_text", "")
            data = json.loads(raw_text)
            return StrategicRecommendation(
                period_start=date_from.isoformat(),
                period_end=date_to.isoformat(),
                location_filter=location,
                incident_count=len(records),
                ai_generated=True,
                **data,
            )
        except Exception:
            return None

    @staticmethod
    def _build_ai_context(records) -> str:
        lines = []
        for item in records[:200]:
            incident = item.incident
            lines.append(
                json.dumps(
                    {
                        "date": incident.occurred_at.date().isoformat() if incident and incident.occurred_at else None,
                        "location": incident.location if incident else None,
                        "site": incident.site if incident else None,
                        "activity": incident.activity if incident else None,
                        "title": incident.title if incident else None,
                        "description": incident.description if incident else None,
                        "hazard": item.hazard_category,
                        "cause": item.cause_category,
                        "severity": item.severity_level,
                        "recurrence": item.recurrence_frequency,
                        "risk_score": item.risk_score,
                        "needs_review": item.needs_human_review,
                    },
                    ensure_ascii=False,
                )
            )
        return "\n".join(lines) or "No records matched."

    @staticmethod
    def _count_by(records, attribute: str) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for item in records:
            counts[getattr(item, attribute)] += 1
        return dict(counts)

    @staticmethod
    def _format_counts(label: str, counts: dict[str, int]) -> str:
        if not counts:
            return "No processed incidents matched the selected filters."
        parts = [
            f"{name}: {count}"
            for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        ]
        return f"{label}: " + "; ".join(parts)

    @staticmethod
    def _top_related_cause(records, hazard: str) -> str:
        counts: dict[str, int] = defaultdict(int)
        for item in records:
            if item.hazard_category == hazard:
                counts[item.cause_category] += 1
        if not counts:
            return "Unknown"
        return max(counts, key=counts.get)

    @staticmethod
    def _risk_signal(records, hazard: str) -> str:
        scores = [item.risk_score or 0 for item in records if item.hazard_category == hazard]
        if not scores:
            return "Unknown"
        if max(scores) > 100:
            return "Critical potential present"
        if max(scores) > 40:
            return "High potential present"
        return "Observed pattern with lower scored potential"

    def _strategic_actions(
        self,
        records,
        hazard_counts: dict[str, int],
        cause_counts: dict[str, int],
    ) -> list[StrategicAction]:
        if not records:
            return [
                StrategicAction(
                    priority="Medium",
                    owner_type="EHS",
                    timeframe="30 days",
                    action="Run targeted observation campaigns before concluding the period has low risk.",
                    reason="No processed reports matched the filter, which may indicate low reporting rather than low risk.",
                    expected_impact="Improves visibility of weak signals and reporting barriers.",
                )
            ]

        top_hazard = max(hazard_counts, key=hazard_counts.get)
        top_cause = max(cause_counts, key=cause_counts.get) if cause_counts else "Unknown"
        max_risk = max(item.risk_score or 0 for item in records)
        priority = "Critical" if max_risk > 100 else "High" if max_risk > 40 else "Medium"

        return [
            StrategicAction(
                priority=priority,
                owner_type=self._owner(top_hazard),
                timeframe="7 days" if priority == "Critical" else "30 days",
                action=f"Launch a focused prevention sprint on {top_hazard}, especially where linked to {top_cause}.",
                reason="This is the strongest observed pattern in the selected period.",
                expected_impact="Reduces the most visible recurring exposure and creates fast learning for similar areas.",
            ),
            StrategicAction(
                priority="High",
                owner_type="EHS",
                timeframe="30 days",
                action="Validate underreported high-energy hazards through targeted inspections and supervisor interviews.",
                reason="Observation data overrepresents easy-to-see issues and may miss rare but severe scenarios.",
                expected_impact="Finds hidden risk before it appears in incident counts.",
            ),
            StrategicAction(
                priority="Medium",
                owner_type="Management",
                timeframe="90 days",
                action="Compare report volume by site, shift, and team against headcount and exposure hours.",
                reason="Low reporting areas may reflect reporting friction or culture, not safer work.",
                expected_impact="Improves confidence in the safety intelligence layer and reduces blind spots.",
            ),
        ]

    @staticmethod
    def _owner(hazard_category: str) -> str:
        if "Mechanical" in hazard_category or "Electrical" in hazard_category:
            return "Maintenance"
        if "Physical" in hazard_category or "Ergonomic" in hazard_category:
            return "Facilities"
        if "Vehicle" in hazard_category:
            return "Production"
        return "EHS"


_STRATEGIC_RECOMMENDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "observed_problem_summary": {"type": "string"},
        "observability_bias_note": {"type": "string"},
        "most_observed_problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "problem": {"type": "string"},
                    "evidence": {"type": "string"},
                    "incident_count": {"type": "integer"},
                    "risk_signal": {"type": "string"},
                },
                "required": ["problem", "evidence", "incident_count", "risk_signal"],
                "additionalProperties": False,
            },
        },
        "hidden_risk_hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string"},
                    "why_it_may_be_underreported": {"type": "string"},
                    "how_to_check": {"type": "string"},
                },
                "required": ["hypothesis", "why_it_may_be_underreported", "how_to_check"],
                "additionalProperties": False,
            },
        },
        "recommended_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string"},
                    "owner_type": {"type": "string"},
                    "timeframe": {"type": "string"},
                    "action": {"type": "string"},
                    "reason": {"type": "string"},
                    "expected_impact": {"type": "string"},
                },
                "required": [
                    "priority",
                    "owner_type",
                    "timeframe",
                    "action",
                    "reason",
                    "expected_impact",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "executive_summary",
        "observed_problem_summary",
        "observability_bias_note",
        "most_observed_problems",
        "hidden_risk_hypotheses",
        "recommended_actions",
    ],
    "additionalProperties": False,
}
