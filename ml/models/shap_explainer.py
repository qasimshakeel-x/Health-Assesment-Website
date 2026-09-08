"""SHAP Explainability Dashboard — TreeExplainer for disease risk models."""
import numpy as np
from typing import Dict, List
from ml.models.constants import DISEASE_RISK_FEATURES


class SHAPDashboard:
    """Generates SHAP explanations for disease risk predictions."""

    def __init__(self):
        self.explainer = None

    def setup(self, model):
        """Initialize SHAP TreeExplainer with the Random Forest model."""
        try:
            import shap
            self.explainer = shap.TreeExplainer(model)
        except ImportError:
            self.explainer = None

    def explain(self, X: np.ndarray, disease: str = "diabetes") -> Dict[str, List]:
        """Generate SHAP explanations for a single prediction."""
        if self.explainer is None:
            return {"features": [], "error": "SHAP explainer not initialized"}

        try:
            shap_values = self.explainer.shap_values(X)
            if isinstance(shap_values, list):
                shap_vals = shap_values[1]  # Class 1 (positive/risk)
            else:
                shap_vals = shap_values

            feature_shap = []
            for i, name in enumerate(DISEASE_RISK_FEATURES):
                if i < len(shap_vals[0]):
                    val = float(shap_vals[0][i])
                    feature_shap.append({
                        "feature": name,
                        "shap_value": round(val, 6),
                        "direction": "increases_risk" if val > 0 else "decreases_risk",
                        "abs_value": abs(val),
                        "plain_language": self._plain_language(name, val)
                    })

            # Sort by absolute SHAP value
            feature_shap.sort(key=lambda x: x["abs_value"], reverse=True)

            return {
                "disease": disease,
                "features": feature_shap[:10],
                "top_5_factors": [f["plain_language"] for f in feature_shap[:5]],
                "base_value": float(self.explainer.expected_value[1]) if isinstance(self.explainer.expected_value, (list, np.ndarray)) else float(self.explainer.expected_value)
            }
        except Exception as e:
            return {"features": [], "error": str(e)}

    def _plain_language(self, feature: str, value: float) -> str:
        """Convert feature name and SHAP value to plain language."""
        direction = "increases" if value > 0 else "decreases"
        names = {
            "age": "Your age",
            "gender": "Your gender",
            "bmi": "Your BMI (body mass index)",
            "sleep_hours": "Your sleep habits",
            "exercise_level": "Your exercise level",
            "smoking": "Your smoking status",
            "alcohol": "Your alcohol consumption",
            "family_diabetes": "Family history of diabetes",
            "family_heart": "Family history of heart disease",
            "family_hypertension": "Family history of hypertension",
            "family_cancer": "Family history of cancer"
        }
        name = names.get(feature, feature)
        return f"{name} {direction} your risk"
