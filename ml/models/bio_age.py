"""Biological Age Estimation Engine — penalty-based formula."""
import numpy as np
from ml.models.constants import LONGEVITY_WEIGHTS


class BioAgeEngine:
    """Estimates biological age based on health metrics using a penalty-based formula."""

    IDEAL_BMI = 22.0
    IDEAL_SLEEP = 8.0
    IDEAL_EXERCISE = 4.0
    PENALTY_PER_BMI_UNIT = 0.5
    PENALTY_PER_SLEEP_DEFICIT = 0.8
    PENALTY_PER_EXERCISE_DEFICIT = 0.6
    SMOKING_PENALTY = 5.0
    ALCOHOL_PENALTY_PER_DRINK = 0.3
    FAMILY_HISTORY_PENALTY = 1.5
    DISEASE_RISK_PENALTY_FACTOR = 0.05

    def __init__(self):
        self.is_loaded = True

    def calculate(
        self,
        age: int,
        bmi: float,
        sleep_hours: float,
        exercise_level: int,
        smoking: bool,
        alcohol: int,
        family_history: list,
        avg_disease_risk: float
    ) -> dict:
        """Calculate biological age and age difference."""
        penalties = []

        # BMI penalty
        bmi_diff = abs(bmi - self.IDEAL_BMI)
        if bmi_diff > 2:
            bmi_penalty = bmi_diff * self.PENALTY_PER_BMI_UNIT
            penalties.append({"factor": "BMI deviation", "penalty": round(bmi_penalty, 2)})

        # Sleep penalty
        if sleep_hours < 6:
            sleep_penalty = (self.IDEAL_SLEEP - sleep_hours) * self.PENALTY_PER_SLEEP_DEFICIT
            penalties.append({"factor": "Sleep deficit", "penalty": round(sleep_penalty, 2)})

        # Exercise penalty
        exercise_deficit = max(0, self.IDEAL_EXERCISE - exercise_level)
        if exercise_deficit > 0:
            exercise_penalty = exercise_deficit * self.PENALTY_PER_EXERCISE_DEFICIT
            penalties.append({"factor": "Low exercise", "penalty": round(exercise_penalty, 2)})

        # Smoking penalty
        if smoking:
            penalties.append({"factor": "Smoking", "penalty": self.SMOKING_PENALTY})

        # Alcohol penalty
        if alcohol > 0:
            alcohol_penalty = alcohol * self.ALCOHOL_PENALTY_PER_DRINK
            penalties.append({"factor": "Alcohol consumption", "penalty": round(alcohol_penalty, 2)})

        # Family history penalty (1 penalty per positive history)
        family_count = sum(1 for h in family_history if h == 1)
        if family_count > 0:
            family_penalty = family_count * self.FAMILY_HISTORY_PENALTY
            penalties.append({"factor": f"Family history ({family_count} conditions)", "penalty": round(family_penalty, 2)})

        # Disease risk penalty
        disease_penalty = avg_disease_risk * self.DISEASE_RISK_PENALTY_FACTOR
        if disease_penalty > 0.5:
            penalties.append({"factor": "Elevated disease risk", "penalty": round(disease_penalty, 2)})

        total_penalty = sum(p["penalty"] for p in penalties)
        biological_age = age + total_penalty
        age_difference = biological_age - age

        return {
            "chronological_age": age,
            "biological_age": round(biological_age, 1),
            "age_difference": round(age_difference, 1),
            "penalties": penalties,
            "status": "older" if age_difference > 0 else "younger" if age_difference < 0 else "optimal"
        }
