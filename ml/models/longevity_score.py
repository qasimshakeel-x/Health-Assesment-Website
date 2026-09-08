"""Longevity Score Engine — weighted 0-100 composite health score."""
import numpy as np
from ml.models.constants import LONGEVITY_WEIGHTS


class LongevityScoreEngine:
    """Calculates a composite longevity score from 0 to 100."""

    def __init__(self):
        self.is_loaded = True

    def calculate(
        self,
        bmi: float,
        sleep_hours: float,
        exercise_level: int,
        avg_disease_risk: float,
        depression_score: int
    ) -> dict:
        """Calculate longevity score and its components."""
        components = {}

        # BMI component (0-100, ideal=22, range 15-40)
        bmi_score = max(0, 100 - abs(bmi - 22) * 4)
        components["bmi"] = round(bmi_score * LONGEVITY_WEIGHTS["bmi"], 2)

        # Sleep component (0-100, ideal=8h, range 3-12)
        sleep_score = max(0, 100 - abs(sleep_hours - 8) * 15)
        components["sleep"] = round(sleep_score * LONGEVITY_WEIGHTS["sleep"], 2)

        # Exercise component (0-100, ideal=4)
        exercise_score = exercise_level * 25
        components["exercise"] = round(exercise_score * LONGEVITY_WEIGHTS["exercise"], 2)

        # Disease risk component (inverted: lower risk = higher score)
        disease_score = max(0, 100 - avg_disease_risk)
        components["disease_risk"] = round(disease_score * LONGEVITY_WEIGHTS["disease_risk"], 2)

        # Depression component (PHQ-9 max 27, lower = better)
        depression_component_score = max(0, 100 - (depression_score / 27) * 100)
        components["depression"] = round(depression_component_score * LONGEVITY_WEIGHTS["depression"], 2)

        total_score = sum(components.values())
        total_score = max(0, min(100, total_score))

        category = self._get_category(total_score)

        return {
            "score": round(total_score, 1),
            "components": components,
            "category": category,
            "description": self._get_description(category)
        }

    def _get_category(self, score: float) -> str:
        if score < 40:
            return "Poor"
        elif score < 60:
            return "Moderate"
        elif score < 80:
            return "Good"
        else:
            return "Excellent"

    def _get_description(self, category: str) -> str:
        descriptions = {
            "Poor": "Your health metrics indicate significant room for improvement. Focus on lifestyle changes.",
            "Moderate": "You're on the right track but there are areas that could be improved.",
            "Good": "Your health indicators are positive. Keep maintaining healthy habits.",
            "Excellent": "Outstanding! Your lifestyle choices are contributing to strong longevity."
        }
        return descriptions.get(category, "")
