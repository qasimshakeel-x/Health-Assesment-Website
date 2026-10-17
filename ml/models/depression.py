"""Depression Risk Detection — PHQ-9 Gradient Boosting classifier."""
import os
import numpy as np
from typing import Dict
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from imblearn.over_sampling import SMOTE
from ml.models.base import MLModel
from ml.models.constants import DEPRESSION_LEVELS
from ml.predict import has_artifact, predict_risk

# Absolute pkl path — cwd-relative path startup crash karta tha (BUG-1 fix)
_PKL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pkl", "depression_classifier.pkl")


class DepressionClassifier(MLModel):
    """PHQ-9 based depression risk classifier using Gradient Boosting."""

    SEVERE_DISCLAIMER = "This tool does not diagnose depression. It estimates risk only."
    CRISIS_RESOURCES = (
        "If you are in crisis, please reach out to the 988 Suicide & Crisis Lifeline "
        "by calling or texting 988 (US). You are not alone."
    )

    def __init__(self):
        super().__init__("depression_classifier")
        self.model = GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train on PHQ-9 responses."""
        smote = SMOTE(random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y)
        self.model.fit(X_resampled, y_resampled)

        y_pred = self.model.predict(X_resampled)
        return {
            "weighted_f1": f1_score(y_resampled, y_pred, average="weighted"),
            "macro_f1": f1_score(y_resampled, y_pred, average="macro")
        }

    def _artifact_risk(self, phq9_scores: list):
        """ML_TRAINING.md §9: use the calibrated `ml/models/depression.joblib` (PHQ-9 items →
        moderate+ risk) when present; None → keep the legacy severity-only response."""
        if not has_artifact("depression"):
            return None
        payload = {f"phq{i}": float(s) for i, s in enumerate(phq9_scores, start=1)}
        try:
            return predict_risk("depression", payload)
        except Exception as exc:      # corrupt/old artifact → legacy path
            import logging
            logging.getLogger(__name__).warning("predict_risk(depression) failed: %s", exc)
            return None

    def predict_depression(self, phq9_scores: list) -> dict:
        """Classify depression severity from PHQ-9 scores."""
        X = np.array([phq9_scores])
        proba = self.model.predict_proba(X)[0]
        predicted_class = self.model.predict(X)[0]

        # Get severity level
        severity = self._phq9_to_level(sum(phq9_scores))
        confidence = float(max(proba)) * 100

        contributing_factors = self._get_contributing_factors(phq9_scores)

        result = {
            "severity": severity,
            "phq9_total": sum(phq9_scores),
            "confidence": round(confidence, 1),
            "contributing_factors": contributing_factors,
            "disclaimer": self.SEVERE_DISCLAIMER,
            "recommendations": self._get_recommendations(severity)
        }

        # §9: calibrated screening risk + coded referral decision (red flags in code, not LLM)
        art = self._artifact_risk(phq9_scores)
        if art is not None:
            result["risk"] = art["risk"]
            result["band"] = art["band"]
            result["see_doctor"] = art["see_doctor"] or severity in (
                "Moderate", "Moderately Severe", "Severe")

        if severity == "Severe":
            result["crisis_resources"] = self.CRISIS_RESOURCES

        return result

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        y_pred = self.model.predict(X_test)
        return {
            "weighted_f1": f1_score(y_test, y_pred, average="weighted"),
            "severe_recall": self._severe_class_recall(y_test, y_pred)
        }

    def _phq9_to_level(self, total: int) -> str:
        for (low, high), label in DEPRESSION_LEVELS.items():
            if low <= total <= high:
                return label
        return "Unknown"

    def _severe_class_recall(self, y_true, y_pred) -> float:
        severe_idx = list(DEPRESSION_LEVELS.values()).index("Severe") if "Severe" in DEPRESSION_LEVELS.values() else -1
        if severe_idx == -1:
            return 0.0
        true_severe = (y_true == severe_idx)
        pred_severe = (y_pred == severe_idx)
        if true_severe.sum() == 0:
            return 0.0
        return float((true_severe & pred_severe).sum() / true_severe.sum())

    def _get_contributing_factors(self, phq9_scores: list) -> list:
        factors = []
        questions = [
            "Loss of interest", "Feeling down", "Sleep problems",
            "Low energy", "Appetite changes", "Low self-esteem",
            "Concentration problems", "Psychomotor changes", "Self-harm thoughts"
        ]
        for i, score in enumerate(phq9_scores):
            if score >= 2:
                factors.append({"question": questions[i], "score": score, "severity": "high" if score == 3 else "moderate"})
        return factors

    def _get_recommendations(self, severity: str) -> list:
        recommendations = {
            "No Depression": ["Maintain your current healthy habits", "Stay socially connected"],
            "Mild": ["Consider speaking with a counselor", "Regular exercise can help", "Practice mindfulness or meditation"],
            "Moderate": ["Please consider professional help", "A therapist can provide targeted support", "Avoid alcohol which can worsen symptoms"],
            "Moderately Severe": ["Professional help is strongly recommended", "Contact your healthcare provider", "Do not hesitate to reach out to crisis resources if needed"],
            "Severe": ["Please seek immediate professional help", "Contact a mental health professional today", "Use crisis resources if you are in distress"]
        }
        return recommendations.get(severity, [])

    def save(self, path: str = None):
        import pickle
        path = path or _PKL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        self.is_loaded = True

    def load(self, path: str = None):
        import pickle
        path = path or _PKL_PATH
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        self.is_loaded = True
