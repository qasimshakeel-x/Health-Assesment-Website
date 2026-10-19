"""Rule-based screening classifiers — Phase 2-5 screeners (09-ML-TRAINING-SPEC §3).

Clinically-validated scoring (GAD-7 thresholds, STOP-BANG, IDF metabolic criteria, burnout
exhaustion scoring) — training nahi chahiye, isliye pkl/load nahi. Har screener ka output
{risk_percent, risk_label, confidence, detail} — disease_risk_results ka shape.

Registry `scoring="rule"` entries idhar dispatch hote hain (registry.py).
Spec 10: ye file "generic base for Phase 2-5 screeners" hai — naya rule-based screener
sirf ek method + registry entry add karke ship hota hai.
"""
from typing import Dict, Any, Optional

from ml.models.base import MLModel
from ml.models.constants import RISK_CATEGORIES


def _risk_label(risk: float) -> str:
    for low, high, label in RISK_CATEGORIES:
        if low <= risk < high:
            return label
    return RISK_CATEGORIES[-1][2]


def _pct(score: float, total: float) -> float:
    """Score → 0-100 percentage, clipped."""
    if total <= 0:
        return 0.0
    return round(max(0.0, min(100.0, (score / total) * 100.0)), 2)


class ScreeningClassifier(MLModel):
    """Rule-based scorers for screeners: gad7, sleep_apnea, metabolic_syndrome, burnout."""

    def __init__(self):
        super().__init__("screening_classifier")
        self.is_loaded = True  # rule-based — no pkl to load

    # ── MLModel interface (no-ops — scoring-based, 09 §4 clinical review instead of AUC) ──
    def train(self, X, y) -> Dict[str, float]:
        return {}

    def evaluate(self, X_test, y_test) -> Dict[str, float]:
        return {}

    def predict_proba(self, X):
        raise NotImplementedError("Rule-based screeners do not use predict_proba")

    # ── Public entry: sab active rule-based screeners ──
    def predict_all(self, profile: Dict[str, Any], screening: Dict[str, Dict]) -> Dict[str, Dict]:
        """profile = health form dict (+ derived diabetes_risk etc.), screening = {key: responses}."""
        results = {}
        scorer_map = {
            "gad7": self.score_gad7,
            "sleep_apnea": self.score_sleep_apnea,
            "metabolic_syndrome": self.score_metabolic_syndrome,
            "burnout": self.score_burnout,
        }
        for key, fn in scorer_map.items():
            out = fn(profile, screening.get(key) or {})
            if out is not None:
                results[key] = out
        return results

    # ── GAD-7 (Anxiety) — official 7-item, 0-3 scale, cut-offs 5/10/15 (06 Phase 2) ──
    def score_gad7(self, profile: Dict, responses: Dict) -> Optional[Dict]:
        answers = responses.get("answers")
        if not answers or len(answers) != 7:
            return None
        total = sum(int(a) for a in answers)
        risk = _pct(total, 21)
        if total <= 4:
            tier = "Minimal"
        elif total <= 9:
            tier = "Mild"
        elif total <= 14:
            tier = "Moderate"
        else:
            tier = "Severe"
        return {
            "risk_percent": risk,
            "risk_label": _risk_label(risk),
            "confidence": None,
            "detail": tier,
            "detail_label": f"Anxiety: {tier} ({total}/21)",
        }

    # ── Sleep Apnea — STOP-BANG subset (06 Phase 2: snore + wake-tired + existing inputs) ──
    def score_sleep_apnea(self, profile: Dict, responses: Dict) -> Optional[Dict]:
        if not responses:
            return None  # questions required hain — missing pe skip
        score = 0
        max_score = 8
        yes = lambda k: str(responses.get(k, "")).lower() in ("yes", "1", "true")
        if yes("snoring"):
            score += 1
        if yes("wake_tired"):
            score += 1
        if yes("witnessed_apnea"):
            score += 1
        if yes("daytime_sleepy"):
            score += 1
        bp_sys = profile.get("bp_systolic") or 0
        bp_dia = profile.get("bp_diastolic") or 0
        if bp_sys >= 130 or bp_dia >= 85:
            score += 1  # "P" — high BP
        if float(profile.get("bmi") or 0) > 35:
            score += 1  # "B" — BMI>35
        if int(profile.get("age") or 0) > 50:
            score += 1  # "A" — age>50
        if int(profile.get("gender") or 0) == 1:
            score += 1  # "G" — male
        risk = _pct(score, max_score)
        if score <= 3:
            tier = "Low"
        elif score <= 5:
            tier = "Intermediate"
        else:
            tier = "High"
        return {
            "risk_percent": risk,
            "risk_label": _risk_label(risk),
            "confidence": None,
            "detail": tier,
            "detail_label": f"STOP-BANG {score}/{max_score} — {tier}",
        }

    # ── Metabolic Syndrome — IDF criteria (06 Phase 3: waist required + 5-factor cluster) ──
    def score_metabolic_syndrome(self, profile: Dict, responses: Dict) -> Optional[Dict]:
        waist = profile.get("waist_circumference")
        if not waist:
            return None  # waist measurement required
        gender = int(profile.get("gender") or 0)
        # IDF central obesity cutoffs (Asian): M ≥90cm, F ≥80cm
        central_obesity = float(waist) >= (90 if gender == 1 else 80)
        yes = lambda k: str(responses.get(k, "")).lower() in ("yes", "1", "true")
        bp_elevated = (float(profile.get("bp_systolic") or 0) >= 130
                       or float(profile.get("bp_diastolic") or 0) >= 85
                       or yes("doctor_high_bp"))
        glucose_high = (float(profile.get("diabetes_risk") or 0) >= 50
                        or yes("doctor_high_sugar") or yes("frequent_thirst_urination"))
        poor_diet = str(profile.get("diet_quality") or "").lower() == "poor"
        low_activity = int(profile.get("exercise_level") or 0) <= 1

        factors = [central_obesity, bp_elevated, glucose_high, poor_diet, low_activity]
        present = sum(1 for f in factors if f)
        # IDF: diagnosis = central obesity + ≥2 others; risk score counts all present factors
        risk = _pct(present, len(factors))
        if central_obesity and present >= 3:
            tier = "Meets IDF criteria"
        elif present >= 2:
            tier = "At risk"
        else:
            tier = "Unlikely"
        return {
            "risk_percent": risk,
            "risk_label": _risk_label(risk),
            "confidence": None,
            "detail": tier,
            "detail_label": f"{present}/5 factors — {tier}",
        }

    # ── Burnout — work hours + job satisfaction + 3 exhaustion items (06 Phase 4) ──
    def score_burnout(self, profile: Dict, responses: Dict) -> Optional[Dict]:
        if not responses:
            return None
        work_hours = responses.get("work_hours")
        satisfaction = responses.get("job_satisfaction")
        exhaustion = responses.get("exhaustion")
        if work_hours is None or satisfaction is None or not exhaustion:
            return None
        if len(exhaustion) != 3:
            return None

        # exhaustion: 3 items × 0-3 → 0-9 (PHQ-style)
        exhaustion_total = sum(int(e) for e in exhaustion)
        score = _pct(exhaustion_total, 9) * 0.6          # exhaustion dominant (0-60)
        if int(work_hours) > 50:
            score += 20
        elif int(work_hours) > 40:
            score += 10
        if int(satisfaction) <= 2:
            score += 20
        elif int(satisfaction) == 3:
            score += 10
        risk = round(min(100.0, score), 2)
        if risk < 25:
            tier = "No Burnout"
        elif risk < 60:
            tier = "At Risk"
        else:
            tier = "Burnout Detected"
        return {
            "risk_percent": risk,
            "risk_label": _risk_label(risk),
            "confidence": None,
            "detail": tier,
            "detail_label": f"Exhaustion {exhaustion_total}/9 — {tier}",
        }
