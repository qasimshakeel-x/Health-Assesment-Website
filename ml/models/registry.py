"""DISEASE_REGISTRY — one config entry per disease (02-ARCHITECTURE.md §5).

Registry pattern: adding a disease = ek config entry + engine + `.pkl`, FastAPI route /
orchestrator loop touch nahi hota. Phase rollout 01-PRD §5.1:
  Phase 1 (ACTIVE)   : diabetes, heart, hypertension, obesity (+ depression, alag engine)
  Phase 2 (ACTIVE)   : stroke (ML), sleep_apnea (STOP-BANG rule), gad7 (rule)
  Phase 3 (ACTIVE)   : ckd (depends_on diabetes+hypertension), liver, metabolic_syndrome (rule)
  Phase 4 (ACTIVE)   : thyroid, pcos (female-only), anemia (ML), burnout (rule)
  Phase 5 (ACTIVE)   : colorectal (age>=40 gate), lung_cancer — stricter disclaimer

Engines:
  engine="disease_risk" → DiseaseRiskEngine (Phase-1 4 ensemble)
  engine="phase2"       → Phase2RiskEngine (8 ML diseases, per-disease stacks)
  engine="screening" (+ scoring="rule") → ScreeningClassifier (rule-based: gad7/sleep_apnea/
                         metabolic_syndrome/burnout — clinical review, 09 §4)
  engine="depression"   → DepressionClassifier (PHQ-9, orchestrator alag handle)

NOTE: anemia/colorectal UCI/Kaggle-ML hain (spec 06 "Model" field) — engine phase2 hai, rule
nahi. screening_key → /screenings/{key}/questions endpoint ka question set (05-API-SPEC §3).
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class DiseaseConfig:
    disease_key: str
    label: str
    category: str          # cardiovascular | metabolic | mental_wellness | lifestyle_linked | cancer_screening
    engine: str            # "disease_risk" | "phase2" | "screening" | "depression"
    depends_on: Tuple[str, ...] = ()
    scoring: str = "ml"    # "ml" (ensemble) | "rule" (STOP-BANG/GAD-7/burnout) 
    screening_key: str = ""   # /screenings/{key}/questions — "" matlab no extra questions
    active: bool = True
    # Inference gates (06-DISEASE-MODULE): training dono jagah theek, serving pe filter.
    # pcos = female-only (gender 0), colorectal = age>=40. Engine `predict` isi se
    # eligible check karta hai + /diseases frontend ko bhi yahi bhejta hai (WS-4).
    min_age: int = 0             # 0 = koi age gate nahi
    requires_gender: Optional[int] = None   # None = dono gender; 0=Female only, 1=Male only


CATEGORIES = [
    "cardiovascular", "metabolic", "mental_wellness",
    "lifestyle_linked", "cancer_screening"
]


# {disease_key: DiseaseConfig} — key `disease_risk_results.disease_key` se match karegi
# (04-DATA-MODEL §2) aur `shap_explanations.disease` isi vocabulary se hoga (12-INTEGRATION §5).
DISEASE_REGISTRY: dict = {
    # ---- Phase 1 — ACTIVE ----
    "diabetes": DiseaseConfig(
        disease_key="diabetes", label="Diabetes",
        category="metabolic", engine="disease_risk", screening_key="diabetes"),
    "heart": DiseaseConfig(
        disease_key="heart", label="Heart Disease",
        category="cardiovascular", engine="disease_risk", screening_key="heart"),
    "hypertension": DiseaseConfig(
        disease_key="hypertension", label="Hypertension",
        category="cardiovascular", engine="disease_risk", screening_key="hypertension"),
    "obesity": DiseaseConfig(
        disease_key="obesity", label="Obesity",
        category="metabolic", engine="disease_risk", screening_key="obesity"),

    # ---- Phase 2 — ACTIVE ----
    "stroke": DiseaseConfig(
        disease_key="stroke", label="Stroke",
        category="cardiovascular", engine="phase2", screening_key="stroke"),
    "gad7": DiseaseConfig(
        disease_key="gad7", label="Anxiety (GAD-7)",
        category="mental_wellness", engine="screening", scoring="rule",
        screening_key="gad7"),
    "sleep_apnea": DiseaseConfig(
        disease_key="sleep_apnea", label="Sleep Apnea",
        category="lifestyle_linked", engine="screening", scoring="rule",
        screening_key="sleep_apnea"),

    # ---- Phase 3 — ACTIVE ----
    "ckd": DiseaseConfig(
        disease_key="ckd", label="Chronic Kidney Disease",
        category="metabolic", engine="phase2", screening_key="ckd",
        depends_on=("diabetes", "hypertension")),
    "liver": DiseaseConfig(
        disease_key="liver", label="Liver Disease",
        category="metabolic", engine="phase2", screening_key="liver"),
    "metabolic_syndrome": DiseaseConfig(
        disease_key="metabolic_syndrome", label="Metabolic Syndrome",
        category="cardiovascular", engine="screening", scoring="rule",
        screening_key="metabolic_syndrome"),

    # ---- Phase 4 — ACTIVE ----
    "thyroid": DiseaseConfig(
        disease_key="thyroid", label="Thyroid Disorder",
        category="metabolic", engine="phase2", screening_key="thyroid"),
    "pcos": DiseaseConfig(
        disease_key="pcos", label="PCOS",
        category="lifestyle_linked", engine="phase2", screening_key="pcos",
        requires_gender=0),  # female-only gate (06 Phase 4)
    "anemia": DiseaseConfig(
        disease_key="anemia", label="Anemia",
        category="lifestyle_linked", engine="phase2", screening_key="anemia"),
    "burnout": DiseaseConfig(
        disease_key="burnout", label="Burnout",
        category="mental_wellness", engine="screening", scoring="rule",
        screening_key="burnout"),

    # ---- Phase 5 — ACTIVE (cancer screening: strict disclaimer required) ----
    "colorectal": DiseaseConfig(
        disease_key="colorectal", label="Colorectal Cancer Risk",
        category="cancer_screening", engine="phase2", min_age=40,
        screening_key="colorectal"),  # age>=40 gate (06 Phase 5)
    "lung_cancer": DiseaseConfig(
        disease_key="lung_cancer", label="Lung Cancer Risk",
        category="cancer_screening", engine="phase2", screening_key="lung_cancer_exposure"),
}


def active_diseases() -> dict:
    """Sirf active registry entries — `/diseases` endpoint isi se feed hoga (05-API-SPEC §3)."""
    return {k: v for k, v in DISEASE_REGISTRY.items() if v.active}


def by_engine(engine: str) -> dict:
    """engine name → active disease configs (orchestrator dispatch helper, 02-ARCHITECTURE §5)."""
    return {k: v for k, v in DISEASE_REGISTRY.items() if v.active and v.engine == engine}


def categories() -> dict:
    """Category → active disease_keys. LongevityScoreEngine category-weighted sirf Phase 2 ke baad
    (01-PRD §6) — 06-DISEASE-MODULES note: weights supervisor se finalize hain; tab isko use karenge."""
    result = {}
    for key, cfg in active_diseases().items():
        result.setdefault(cfg.category, []).append(key)
    return result