"""Pydantic v2 schemas for user and health profile data."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# Server-side disclaimer — 05-API-SPEC §8: har risk-bearing response ke top level pe chahiye,
# sirf frontend pe rely nahi karna (12-INTEGRATION §8). Cancer screening (Phase 5) ke liye
# stricter variant alag constant banega.
DISCLAIMER = (
    "This is an AI-estimated health risk assessment, not a medical diagnosis. "
    "Consult a qualified doctor."
)


class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    age: Optional[int] = Field(None, ge=18, le=120)
    gender: Optional[int] = Field(None, ge=0, le=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class UserInfo(BaseModel):
    id: int
    name: str
    email: str
    role: str
    age: Optional[int] = None
    gender: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserInfo] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class HealthProfileInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=18, le=120)
    gender: int = Field(..., ge=0, le=1)  # 0=Female, 1=Male
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    sleep_hours: float = Field(..., ge=3.0, le=12.0)
    exercise_level: int = Field(..., ge=0, le=4)
    smoking: bool = False
    alcohol: int = Field(0, ge=0, le=7)
    family_history: List[int] = Field(default=[0, 0, 0, 0], min_length=4, max_length=4)
    phq9: List[int] = Field(..., min_length=9, max_length=9)

    # Phase 2-5 inputs (06-DISEASE-MODULES) — optional taake purana frontend/form422 na de.
    # BP → stroke/metabolic_syndrome, waist → IDF metabolic, diet → anemia/colorectal/liver.
    bp_systolic: Optional[float] = Field(None, ge=50, le=250)
    bp_diastolic: Optional[float] = Field(None, ge=30, le=150)
    waist_circumference: Optional[float] = Field(None, ge=40, le=250)
    diet_quality: Optional[str] = Field(None, pattern="^(poor|average|good)$")

    # {screening_key: responses} — GET /screenings/{key}/questions ke hisaab se banaya jata
    # hai (04-DATA-MODEL §2: har key apni screening_responses row banegi).
    screening_responses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("screening_responses")
    @classmethod
    def validate_screening_keys(cls, v):
        # Local import: schema module ML package pe depend na kare cyclic-import safety ke liye
        from ml.models.registry import DISEASE_REGISTRY
        allowed = {c.screening_key for c in DISEASE_REGISTRY.values() if c.screening_key}
        unknown = sorted(set(v.keys()) - allowed)
        if unknown:
            raise ValueError(
                f"Unknown screening key(s): {', '.join(unknown)}. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )
        return v

    @field_validator("phq9")
    @classmethod
    def validate_phq9(cls, v):
        for i, score in enumerate(v):
            if score < 0 or score > 3:
                raise ValueError(f"PHQ-9 question {i+1} must be between 0 and 3")
        return v

    @property
    def bmi(self) -> float:
        return self.weight / (self.height / 100.0) ** 2


class DiseaseRisk(BaseModel):
    risk_percent: float
    category: str


class BiologicalAgeResult(BaseModel):
    chronological_age: int
    biological_age: float
    age_difference: float
    penalties: list
    status: str


class LongevityResult(BaseModel):
    score: float
    components: dict
    category: str
    description: str


class DepressionResult(BaseModel):
    severity: str
    phq9_total: int
    confidence: float
    contributing_factors: list
    disclaimer: str
    recommendations: list
    crisis_resources: Optional[str] = None


class SHAPFeature(BaseModel):
    feature: str
    shap_value: float
    direction: str
    abs_value: float
    plain_language: str


class PredictionResponse(BaseModel):
    id: int
    disease_risks: dict
    biological_age: BiologicalAgeResult
    longevity_score: LongevityResult
    depression: DepressionResult
    shap_explanations: list
    created_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    message: str
    # Session-based (S15): client har chat-open pe naya session_id bhejta hai — ye sirf
    # reference ke liye hai, server ab DB mein chat SAVE NAHI karta (refresh pe chat fresh).
    session_id: Optional[str] = Field(None, max_length=64)
    # Multi-turn context: client apne current page ke pichhle messages bhejta hai (server
    # stateless hai — DB mein kuch store nahi hota). Refresh pe client ka state khali → fresh chat.
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    response: str
    risk_context: Optional[str] = None
    session_id: Optional[str] = None


class SimulationInput(BaseModel):
    years: int = Field(10, ge=1, le=30)
    sleep_hours_delta: float = Field(0, ge=0, le=5)
    exercise_level_delta: int = Field(0, ge=0, le=4)
    smoking_quit: bool = False
    bmi_improvement: float = Field(0, ge=0, le=10)
    diet_improvement: str = Field("none", pattern="^(none|moderate|strict)$")
