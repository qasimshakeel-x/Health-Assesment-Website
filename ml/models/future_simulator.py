"""Future Health Simulation — 10-year projection with client-side cached coefficients."""
from typing import Dict


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

    def simulate(
        self,
        current_profile: Dict,
        years: int = 10,
        lifestyle_changes: Dict = None
    ) -> Dict:
        """Run 10-year simulation comparing current vs improved lifestyle."""
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
        """Project health metrics forward N years."""
        sleep_delta = changes.get("sleep_hours", 0)
        exercise_delta = changes.get("exercise_level", 0)
        smoking_quit = changes.get("smoking_quit", False)
        bmi_improvement = changes.get("bmi_improvement", 0)
        diet_level = changes.get("diet_improvement", "none")

        projected_bmi = profile.get("bmi", 25) + (self.COEFFICIENTS["bmi_change_per_year"][diet_level] * years) + bmi_improvement
        projected_bio_age = profile.get("biological_age", profile.get("age", 40)) + (
            self.COEFFICIENTS["bio_age_change_per_year"]["exercise_improvement"] * exercise_delta * years
        )
        if smoking_quit:
            projected_bio_age += self.COEFFICIENTS["bio_age_change_per_year"]["smoking_quit"] * years
        if sleep_delta > 0:
            projected_bio_age += self.COEFFICIENTS["bio_age_change_per_year"]["sleep_improvement"] * sleep_delta * years

        projected_diabetes = max(0, profile.get("diabetes_risk", 30) + self.COEFFICIENTS["disease_risk_change_per_year"]["diet_improvement"] * years)
        projected_heart = max(0, profile.get("heart_risk", 25) + self.COEFFICIENTS["disease_risk_change_per_year"]["exercise_improvement"] * years)

        return {
            "bmi": round(projected_bmi, 1),
            "biological_age": round(projected_bio_age, 1),
            "diabetes_risk": round(projected_diabetes, 1),
            "heart_risk": round(projected_heart, 1)
        }

    def _compare(self, current: Dict, improved: Dict) -> Dict:
        return {
            "bmi_diff": round(improved["bmi"] - current["bmi"], 1),
            "age_diff": round(improved["biological_age"] - current["biological_age"], 1),
            "diabetes_diff": round(improved["diabetes_risk"] - current["diabetes_risk"], 1),
            "heart_diff": round(improved["heart_risk"] - current["heart_risk"], 1)
        }
