"""Unit tests — ML engines (07-DEV-WORKFLOW §4, module classes)."""
import pytest

from ml.models.bio_age import BioAgeEngine
from ml.models.longevity_score import LongevityScoreEngine
from ml.models.future_simulator import FutureSimulator
from ml.models.screening_classifier import ScreeningClassifier
from ml.models.registry import active_diseases, by_engine, categories
from backend.tests.conftest import sample_profile


# ── Bio Age ──────────────────────────────────────────────────────────────────
def test_bio_age_ideal_profile_is_optimal():
    out = BioAgeEngine().calculate(
        age=40, bmi=22, sleep_hours=8, exercise_level=4,
        smoking=False, alcohol=0, family_history=[0, 0, 0, 0], avg_disease_risk=0)
    assert out["biological_age"] == 40.0
    assert out["age_difference"] == 0.0
    assert out["status"] == "optimal"


def test_bio_age_unhealthy_profile_ages_user():
    out = BioAgeEngine().calculate(
        age=40, bmi=35, sleep_hours=4, exercise_level=0,
        smoking=True, alcohol=7, family_history=[1, 1, 1, 1], avg_disease_risk=70)
    assert out["biological_age"] > 40
    assert out["status"] == "older"
    assert out["age_difference"] > 0
    assert any(p["factor"] == "Smoking" for p in out["penalties"])


# ── Longevity Score ──────────────────────────────────────────────────────────
def test_longevity_score_bounds_and_ordering():
    eng = LongevityScoreEngine()
    good = eng.calculate(bmi=22, sleep_hours=8, exercise_level=4,
                         avg_disease_risk=0, depression_score=0)
    bad = eng.calculate(bmi=38, sleep_hours=4, exercise_level=0,
                        avg_disease_risk=80, depression_score=25)
    assert 0 <= bad["score"] < good["score"] <= 100
    assert good["category"] == "Excellent"
    assert set(good["components"]) == {"bmi", "sleep", "exercise", "disease_risk", "depression"}


# ── Screening classifiers (rule-based) ───────────────────────────────────────
def test_screening_gad7_thresholds():
    sc = ScreeningClassifier()
    assert sc.score_gad7({}, {}) is None
    minimal = sc.score_gad7({}, {"answers": [0] * 7})
    assert minimal["detail"] == "Minimal"
    severe = sc.score_gad7({}, {"answers": [3] * 7})
    assert severe["detail"] == "Severe"
    assert severe["risk_percent"] == 100.0


def test_screening_sleep_apnea_stopbang():
    sc = ScreeningClassifier()
    assert sc.score_sleep_apnea({}, {}) is None
    profile = {"bp_systolic": 140, "bp_diastolic": 90, "bmi": 40, "age": 60, "gender": 1}
    out = sc.score_sleep_apnea(profile, {"snoring": "yes", "wake_tired": "yes",
                                         "witnessed_apnea": "yes", "daytime_sleepy": "yes"})
    assert out["risk_percent"] == 100.0
    assert "STOP-BANG 8/8" in out["detail_label"]


def test_screening_metabolic_syndrome_requires_waist():
    sc = ScreeningClassifier()
    assert sc.score_metabolic_syndrome({}, {}) is None
    out = sc.score_metabolic_syndrome(
        {"waist_circumference": 95, "gender": 1, "bp_systolic": 140,
         "diabetes_risk": 60, "diet_quality": "poor", "exercise_level": 0}, {})
    assert out["detail"] == "Meets IDF criteria"


def test_screening_burnout():
    sc = ScreeningClassifier()
    assert sc.score_burnout({}, {}) is None
    out = sc.score_burnout({}, {"work_hours": 55, "job_satisfaction": 1,
                                "exhaustion": [3, 3, 3]})
    assert out["risk_percent"] == 100.0
    assert out["detail"] == "Burnout Detected"


# ── Registry ─────────────────────────────────────────────────────────────────
def test_registry_has_16_active_diseases():
    active = active_diseases()
    assert len(active) == 16
    assert set(by_engine("disease_risk")) == {"diabetes", "heart", "hypertension", "obesity"}
    assert len(by_engine("phase2")) == 8
    assert set(by_engine("screening")) == {"gad7", "sleep_apnea", "metabolic_syndrome", "burnout"}
    assert "cancer_screening" in categories()


# ── Future simulator ─────────────────────────────────────────────────────────
def test_future_simulator_improved_beats_current():
    sim = FutureSimulator()
    profile = {
        "age": 40, "bmi": 30, "biological_age": 45,
        "disease_risks": [{"disease_key": "diabetes", "risk_percent": 60}],
        "sleep_hours": 5, "exercise_level": 1, "longevity_score": 50,
    }
    res = sim.simulate(profile, years=10, lifestyle_changes={
        "smoking_quit": True, "exercise_level": 2,
        "sleep_hours": 1, "bmi_improvement": 2, "diet_improvement": "strict"})
    assert res["improved"]["biological_age"] < res["current"]["biological_age"]
    assert res["improved"]["diseases"][0]["risk_percent"] <= \
        res["current"]["diseases"][0]["risk_percent"]


# ── Integrated pipeline (models loaded) ──────────────────────────────────────
def test_pipeline_components(pipeline):
    out = pipeline.run_pipeline(sample_profile())
    assert out["disease_risks"]
    assert all(0 <= d["risk_percent"] <= 100 for d in out["disease_risks"].values())
    assert 0 <= out["longevity_score"]["score"] <= 100
    assert out["biological_age"]["biological_age"] > 0


def test_pipeline_phase2_gates(pipeline):
    eng = pipeline.phase2_engine
    assert eng._eligible("pcos", {"gender": 0, "age": 45}) is True
    assert eng._eligible("pcos", {"gender": 1, "age": 45}) is False
    assert eng._eligible("colorectal", {"gender": 0, "age": 45}) is True
    assert eng._eligible("colorectal", {"gender": 0, "age": 30}) is False


def test_pipeline_depression_severe(pipeline):
    out = pipeline.depression_classifier.predict_depression([3] * 9)
    assert out["phq9_total"] == 27
    assert out["severity"] == "Severe"
    assert "crisis_resources" in out
    assert out["disclaimer"]


def test_pipeline_shap_values_normalized(pipeline):
    out = pipeline.run_pipeline(sample_profile())
    shap = out["shap_explanations"]
    assert isinstance(shap, dict) and len(shap) >= 8
    assert "diabetes" in shap
    for rows in shap.values():
        assert 1 <= len(rows) <= 5
        assert all(-1.0 <= r["shap_value"] <= 1.0 for r in rows)
        assert all(r["impact"] in ("increases risk", "decreases risk") for r in rows)


# ── Artifact band/see_doctor (ML_TRAINING.md §7/§9) ──────────────────────────
def test_artifact_threshold_and_band_are_cwd_independent():
    """`ml/predict` ke path helpers cwd se independent hone chahiye.

    Regression (2026-10-15): `_metrics_path` repo-root pe `reports/` dhoondta tha
    (`dirname(dirname(__file__))`) jo exist nahi karta → `threshold()` hamesha None →
    reload path (`/latest`, `/history`) pe band/see_doctor/disclaimer gayab ho jaate the.
    """
    from ml.predict import band_for, has_artifact, threshold

    assert has_artifact("diabetes")
    t = threshold("diabetes")
    assert t is not None and 0 < t < 1
    assert band_for("diabetes", t) == "high"
    assert band_for("diabetes", t * 0.1) == "low"
    assert band_for("does_not_exist", 0.5) is None  # unknown → None, crash nahi


def test_risk_rows_carry_band_only_for_ml_diseases():
    """`risk_rows_from_results` — ML diseases pe band/see_doctor/disclaimer, rule-based pe None."""
    from backend.app.routes.predict import risk_rows_from_results

    rows = risk_rows_from_results({"disease_risks": {
        "diabetes": {"risk_percent": 60.0, "label": "Diabetes", "category": "metabolic",
                     "risk_label": "High Risk", "confidence": None},
        "gad7": {"risk_percent": 50.0, "label": "GAD-7", "category": "mental_wellness",
                 "risk_label": "Moderate", "confidence": None},
    }})
    by = {r["disease_key"]: r for r in rows}
    assert by["diabetes"]["band"] == "high"
    assert by["diabetes"]["see_doctor"] is True
    assert by["diabetes"]["disclaimer"]
    assert by["gad7"]["band"] is None  # rule-based screener → band-less

