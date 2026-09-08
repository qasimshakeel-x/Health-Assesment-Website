"""ML Pipeline Orchestrator — Facade pattern, single entrypoint for all ML inference."""
import numpy as np
from typing import Dict, Any, Optional
from ml.models.disease_risk import DiseaseRiskEngine
from ml.models.bio_age import BioAgeEngine
from ml.models.longevity_score import LongevityScoreEngine
from ml.models.depression import DepressionClassifier
from ml.models.constants import DISEASE_RISK_FEATURES


class MLPipelineOrchestrator:
    """Single entrypoint that coordinates all ML modules."""

    def __init__(self):
        self.disease_engine = DiseaseRiskEngine()
        self.bio_age_engine = BioAgeEngine()
        self.longevity_engine = LongevityScoreEngine()
        self.depression_classifier = DepressionClassifier()
        self.models_loaded = False

    def load_models(self):
        """Load all pre-trained models. Called once at FastAPI startup."""
        self.disease_engine.load()
        self.bio_age_engine = BioAgeEngine()  # Formula-based, no persistence needed
        self.longevity_engine = LongevityScoreEngine()  # Formula-based
        self.depression_classifier.load()
        self.models_loaded = True

    def run_pipeline(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full 9-module pipeline. Returns complete results dict."""
        if not self.models_loaded:
            raise RuntimeError("Models not loaded")

        # Build feature vector for disease prediction
        feature_vector = self._build_feature_vector(profile_data)

        # Run modules (can be parallelized with asyncio.gather in production)
        disease_results = self.disease_engine.predict_proba(np.array([feature_vector]))

        # Average disease risk for bio age and longevity calculations
        avg_risk = np.mean([d["risk_percent"] for d in disease_results.values()])

        # Biological age
        bio_age = self.bio_age_engine.calculate(
            age=profile_data["age"],
            bmi=profile_data.get("bmi", self._compute_bmi(profile_data["height"], profile_data["weight"])),
            sleep_hours=profile_data["sleep_hours"],
            exercise_level=profile_data["exercise_level"],
            smoking=profile_data["smoking"],
            alcohol=profile_data["alcohol"],
            family_history=profile_data.get("family_history", [0, 0, 0, 0]),
            avg_disease_risk=avg_risk
        )

        # Depression classification
        phq9_scores = profile_data.get("phq9", [0] * 9)
        depression_result = self.depression_classifier.predict_depression(phq9_scores)

        # Longevity score
        bmi = profile_data.get("bmi", self._compute_bmi(profile_data["height"], profile_data["weight"]))
        longevity = self.longevity_engine.calculate(
            bmi=bmi,
            sleep_hours=profile_data["sleep_hours"],
            exercise_level=profile_data["exercise_level"],
            avg_disease_risk=avg_risk,
            depression_score=depression_result["phq9_total"]
        )

        # SHAP explanations for the RF model
        shap_values = self._compute_shap(feature_vector)

        return {
            "disease_risks": disease_results,
            "biological_age": bio_age,
            "longevity_score": longevity,
            "depression": depression_result,
            "shap_explanations": shap_values,
            "avg_disease_risk": round(float(avg_risk), 2)
        }

    def _build_feature_vector(self, data: Dict) -> list:
        """Convert profile data dict to feature array."""
        bmi = data.get("bmi", self._compute_bmi(data["height"], data["weight"]))
        family = data.get("family_history", [0, 0, 0, 0])
        return [
            data["age"], data["gender"], bmi, data["sleep_hours"],
            data["exercise_level"], int(data["smoking"]), data["alcohol"],
            family[0], family[1], family[2], family[3]
        ]

    def _compute_bmi(self, height: float, weight: float) -> float:
        return weight / (height / 100.0) ** 2

    def _compute_shap(self, feature_vector: list) -> list:
        """Compute SHAP values using TreeExplainer on the RF model."""
        try:
            import shap
            if hasattr(self.disease_engine, 'models') and "diabetes" in self.disease_engine.models:
                rf_model = self.disease_engine.models["diabetes"].get("random_forest")
                if rf_model is not None:
                    explainer = shap.TreeExplainer(rf_model)
                    shap_vals = explainer.shap_values(np.array([feature_vector]))
                    if isinstance(shap_vals, list):
                        shap_vals = shap_vals[1]  # Class 1 (positive)

                    results = []
                    for i, name in enumerate(DISEASE_RISK_FEATURES):
                        val = float(shap_vals[0][i]) if len(shap_vals[0]) > i else 0.0
                        results.append({
                            "feature": name,
                            "shap_value": round(val, 6),
                            "impact": "increases risk" if val > 0 else "decreases risk"
                        })
                    results.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
                    return results[:5]
        except Exception:
            pass
        return []
