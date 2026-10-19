"""Disease Risk Prediction Engine — Ensemble of RF + XGBoost + Logistic Regression."""
import logging
import os
import numpy as np
from typing import Dict
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from imblearn.over_sampling import SMOTE
from ml.models.base import MLModel
from ml.models.constants import (ENSEMBLE_WEIGHTS, RISK_CATEGORIES, DISEASE_RISK_FEATURES,
                                 PHASE1_SCHEMAS)
from ml.predict import has_artifact, predict_risk

log = logging.getLogger(__name__)

# Absolute pkl path — cwd-relative path se startup crash hota tha (server_output.log FileNotFoundError)
_PKL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pkl", "disease_ensemble.pkl")


def _yn(value) -> int:
    """Yes/No answer → 0/1 (frontend "yes"/"no", bool, 1/0 — bool("no")==True bug se bachao)."""
    if isinstance(value, str):
        return 1 if value.strip().lower() in ("yes", "y", "true", "1") else 0
    return 1 if bool(value) else 0


class DiseaseRiskEngine(MLModel):
    """Ensemble model predicting risk for Diabetes, Heart Disease, Hypertension, Obesity."""

    DISEASES = ["diabetes", "heart", "hypertension", "obesity"]

    def __init__(self):
        super().__init__("disease_risk_ensemble")
        self.models = {}
        self.diseases_trained = False

    def _get_ensemble(self):
        """Return the three base estimators with their weights."""
        return {
            "random_forest": RandomForestClassifier(
                n_estimators=200, max_depth=10, random_state=42, n_jobs=-1
            ),
            "xgboost": self._get_xgboost(),
            "logistic_regression": LogisticRegression(
                max_iter=1000, random_state=42, solver="lbfgs"
            ),
        }

    def _get_xgboost(self):
        try:
            from xgboost import XGBClassifier
            # NOTE: xgboost 2.x mein use_label_encoder param hat gaya — ab remove (silence warning)
            return XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.1,
                eval_metric="logloss",
                random_state=42, n_jobs=-1
            )
        except ImportError:
            # Fallback to GradientBoosting if xgboost not installed
            return GradientBoostingClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.1,
                random_state=42
            )

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train ensemble on feature matrix X and binary labels y.

        NOTE: ye single-disease single-X variant hai aur self.models ko estimator-name se
        populate karta hai (predict_proba() disease-key se expect karta hai). Per-disease
        training ab ml/train.py karta hai; RFC: Strategy interface ke liye yahan sirf
        train() implement karna zaroori tha.
        """
        smote = SMOTE(random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y)

        self.models = {}
        metrics = {}

        for name, model in self._get_ensemble().items():
            model.fit(X_resampled, y_resampled)
            self.models[name] = model
            y_pred_proba = model.predict_proba(X_resampled)[:, 1]
            metrics[f"{name}_auc"] = roc_auc_score(y_resampled, y_pred_proba) if len(np.unique(y)) > 1 else 0.0

        self.diseases_trained = True
        return metrics

    def predict_proba(self, X: np.ndarray) -> Dict[str, Dict]:
        """Return risk probabilities for all diseases."""
        if not self.diseases_trained and not self.models:
            raise RuntimeError("Models not trained or loaded")

        results = {}
        for disease in self.DISEASES:
            if disease in self.models:
                disease_models = self.models[disease]
                predictions = []
                for name, model in disease_models.items():
                    proba = model.predict_proba(X)[:, 1]
                    predictions.append(ENSEMBLE_WEIGHTS[name] * proba)
                ensemble_proba = np.sum(predictions, axis=0)[0] * 100
                results[disease] = {
                    "risk_percent": round(float(ensemble_proba), 2),
                    "category": self._get_category(float(ensemble_proba))
                }
        return results

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        return {}  # Handled per-disease in ml/train.py

    # ── Per-disease inference (WS-7: par-disease screening questions) ──────────────
    def _build_vector(self, disease: str, p: Dict, extras: Dict) -> np.ndarray:
        """Profile + screening responses → disease feature vector.

        PHASE1_SCHEMAS ke order mein exact (BUG-5: training == inference columns):
        base 11 features + 3 disease-specific screening symptoms.
        """
        fam = p.get("family_history", [0, 0, 0, 0])
        scr = (extras.get("screening") or {}).get(disease) or {}
        base = [
            float(p.get("age") or 0), int(p.get("gender") or 0), float(p.get("bmi") or 0),
            float(p.get("sleep_hours") or 7), int(p.get("exercise_level") or 0),
            int(bool(p.get("smoking"))), int(p.get("alcohol") or 0),
            fam[0], fam[1], fam[2], fam[3],
        ]
        extra_keys = {
            "diabetes": ["freq_urination", "excess_thirst", "weight_loss"],
            "heart": ["chest_pain", "short_breath", "palpitations"],
            "hypertension": ["headaches", "dizziness", "blurred_vision"],
            "obesity": ["sugary_diet", "freq_hunger", "hard_lose_weight"],
        }.get(disease, [])
        return np.array(base + [_yn(scr.get(k)) for k in extra_keys], dtype=float)

    def _artifact_risk(self, disease: str, vec: np.ndarray):
        """Spec §9: prefer the calibrated `ml/train.py` artifact for this disease.

        Returns the predict_risk dict, or None when the artifact is missing / mismatched so the
        caller falls back to the legacy pkl ensemble.
        """
        if not has_artifact(disease):
            return None
        names = self.feature_names(disease)
        if not names or len(names) != len(vec):
            return None
        payload = dict(zip(names, [float(v) for v in vec]))
        try:
            return predict_risk(disease, payload)
        except Exception as exc:      # corrupt/old artifact → legacy path
            log.warning("predict_risk(%s) failed, falling back to pkl ensemble: %s", disease, exc)
            return None

    def predict_all(self, profile: Dict, extras: Dict) -> Dict[str, Dict]:
        """All Phase-1 diseases — per-disease vector (registry engine="disease_risk").

        Uses the trained `ml/models/<disease>.joblib` (ml/predict.py) when present; falls back to
        the legacy pkl ensemble otherwise (ML_TRAINING.md §9 + acceptance §10).
        """
        results = {}
        for disease in self.DISEASES:
            vec = self._build_vector(disease, profile, extras)

            art = self._artifact_risk(disease, vec)
            if art is not None:
                risk = art["risk"] * 100
                results[disease] = {
                    "risk_percent": round(risk, 2),
                    "category": self._get_category(risk),
                    "band": art["band"],
                    "see_doctor": art["see_doctor"],
                    "disclaimer": art["disclaimer"],
                }
                continue

            if disease not in self.models:
                continue
            predictions = []
            for name, model in self.models[disease].items():
                proba = model.predict_proba(np.array([vec]))[:, 1]
                predictions.append(ENSEMBLE_WEIGHTS.get(name, 0.0) * proba)
            ensemble_proba = float(np.sum(predictions)) * 100
            results[disease] = {
                "risk_percent": round(ensemble_proba, 2),
                "category": self._get_category(ensemble_proba),
            }
        return results

    def feature_names(self, disease: str = "diabetes") -> list:
        """SHAP labels ke liye — disease feature vector ka column order."""
        return list(PHASE1_SCHEMAS.get(disease, DISEASE_RISK_FEATURES))

    def _get_category(self, risk: float) -> str:
        for low, high, label in RISK_CATEGORIES:
            if low <= risk < high:
                return label
        return RISK_CATEGORIES[-1][2]

    def save(self, path: str = None):
        """Save all disease models."""
        import pickle
        path = path or _PKL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.models, f)
        self.is_loaded = True

    def load(self, path: str = None):
        """Load all disease models."""
        import pickle
        path = path or _PKL_PATH
        with open(path, "rb") as f:
            self.models = pickle.load(f)
        self.diseases_trained = True
        self.is_loaded = True
