from enum import Enum

class HazardCategory(str, Enum):
    PHYSICAL = "Physical Hazards"
    MECHANICAL_EQUIPMENT = "Mechanical / Equipment Hazards"
    ELECTRICAL = "Electrical Hazards"
    CHEMICAL = "Chemical Hazards"
    FIRE_EXPLOSION = "Fire & Explosion Hazards"
    ERGONOMIC = "Ergonomic Hazards"
    VEHICLE_TRAFFIC = "Vehicle & Traffic Hazards"
    PROCESS_SAFETY_OPERATIONAL = "Process Safety / Operational Hazards"
    ENVIRONMENTAL = "Environmental Hazards"
    UNKNOWN = "Unknown"

class CauseCategory(str, Enum):
    WORKPLACE_DESIGN = "Workplace Design"
    HUMAN_FACTORS = "Human Factors"
    ORGANIZATION = "Organization"
    HOUSEKEEPING = "Housekeeping"
    PROCEDURES = "Procedures"
    MAINTENANCE_MANAGEMENT = "Maintenance Management"
    COMPETENCES = "Competences"
    PPE = "Personal Protective Equipment"
    COMMUNICATION = "Communication"
    PEDESTRIAN = "Pedestrian"
    FACILITIES_EQUIPMENT = "Facilities and equipment"
    UNKNOWN = "Unknown"

class SeverityLevel(str, Enum):
    VERY_LOW = "Very low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very high"
    UNKNOWN = "Unknown"

class RecurrenceFrequency(str, Enum):
    LESS_OFTEN = "Less often"
    ONE_TO_FIVE_YEARS = "1 year - 5 years"
    SIX_MONTHS_TO_ONE_YEAR = "6 months - 1 year"
    FOURTEEN_DAYS_TO_SIX_MONTHS = "14 days - 6 months"
    ZERO_TO_FOURTEEN_DAYS = "0 - 14 days"
    UNKNOWN = "Unknown"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"