"""Pydantic v2 schemas for user and health profile data."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


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


class ChatResponse(BaseModel):
    response: str
    risk_context: Optional[str] = None


class SimulationInput(BaseModel):
    years: int = Field(10, ge=1, le=30)
    sleep_hours_delta: float = Field(0, ge=0, le=5)
    exercise_level_delta: int = Field(0, ge=0, le=4)
    smoking_quit: bool = False
    bmi_improvement: float = Field(0, ge=0, le=10)
    diet_improvement: str = Field("none", pattern="^(none|moderate|strict)$")
