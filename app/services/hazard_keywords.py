from app.domain.enums import HazardCategory

HAZARD_KEYWORDS: dict[HazardCategory, list[str]] = {
    HazardCategory.PHYSICAL: [
        "slip", "trip", "fall", "wet floor", "working at height",
        "falling object", "noise", "vibration",
    ],
    HazardCategory.MECHANICAL_EQUIPMENT: [
        "machine", "guard", "guarding", "moving part", "pinch",
        "crush", "equipment", "lockout", "tagout", "finger", "hand injury",
    ],
    HazardCategory.ELECTRICAL: [
        "electric", "shock", "wire", "cable", "voltage",
        "arc flash", "short circuit", "faulty equipment",
    ],
    HazardCategory.CHEMICAL: [
        "chemical", "spill", "leak", "fumes",
        "gas", "hazardous substance", "toxic",
    ],
    HazardCategory.FIRE_EXPLOSION: [
        "fire", "explosion", "flammable",
        "ignite", "combustion",
    ],
    HazardCategory.ERGONOMIC: [
        "lifting", "strain", "posture",
        "repetitive", "ergonomic",
    ],
    HazardCategory.VEHICLE_TRAFFIC: [
        "forklift", "vehicle", "traffic",
        "collision", "pedestrian", "reversing",
    ],
    HazardCategory.PROCESS_SAFETY_OPERATIONAL: [
        "process", "pressure", "valve",
        "overload", "system failure",
    ],
    HazardCategory.ENVIRONMENTAL: [
        "environment", "pollution", "waste",
        "emission", "contamination",
    ],
}