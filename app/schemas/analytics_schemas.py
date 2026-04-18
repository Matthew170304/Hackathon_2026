from pydantic import BaseModel


class PowerBIIncidentRecord(BaseModel):
    incident_id: str
    external_case_id: str | None
    year: int | None
    month: int | None
    country: str | None
    site: str | None
    location: str | None
    activity: str | None
    hazard_category: str
    cause_category: str
    severity_level: str
    recurrence_frequency: str
    risk_score: int | None
    risk_level_label: str
    recommendation_summary: str
    needs_human_review: bool


class RiskCluster(BaseModel):
    country: str | None
    site: str | None
    activity: str | None
    hazard_category: str
    cause_category: str
    incident_count: int
    average_risk_score: float
    max_risk_score: int
    critical_count: int


class RoadmapAction(BaseModel):
    timeframe: str
    owner_type: str
    action: str
    reason: str
    expected_impact: str


class SiteRiskRoadmap(BaseModel):
    year: int
    site: str | None
    actions: list[RoadmapAction]


class ObservedProblem(BaseModel):
    problem: str
    evidence: str
    incident_count: int
    risk_signal: str


class HiddenRiskHypothesis(BaseModel):
    hypothesis: str
    why_it_may_be_underreported: str
    how_to_check: str


class StrategicAction(BaseModel):
    priority: str
    owner_type: str
    timeframe: str
    action: str
    reason: str
    expected_impact: str


class StrategicPeriod(BaseModel):
    start: str
    end: str
    location_filter: str | None


class StrategicDataQuality(BaseModel):
    incident_count: int
    missing_severity_rate: float
    missing_recurrence_rate: float
    unknown_hazard_rate: float
    unknown_cause_rate: float
    needs_review_rate: float
    average_confidence: float
    reporting_bias_assessment: str
    data_limitations: list[str]


class StrategicPriority(BaseModel):
    rank: int
    problem: str
    cluster_key: str
    priority_score: float
    confidence: float
    observed_frequency: int
    average_risk_score: float
    max_risk_score: int
    critical_count: int
    severity_signal: str
    recurrence_signal: str
    observability: str
    underreporting_likelihood: str
    why_it_matters: str
    evidence_case_ids: list[str]
    recommended_actions: list[StrategicAction]


class StrategicRecommendation(BaseModel):
    period_start: str
    period_end: str
    location_filter: str | None
    incident_count: int
    ai_generated: bool
    methodology: str
    period: StrategicPeriod
    data_quality: StrategicDataQuality
    strategic_priorities: list[StrategicPriority]
    executive_summary: str
    observed_problem_summary: str
    observability_bias_note: str
    most_observed_problems: list[ObservedProblem]
    hidden_risk_hypotheses: list[HiddenRiskHypothesis]
    recommended_actions: list[StrategicAction]
