"""Future Health Simulation — N-year projection with client-side cached coefficients.

WS-5: har scenario ab sirf BMI/bio-age/2 risks nahi — **poori `disease_risk_results` list
(16 diseases)** project karta hai + dono scenarios ka longevity score LongevityScoreEngine se
banta hai (01-PRD §6 weights). Coefficients class-ke constants hain → frontend initial response
ke baad slider pe client-side recalculation kar sake (08-FRONTEND §Simulator, Observer pattern).
"""
from typing import Dict, List


class FutureSimulator:
    """Projects health metrics over time based on lifestyle scenarios."""

    # Cached coefficients for client-side recalculation (Observer pattern)
    COEFFICIENTS = {
        "bmi_change_per_year": {
            "none": 0.0,
            "moderate": -0.3,
            "strict": -0.8
        },
        "disease_risk_change_per_year": {
            "smoking_quit": -2.5,
            "exercise_improvement": -1.5,
            "diet_improvement": -2.0
        },
        "bio_age_change_per_year": {
            "sleep_improvement": -0.4,
            "exercise_improvement": -0.3,
            "smoking_quit": -0.6,
            "bmi_improvement": -0.2
        }
    }

    def __init__(self):
        # Formula-based (koi pkl nahi) — dono scenarios ka longevity score isi se
        try:
            from ml.models.longevity_score import LongevityScoreEngine
            self._longevity_engine = LongevityScoreEngine()
        except Exception:
            self._longevity_engine = None

    def simulate(
        self,
        current_profile: Dict,
        years: int = 10,
        lifestyle_changes: Dict = None
    ) -> Dict:
        """Run N-year simulation comparing current vs improved lifestyle."""
        if lifestyle_changes is None:
            lifestyle_changes = {}

        current_scenario = self._project(current_profile, years, {})
        improved_scenario = self._project(current_profile, years, lifestyle_changes)

        return {
            "years": years,
            "current": current_scenario,
            "improved": improved_scenario,
            "comparison": self._compare(current_scenario, improved_scenario)
        }

    def _project(self, profile: Dict, years: int, changes: Dict) -> Dict:
        """Project health metrics forward N years (bina changes ke = current baseline)."""
        sleep_delta = changes.get("sleep_hours", 0)
        exercise_delta = changes.get("exercise_level", 0)
        smoking_quit = changes.get("smoking_quit", False)
        bmi_improvement = changes.get("bmi_improvement", 0)
        diet_level = changes.get("diet_improvement", "none")

        bmi_coeff = self.COEFFICIENTS["bmi_change_per_year"].get(diet_level, 0.0)
        projected_bmi = float(profile.get("bmi", 25.0)) + (bmi_coeff * years) + float(bmi_improvement)
        bio_age_base = float(profile.get("biological_age", profile.get("age", 40.0)))
        projected_bio_age = bio_age_base + (
            self.COEFFICIENTS["bio_age_change_per_year"]["exercise_improvement"] * exercise_delta * years
        )
        if smoking_quit:
            projected_bio_age += self.COEFFICIENTS["bio_age_change_per_year"]["smoking_quit"] * years
        if sleep_delta > 0:
            projected_bio_age += self.COEFFICIENTS["bio_age_change_per_year"]["sleep_improvement"] * sleep_delta * years

        # ── Risk delta per year — SAME delta har disease pe lagta hai (WS-5: 16 comparisons) ──
        risk_coeff = self.COEFFICIENTS["disease_risk_change_per_year"]
        risk_per_year = 0.0
        if smoking_quit:
            risk_per_year += risk_coeff["smoking_quit"]
        if exercise_delta > 0:
            risk_per_year += risk_coeff["exercise_improvement"] * min(1.0, exercise_delta / 2.0)
        if diet_level == "moderate":
            risk_per_year += risk_coeff["diet_improvement"] * 0.5
        elif diet_level == "strict":
            risk_per_year += risk_coeff["diet_improvement"]

        diseases: List[Dict] = []
        for d in profile.get("disease_risks") or []:
            base = float(d.get("risk_percent") or 0.0)
            new = max(0.0, min(100.0, base + risk_per_year * years))
            item = dict(d)
            item["risk_percent"] = round(new, 1)
            item["delta"] = round(new - base, 1)
            diseases.append(item)

        def _risk_of(key: str):
            for d in diseases:
                if d.get("disease_key") == key:
                    return d["risk_percent"]
            return None

        # diabetes/heart top-level keys rakhe (purane clients) — list se derive, warna purana formula
        projected_diabetes = _risk_of("diabetes")
        if projected_diabetes is None:
            projected_diabetes = max(
                0.0,
                float(profile.get("diabetes_risk", 30.0)) + self._diet_coeff(diet_level) * years,
            )
        projected_heart = _risk_of("heart")
        if projected_heart is None:
            heart_coeff = risk_coeff["exercise_improvement"] if exercise_delta > 0 else 0.0
            projected_heart = max(0.0, float(profile.get("heart_risk", 25.0)) + heart_coeff * years)

        # Avg risk (projected) → longevity input
        if diseases:
            avg_risk = sum(d["risk_percent"] for d in diseases) / len(diseases)
        else:
            avg_risk = float(profile.get("avg_disease_risk", 30.0))

        projected_sleep = max(3.0, min(12.0, float(profile.get("sleep_hours", 7.0)) + sleep_delta))
        projected_exercise = max(0, min(4, int(profile.get("exercise_level", 2)) + exercise_delta))
        longevity = self._longevity_score(
            projected_bmi, projected_sleep, projected_exercise, avg_risk, profile
        )

        return {
            "bmi": round(projected_bmi, 1),
            "biological_age": round(projected_bio_age, 1),
            "diabetes_risk": round(float(projected_diabetes), 1),
            "heart_risk": round(float(projected_heart), 1),
            "longevity_score": longevity,
            "avg_disease_risk": round(float(avg_risk), 2),
            "diseases": diseases,   # WS-5: 16-disease comparison (current vs improved)
        }

    @classmethod
    def _diet_coeff(cls, diet_level: str) -> float:
        c = cls.COEFFICIENTS["disease_risk_change_per_year"]["diet_improvement"]
        if diet_level == "strict":
            return c
        if diet_level == "moderate":
            return c * 0.5
        return 0.0

    def _longevity_score(self, bmi, sleep_hours, exercise_level, avg_disease_risk, profile) -> float:
        """Dono scenarios ka longevity score ek hi engine se (consistent comparison)."""
        fallback = float(profile.get("longevity_score") or 0.0)
        if self._longevity_engine is None:
            return fallback
        try:
            result = self._longevity_engine.calculate(
                bmi=bmi,
                sleep_hours=sleep_hours,
                exercise_level=exercise_level,
                avg_disease_risk=avg_disease_risk,
                depression_score=float(profile.get("phq9_total") or 0),
            )
            return round(float(result["score"]), 1)
        except Exception:
            return fallback

    def _compare(self, current: Dict, improved: Dict) -> Dict:
        return {
            "bmi_diff": round(improved["bmi"] - current["bmi"], 1),
            "age_diff": round(improved["biological_age"] - current["biological_age"], 1),
            "diabetes_diff": round(improved["diabetes_risk"] - current["diabetes_risk"], 1),
            "heart_diff": round(improved["heart_risk"] - current["heart_risk"], 1),
            "longevity_diff": round(improved["longevity_score"] - current["longevity_score"], 1),
        }
