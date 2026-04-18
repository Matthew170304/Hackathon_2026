from pydantic import BaseModel

from app.domain.enums import CauseCategory, HazardCategory


class IncidentRecommendation(BaseModel):
    summary: str
    priority: str
    owner_type: str
    timeframe: str


class RecommendationService:
    def choose_priority(self, risk_score: int | None) -> str:
        if risk_score is None:
            return "Review"
        if risk_score > 100:
            return "Critical"
        if risk_score > 40:
            return "High"
        if risk_score > 10:
            return "Medium"
        return "Low"

    def generate_incident_recommendation(
        self,
        hazard_category: HazardCategory,
        cause_category: CauseCategory,
        risk_score: int | None,
    ) -> IncidentRecommendation:
        priority = self.choose_priority(risk_score)
        timeframe = self._timeframe(priority)
        owner = self._owner_type(hazard_category, cause_category)
        action = self._action(hazard_category, cause_category)

        return IncidentRecommendation(
            summary=f"{action} Owner: {owner}. Timeframe: {timeframe}.",
            priority=priority,
            owner_type=owner,
            timeframe=timeframe,
        )

    @staticmethod
    def _timeframe(priority: str) -> str:
        if priority == "Critical":
            return "Immediate"
        if priority == "High":
            return "7 days"
        if priority == "Medium":
            return "30 days"
        return "90 days"

    @staticmethod
    def _owner_type(
        hazard_category: HazardCategory,
        cause_category: CauseCategory,
    ) -> str:
        if hazard_category in {
            HazardCategory.MECHANICAL_EQUIPMENT,
            HazardCategory.ELECTRICAL,
        }:
            return "Maintenance"
        if hazard_category in {HazardCategory.PHYSICAL, HazardCategory.ERGONOMIC}:
            return "Facilities"
        if cause_category in {CauseCategory.PROCEDURES, CauseCategory.COMPETENCES}:
            return "Production"
        if cause_category == CauseCategory.ORGANIZATION:
            return "Management"
        return "EHS"

    @staticmethod
    def _action(
        hazard_category: HazardCategory,
        cause_category: CauseCategory,
    ) -> str:
        hazard_actions = {
            HazardCategory.PHYSICAL: "Remove slip/trip exposure, improve signage, and verify housekeeping controls.",
            HazardCategory.MECHANICAL_EQUIPMENT: "Inspect guarding, isolate unsafe equipment, and confirm lockout controls.",
            HazardCategory.ELECTRICAL: "Isolate electrical exposure and complete a qualified inspection.",
            HazardCategory.CHEMICAL: "Contain exposure, verify storage/labeling, and review spill controls.",
            HazardCategory.FIRE_EXPLOSION: "Remove ignition exposure and verify emergency/fire controls.",
            HazardCategory.ERGONOMIC: "Review work method, posture, load, and task rotation controls.",
            HazardCategory.VEHICLE_TRAFFIC: "Separate pedestrians from mobile equipment and review traffic rules.",
            HazardCategory.PROCESS_SAFETY_OPERATIONAL: "Review operating limits, alarms, and critical process controls.",
            HazardCategory.ENVIRONMENTAL: "Contain environmental exposure and verify waste/emission controls.",
            HazardCategory.UNKNOWN: "Assign an EHS review to clarify hazard and required controls.",
        }
        cause_actions = {
            CauseCategory.PROCEDURES: "Update the work instruction and confirm the procedure is followed.",
            CauseCategory.COMPETENCES: "Refresh training and verify operator competence.",
            CauseCategory.HOUSEKEEPING: "Add housekeeping checks and clear the affected area.",
            CauseCategory.PPE: "Confirm PPE requirements and availability.",
        }

        return cause_actions.get(cause_category, hazard_actions[hazard_category])
