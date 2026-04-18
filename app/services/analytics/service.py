from collections import defaultdict
from datetime import date
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import CauseCategory, HazardCategory, RecurrenceFrequency, SeverityLevel
from app.repositories.incident_repository import IncidentRepository
from app.schemas.analytics_schemas import (
    HiddenRiskHypothesis,
    ObservedProblem,
    PowerBIIncidentRecord,
    RiskCluster,
    RoadmapAction,
    SiteRiskRoadmap,
    StrategicAction,
    StrategicDataQuality,
    StrategicPeriod,
    StrategicPriority,
    StrategicRecommendation,
)
from app.services.risk_scoring.service import (
    HIGH_RISK_MAX_SCORE,
    LOW_RISK_MAX_SCORE,
    MEDIUM_RISK_MAX_SCORE,
    RISK_LABEL_CRITICAL,
    RISK_LABEL_HIGH,
    RISK_LABEL_MEDIUM,
)


OBSERVABILITY_BY_HAZARD = {
    HazardCategory.PHYSICAL.value: "high",
    CauseCategory.HOUSEKEEPING.value: "high",
    HazardCategory.VEHICLE_TRAFFIC.value: "medium",
    HazardCategory.MECHANICAL_EQUIPMENT.value: "medium",
    HazardCategory.ELECTRICAL.value: "low",
    HazardCategory.CHEMICAL.value: "medium",
    HazardCategory.FIRE_EXPLOSION.value: "low",
    HazardCategory.PROCESS_SAFETY_OPERATIONAL.value: "low",
    HazardCategory.ERGONOMIC.value: "low",
    HazardCategory.ENVIRONMENTAL.value: "low",
    HazardCategory.UNKNOWN.value: "low",
}

OBSERVABILITY_MULTIPLIER = {
    "high": 0.85,
    "medium": 1.0,
    "low": 1.25,
}

# These scores are intentionally simple. They are not a prediction model.
# They make the ranking auditable for hackathon/demo use.
SEVERITY_WEIGHT = {
    SeverityLevel.VERY_LOW.value: 1,
    SeverityLevel.LOW.value: 5,
    SeverityLevel.MEDIUM.value: 10,
    SeverityLevel.HIGH.value: 25,
    SeverityLevel.VERY_HIGH.value: 75,
    SeverityLevel.UNKNOWN.value: 0,
}

RECURRENCE_WEIGHT = {
    RecurrenceFrequency.LESS_OFTEN.value: 1,
    RecurrenceFrequency.ONE_TO_FIVE_YEARS.value: 2,
    RecurrenceFrequency.SIX_MONTHS_TO_ONE_YEAR.value: 3,
    RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS.value: 4,
    RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS.value: 5,
    RecurrenceFrequency.UNKNOWN.value: 0,
}

ROADMAP_ACTION_LIMIT = 10
STRATEGIC_PRIORITY_LIMIT = 12
AI_STRATEGIC_PRIORITY_LIMIT = 8
EVIDENCE_CASE_ID_LIMIT = 8
OBSERVED_PROBLEM_LIMIT = 5
RECOMMENDED_ACTION_LIMIT = 3

TIMEFRAME_ONE_WEEK = "7 days"
TIMEFRAME_ONE_MONTH = "30 days"
TIMEFRAME_THREE_MONTHS = "90 days"

OPENAI_PROVIDER = "openai"
AI_STRATEGIC_TEMPERATURE = 0.1

HIGH_NEEDS_REVIEW_RATE = 0.25
LOW_SAMPLE_SIZE_COUNT = 10
WEAK_DATA_NEEDS_REVIEW_RATE = 0.35
WEAK_DATA_CONFIDENCE_THRESHOLD = 0.65
UNDERREPORTING_CONFIDENCE_THRESHOLD = 0.6

FREQUENCY_POINTS_PER_INCIDENT = 8
MAX_FREQUENCY_POINTS = 40
AVERAGE_RISK_WEIGHT = 0.35
MAXIMUM_RISK_WEIGHT = 0.25
CRITICAL_CASE_POINTS = 15
RECURRENCE_WEIGHT_MULTIPLIER = 5
CONFIDENCE_BASE_MULTIPLIER = 0.75
CONFIDENCE_WEIGHT_MULTIPLIER = 0.25


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
                    critical_count=sum(
                        1
                        for item in items
                        if (item.risk_score or 0) > HIGH_RISK_MAX_SCORE
                    ),
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
        for cluster in clusters[:ROADMAP_ACTION_LIMIT]:
            if cluster.max_risk_score > HIGH_RISK_MAX_SCORE:
                timeframe = TIMEFRAME_ONE_WEEK
            elif cluster.max_risk_score > MEDIUM_RISK_MAX_SCORE:
                timeframe = TIMEFRAME_ONE_MONTH
            else:
                timeframe = TIMEFRAME_THREE_MONTHS

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
        evidence = self._build_strategic_evidence(
            date_from=date_from,
            date_to=date_to,
            location=location,
            records=records,
        )
        fallback = self._build_fallback_strategic_recommendation(
            date_from=date_from,
            date_to=date_to,
            location=location,
            records=records,
            evidence=evidence,
        )

        ai_result = await self._try_generate_ai_strategic_recommendation(
            date_from=date_from,
            date_to=date_to,
            location=location,
            records=records,
            evidence=evidence,
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

            incident_location_text = " ".join(
                [
                    incident.location or "",
                    incident.country or "",
                    incident.site or "",
                ]
            ).lower()
            if location_filter and location_filter not in incident_location_text:
                continue

            records.append(item)

        return records

    def _build_fallback_strategic_recommendation(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
        records,
        evidence: dict[str, Any],
    ) -> StrategicRecommendation:
        hazard_counts = self._count_by(records, "hazard_category")
        priorities = evidence["strategic_priorities"]

        observed_problems = [
            ObservedProblem(
                problem=priority.problem,
                evidence=(
                    f"{priority.observed_frequency} observed incident(s), "
                    f"max risk {priority.max_risk_score}, evidence cases: "
                    f"{', '.join(priority.evidence_case_ids[:OBSERVED_PROBLEM_LIMIT]) or 'none'}."
                ),
                incident_count=priority.observed_frequency,
                risk_signal=priority.severity_signal,
            )
            for priority in priorities[:OBSERVED_PROBLEM_LIMIT]
        ]

        return StrategicRecommendation(
            period_start=date_from.isoformat(),
            period_end=date_to.isoformat(),
            location_filter=location,
            incident_count=len(records),
            ai_generated=False,
            methodology=evidence["methodology"],
            period=evidence["period"],
            data_quality=evidence["data_quality"],
            strategic_priorities=priorities,
            executive_summary=(
                f"{len(records)} processed incident(s) were analyzed. "
                "Priorities were ranked with observed frequency, severity potential, recurrence, "
                "observability bias, confidence, and evidence traceability."
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
            recommended_actions=[
                action
                for priority in priorities[:RECOMMENDED_ACTION_LIMIT]
                for action in priority.recommended_actions[:1]
            ] or self._no_data_actions(),
        )

    async def _try_generate_ai_strategic_recommendation(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
        records,
        evidence: dict[str, Any],
    ) -> StrategicRecommendation | None:
        settings = get_settings()
        if settings.ai_provider.lower() != OPENAI_PROVIDER or not settings.openai_api_key:
            return None

        try:
            from openai import AsyncOpenAI
        except ImportError:
            return None

        context = json.dumps(self._evidence_for_ai(evidence), ensure_ascii=False, indent=2)
        system_prompt = (
            "You are a senior EHS prevention strategist. Analyze observation-based safety reports. "
            "Do not assume low report count means low risk. Explicitly account for observability bias, "
            "underreporting, low-frequency high-severity hazards, reporting culture, and weak signals. "
            "Use only the structured evidence package. Do not invent counts or evidence case IDs. "
            "Separate observed patterns from hidden-risk hypotheses. "
            "Return concise JSON only."
        )
        user_prompt = (
            f"Period: {date_from.isoformat()} to {date_to.isoformat()}\n"
            f"Location filter: {location or 'all'}\n"
            f"Structured evidence package:\n{context}"
        )

        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.responses.create(
                model=settings.hazard_ai_model,
                temperature=AI_STRATEGIC_TEMPERATURE,
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
                methodology=evidence["methodology"],
                period=evidence["period"],
                data_quality=evidence["data_quality"],
                strategic_priorities=evidence["strategic_priorities"],
                **data,
            )
        except Exception:
            return None

    def _build_strategic_evidence(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
        records,
    ) -> dict[str, Any]:
        period = StrategicPeriod(
            start=date_from.isoformat(),
            end=date_to.isoformat(),
            location_filter=location,
        )
        data_quality = self._data_quality(records)
        priorities = self._strategic_priorities(records)
        return {
            "methodology": (
                "Weighted evidence model: clustered incidents by site/activity/hazard/cause, "
                "then ranked clusters using observed frequency, average and maximum risk, critical count, "
                "recurrence, severity, observability bias, confidence, and traceable evidence case IDs. "
                "Lower observability increases hidden-risk weight because observation-based reports undercount "
                "weak signals and rare high-severity hazards."
            ),
            "period": period,
            "data_quality": data_quality,
            "strategic_priorities": priorities,
        }

    def _data_quality(self, records) -> StrategicDataQuality:
        count = len(records)
        if count == 0:
            return StrategicDataQuality(
                incident_count=0,
                missing_severity_rate=0.0,
                missing_recurrence_rate=0.0,
                unknown_hazard_rate=0.0,
                unknown_cause_rate=0.0,
                needs_review_rate=0.0,
                average_confidence=0.0,
                reporting_bias_assessment="High uncertainty: no matching processed reports.",
                data_limitations=[
                    "No records matched the selected period/location.",
                    "No conclusion about true risk can be drawn from absence of reports.",
                ],
            )

        missing_severity = sum(
            1 for item in records if item.severity_level == SeverityLevel.UNKNOWN.value
        )
        missing_recurrence = sum(
            1 for item in records if item.recurrence_frequency == RecurrenceFrequency.UNKNOWN.value
        )
        unknown_hazard = sum(
            1 for item in records if item.hazard_category == HazardCategory.UNKNOWN.value
        )
        unknown_cause = sum(
            1 for item in records if item.cause_category == CauseCategory.UNKNOWN.value
        )
        needs_review = sum(1 for item in records if item.needs_human_review)
        confidences = [
            confidence
            for item in records
            for confidence in (
                item.hazard_confidence,
                item.cause_confidence,
                item.severity_confidence,
                item.recurrence_confidence,
            )
        ]
        average_confidence = sum(confidences) / len(confidences)
        limitations = [
            "Observation-based data overrepresents visible hazards and underrepresents weak signals.",
            "No exposure denominators are available, so counts are not normalized by headcount, hours, or asset count.",
        ]
        if missing_severity:
            limitations.append("Some severity values are unknown or inferred.")
        if missing_recurrence:
            limitations.append("Some recurrence values are unknown or inferred.")
        if needs_review / count > HIGH_NEEDS_REVIEW_RATE:
            limitations.append("High share of records need human review, reducing certainty.")

        return StrategicDataQuality(
            incident_count=count,
            missing_severity_rate=round(missing_severity / count, 3),
            missing_recurrence_rate=round(missing_recurrence / count, 3),
            unknown_hazard_rate=round(unknown_hazard / count, 3),
            unknown_cause_rate=round(unknown_cause / count, 3),
            needs_review_rate=round(needs_review / count, 3),
            average_confidence=round(average_confidence, 3),
            reporting_bias_assessment=self._reporting_bias_assessment(count, needs_review, average_confidence),
            data_limitations=limitations,
        )

    def _strategic_priorities(self, records) -> list[StrategicPriority]:
        # Group incidents into patterns. A pattern is easier to act on than one row.
        # Example: "Nordborg + Maintenance + Electrical + Workplace Design".
        grouped: dict[tuple, list] = defaultdict(list)
        for item in records:
            incident = item.incident
            key = (
                incident.site if incident else None,
                incident.activity if incident else None,
                item.hazard_category,
                item.cause_category,
            )
            grouped[key].append(item)

        priorities = []
        for key, items in grouped.items():
            site, activity, hazard, cause = key

            # Basic risk evidence from the cluster.
            scores = [item.risk_score or 0 for item in items]
            if scores:
                average_risk = sum(scores) / len(scores)
                max_risk = max(scores)
            else:
                average_risk = 0
                max_risk = 0

            critical_count = sum(1 for score in scores if score > HIGH_RISK_MAX_SCORE)

            # Observation bias: low-observability hazards get a higher weight.
            # Example: exposed wiring is easier to miss than a wet floor.
            observability = OBSERVABILITY_BY_HAZARD.get(hazard, "low")
            confidence = self._cluster_confidence(items)
            priority_score = self._calculate_priority_score(
                item_count=len(items),
                average_risk=average_risk,
                max_risk=max_risk,
                critical_count=critical_count,
                observability=observability,
                confidence=confidence,
                items=items,
            )
            evidence_case_ids = [
                item.incident.external_case_id or item.incident_id
                for item in items
                if item.incident is not None
            ][:EVIDENCE_CASE_ID_LIMIT]
            priorities.append(
                StrategicPriority(
                    rank=0,
                    problem=self._cluster_problem(site, activity, hazard, cause),
                    cluster_key=" | ".join(str(value or HazardCategory.UNKNOWN.value) for value in key),
                    priority_score=round(priority_score, 2),
                    confidence=confidence,
                    observed_frequency=len(items),
                    average_risk_score=round(average_risk, 2),
                    max_risk_score=max_risk,
                    critical_count=critical_count,
                    severity_signal=self._severity_signal(max_risk),
                    recurrence_signal=self._recurrence_signal(items),
                    observability=observability,
                    underreporting_likelihood=self._underreporting_likelihood(observability, hazard, confidence),
                    why_it_matters=self._why_cluster_matters(hazard, cause, observability, max_risk, len(items)),
                    evidence_case_ids=evidence_case_ids,
                    recommended_actions=[
                        self._priority_action(hazard, cause, max_risk, observability)
                    ],
                )
            )

        priorities.sort(key=lambda item: item.priority_score, reverse=True)
        for index, priority in enumerate(priorities, start=1):
            priority.rank = index
        return priorities[:STRATEGIC_PRIORITY_LIMIT]

    @staticmethod
    def _calculate_priority_score(
        item_count: int,
        average_risk: float,
        max_risk: int,
        critical_count: int,
        observability: str,
        confidence: float,
        items,
    ) -> float:
        frequency_points = min(item_count * FREQUENCY_POINTS_PER_INCIDENT, MAX_FREQUENCY_POINTS)
        average_risk_points = average_risk * AVERAGE_RISK_WEIGHT
        maximum_risk_points = max_risk * MAXIMUM_RISK_WEIGHT
        critical_case_points = critical_count * CRITICAL_CASE_POINTS
        severity_points = max(SEVERITY_WEIGHT.get(item.severity_level, 0) for item in items)
        recurrence_points = max(
            RECURRENCE_WEIGHT.get(item.recurrence_frequency, 0)
            for item in items
        ) * RECURRENCE_WEIGHT_MULTIPLIER

        base_score = (
            frequency_points
            + average_risk_points
            + maximum_risk_points
            + critical_case_points
            + severity_points
            + recurrence_points
        )

        hidden_risk_multiplier = OBSERVABILITY_MULTIPLIER[observability]
        confidence_multiplier = CONFIDENCE_BASE_MULTIPLIER + confidence * CONFIDENCE_WEIGHT_MULTIPLIER

        return round(base_score * hidden_risk_multiplier * confidence_multiplier, 2)

    @staticmethod
    def _evidence_for_ai(evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "methodology": evidence["methodology"],
            "period": evidence["period"].model_dump(),
            "data_quality": evidence["data_quality"].model_dump(),
            "strategic_priorities": [
                priority.model_dump()
                for priority in evidence["strategic_priorities"][:AI_STRATEGIC_PRIORITY_LIMIT]
            ],
        }

    @staticmethod
    def _reporting_bias_assessment(
        count: int,
        needs_review: int,
        average_confidence: float,
    ) -> str:
        if count < LOW_SAMPLE_SIZE_COUNT:
            return "High uncertainty: low sample size may hide risk."
        if (
            needs_review / count > WEAK_DATA_NEEDS_REVIEW_RATE
            or average_confidence < WEAK_DATA_CONFIDENCE_THRESHOLD
        ):
            return "Moderate to high uncertainty: review share or confidence suggests weak data quality."
        return "Moderate uncertainty: observation-based data still needs exposure and culture checks."

    @staticmethod
    def _cluster_confidence(items) -> float:
        values = []
        for item in items:
            values.extend(
                [
                    item.hazard_confidence,
                    item.cause_confidence,
                    item.severity_confidence,
                    item.recurrence_confidence,
                ]
            )
        if not values:
            return 0.0
        return round(sum(values) / len(values), 3)

    @staticmethod
    def _cluster_problem(
        site: str | None,
        activity: str | None,
        hazard: str,
        cause: str,
    ) -> str:
        context = []
        if site:
            context.append(site)
        if activity:
            context.append(activity)
        context_text = " / ".join(context) if context else "selected scope"
        return f"{hazard} linked to {cause} in {context_text}"

    @staticmethod
    def _severity_signal(max_risk: int) -> str:
        if max_risk > HIGH_RISK_MAX_SCORE:
            return "Critical potential present"
        if max_risk > MEDIUM_RISK_MAX_SCORE:
            return "High potential present"
        if max_risk > LOW_RISK_MAX_SCORE:
            return "Medium potential present"
        return "Lower scored potential, still monitor for recurrence"

    @staticmethod
    def _recurrence_signal(items) -> str:
        recurrence_values = [item.recurrence_frequency for item in items]
        if RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS.value in recurrence_values:
            return "Frequent recurrence signal"
        if RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS.value in recurrence_values:
            return "Recurring within months"
        if RecurrenceFrequency.UNKNOWN.value in recurrence_values:
            return "Recurrence uncertain"
        return "Lower observed recurrence"

    @staticmethod
    def _underreporting_likelihood(
        observability: str,
        hazard: str,
        confidence: float,
    ) -> str:
        if observability == "low" or confidence < UNDERREPORTING_CONFIDENCE_THRESHOLD:
            return "High"
        if "Mechanical" in hazard or "Vehicle" in hazard or observability == "medium":
            return "Medium"
        return "Low"

    @staticmethod
    def _why_cluster_matters(
        hazard: str,
        cause: str,
        observability: str,
        max_risk: int,
        count: int,
    ) -> str:
        reasons = [
            f"{count} observed report(s)",
            f"maximum risk score {max_risk}",
            f"{observability} observability",
            f"cause pattern: {cause}",
        ]
        if observability == "low":
            reasons.append("low-observability hazards can be undercounted in employee reports")
        if max_risk > HIGH_RISK_MAX_SCORE:
            reasons.append("critical potential requires rapid verification")
        return f"{hazard}: " + "; ".join(reasons) + "."

    def _priority_action(
        self,
        hazard: str,
        cause: str,
        max_risk: int,
        observability: str,
    ) -> StrategicAction:
        if max_risk > HIGH_RISK_MAX_SCORE:
            priority = RISK_LABEL_CRITICAL
            timeframe = TIMEFRAME_ONE_WEEK
        elif max_risk > MEDIUM_RISK_MAX_SCORE:
            priority = RISK_LABEL_HIGH
            timeframe = TIMEFRAME_ONE_MONTH
        else:
            priority = RISK_LABEL_MEDIUM
            timeframe = TIMEFRAME_THREE_MONTHS

        validation = ""
        if observability == "low":
            validation = " Include targeted verification because this is a low-observability hazard."

        return StrategicAction(
            priority=priority,
            owner_type=self._owner(hazard),
            timeframe=timeframe,
            action=f"Run a focused control review for {hazard} linked to {cause}.{validation}",
            reason="Selected by weighted frequency, risk potential, recurrence, observability, and confidence.",
            expected_impact="Reduces the highest-ranked evidence-backed risk cluster and checks for hidden exposure.",
        )

    @staticmethod
    def _no_data_actions() -> list[StrategicAction]:
        return [
            StrategicAction(
                priority=RISK_LABEL_MEDIUM,
                owner_type="EHS",
                timeframe=TIMEFRAME_ONE_MONTH,
                action="Run targeted observation campaigns before concluding the period has low risk.",
                reason="No processed reports matched the filter, which may indicate low reporting rather than low risk.",
                expected_impact="Improves visibility of weak signals and reporting barriers.",
            )
        ]

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
