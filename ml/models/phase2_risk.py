"""Phase 2–5 Disease Risk Engine — per-disease model configs (06 §3-5, 09 §3).

8 new ML diseases ship karta hai — har disease ka apna feature schema (form/screening inputs ke
saath BUG-5-aligned), apna model stack (spec 06 "Model" per disease), apni .pkl. Registry
`engine="phase2"` entries isi engine par dispatch hote hain.

UCI note: ckd UCI real data PASS karta hai (prepare_uci.py probe: AUC 0.933); inference-time
diabetes/hypertension risk-%-se UCI ke binary dm/htn flags map ke liye `>=50 → 1` rakha hai —
training == inference columns rahe (BUG-5).
"""
import os
import pickle
import numpy as np
from typing import Dict, Any

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score
from imblearn.over_sampling import SMOTE

from ml.models.base import MLModel
from ml.models.constants import RISK_CATEGORIES
from ml.models.registry import DISEASE_REGISTRY
from ml.predict import has_artifact, predict_risk

_PKL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pkl", "phase2_diseases.pkl")


def _yn(value) -> int:
    """Yes/No answer → 0/1. Frontend "yes"/"no", bool, 1/0 — kuch bhej sakta hai; bool("no")
    True hota hai, is liye string ko explicitly handle karna zaroori hai (WS-3)."""
    if isinstance(value, str):
        return 1 if value.strip().lower() in ("yes", "y", "true", "1") else 0
    return 1 if bool(value) else 0


def _xgb():
    try:
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                             eval_metric="logloss", random_state=42, n_jobs=-1)
    except ImportError:
        return GradientBoostingClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                                          random_state=42)


# Per-disease model stacks — 06-DISEASE-MODULES.md "Model" field se (not one-size-fits-all).
# Phase-1 ensemble (RF+XGB+LR) {{"name" pair har disease ke spec flagship models}}
MODEL_STACKS = {
    "stroke": ["logistic_regression", "random_forest"],
    "ckd": ["random_forest", "xgboost"],
    "liver": ["logistic_regression", "xgboost"],
    "thyroid": ["random_forest"],
    "pcos": ["logistic_regression", "random_forest"],
    "anemia": ["decision_tree", "random_forest"],
    "colorectal": ["logistic_regression"],
    "lung_cancer": ["random_forest"],
}

_ENSEMBLE_WEIGHTS = {"random_forest": 0.40, "xgboost": 0.40,
                     "logistic_regression": 0.20, "decision_tree": 0.20}


def _stack_weights(names: list) -> dict:
    """Phase-2 stacks alag-alag size ke hain (1-2 models) — normalized weights sum=1.
    Fixed weights (0.4/0.4/0.2) sirf 3-model ensemble ke liye sum=1 karte the; single-transformer
    disease jo aaye / mari-f1 predictions-hi-nahi bug yahan tha risk% cap pe."""
    base = [max(0.0, _ENSEMBLE_WEIGHTS.get(n, 0.4)) for n in names]
    total = sum(base) or 1.0
    return {n: w / total for n, w in zip(names, base)}


def _build_estimator(name: str):
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42, n_jobs=-1)
    if name == "xgboost":
        return _xgb()
    if name == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=42, solver="lbfgs")
    if name == "decision_tree":
        return DecisionTreeClassifier(max_depth=5, random_state=42)
    raise ValueError(f"Unknown estimator: {name}")


class Phase2RiskEngine(MLModel):
    """Registry engine="phase2" — 8 diseases, per-disease features/models."""

    def __init__(self):
        super().__init__("phase2_disease_engine")
        self.models: Dict[str, Dict[str, object]] = {}

    # ── Training ───────────────────────────────────────────────────────────────
    def train_dataset(self, disease: str, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train the per-disease model stack on (X, y) — SMOTE + held-out test."""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)
        X_res, y_res = X_train, y_train
        if len(np.unique(y_train)) > 1:
            try:
                X_res, y_res = SMOTE(random_state=42).fit_resample(X_train, y_train)
            except Exception:
                X_res, y_res = X_train, y_train

        models = {}
        probas = []
        names = MODEL_STACKS.get(disease, ["random_forest"])
        weights = _stack_weights(names)
        for name in names:
            mdl = _build_estimator(name)
            mdl.fit(X_res, y_res)
            models[name] = mdl
            p = mdl.predict_proba(X_test)[:, 1]
            probas.append(weights[name] * p)

        self.models[disease] = models
        ens_proba = np.sum(probas, axis=0)
        return {
            "auc_roc": roc_auc_score(y_test, ens_proba) if len(np.unique(y_test)) > 1 else 0.0,
            "macro_f1": f1_score(y_test, (ens_proba >= 0.5).astype(int), average="macro"),
            "n_models": len(names),
        }

    # ── Inference ──────────────────────────────────────────────────────────────
    def _artifact_risk(self, disease: str, vec: np.ndarray):
        """Spec §9: prefer the calibrated `ml/train.py` artifact; None → legacy pkl stack."""
        if not has_artifact(disease):
            return None
        names = self._FEATURE_NAMES.get(disease, [])
        if not names or len(names) != len(vec):
            return None
        payload = dict(zip(names, [float(v) for v in vec]))
        try:
            return predict_risk(disease, payload)
        except Exception as exc:      # corrupt/old artifact → legacy path
            import logging
            logging.getLogger(__name__).warning(
                "predict_risk(%s) failed, falling back to pkl stack: %s", disease, exc)
            return None

    def predict(self, disease: str, profile: Dict[str, Any], extras: Dict[str, Any]) -> Dict[str, Any]:
        """Per-disease risk from profile dict + extras (e.g. ckd ke diabetes/hypertension risks).

        Ineligible pe `None` → orchestrator skip karega (disease_risk_results row nahi banegi).
        Trained `ml/models/<disease>.joblib` ho to wahi use hota hai (ML_TRAINING.md §9),
        warna legacy per-disease pkl stack pe fallback.
        """
        if disease not in self._FEATURE_NAMES:
            return None
        if not self._eligible(disease, profile):
            return None
        vec = self._build_vector(disease, profile, extras)

        art = self._artifact_risk(disease, vec)
        if art is not None:
            risk = art["risk"] * 100
            return {
                "risk_percent": round(risk, 2),
                "risk_label": self._category(risk),
                "confidence": art["risk"],
                "band": art["band"],
                "see_doctor": art["see_doctor"],
                "disclaimer": art["disclaimer"],
            }

        if disease not in self.models:
            return None
        names = list(self.models[disease].keys())
        weights = _stack_weights(names)
        probas = []
        for name in names:
            p = self.models[disease][name].predict_proba(np.array([vec]))[:, 1]
            probas.append(weights[name] * p)
        risk = float(np.sum(probas)) * 100
        return {
            "risk_percent": round(risk, 2),
            "risk_label": self._category(risk),
            "confidence": round(float(np.sum(probas)), 4),
        }

    def _eligible(self, disease: str, profile: Dict[str, Any]) -> bool:
        """Registry-driven inference gates (06-DISEASE-MODULE: pcos female-only, colorectal 40+).

        Training data dono cases cover karta tha; serving pe filter — ineligible user ke liye
        risk row hi nahi banti (05-API-SPEC §9: array mein sirf chalayi gayi diseases).
        """
        cfg = DISEASE_REGISTRY.get(disease)
        if cfg is None:
            return True
        if cfg.requires_gender is not None and int(profile.get("gender") or 0) != cfg.requires_gender:
            return False
        if cfg.min_age and float(profile.get("age") or 0) < cfg.min_age:
            return False
        return True

    def _category(self, risk: float) -> str:
        for low, high, label in RISK_CATEGORIES:
            if low <= risk < high:
                return label
        return RISK_CATEGORIES[-1][2]

    def _build_vector(self, disease: str, p: Dict[str, Any], extras: Dict[str, Any]) -> np.ndarray:
        """Profile+screening → disease feature vector (BUG-5: training columns ke order mein)."""
        fam = p.get("family_history", [0, 0, 0, 0])
        gender = int(p.get("gender") or 0)
        bmi = float(p.get("bmi") or 0)
        age = float(p.get("age") or 0)
        smoking = int(bool(p.get("smoking")))
        alcohol = int(p.get("alcohol") or 0)
        exercise = int(p.get("exercise_level") or 0)
        bp_sys = float(p.get("bp_systolic") or 118)
        bp_dia = float(p.get("bp_diastolic") or 76)

        if disease == "stroke":
            scr = extras.get("screening", {}).get("stroke", {})
            return np.array([age, gender, bmi, p.get("sleep_hours", 7), exercise,
                             smoking, alcohol, fam[0], fam[1], fam[2], fam[3],
                             bp_sys, bp_dia,
                             _yn(scr.get("tia_symptoms")), _yn(scr.get("speech_difficulty")),
                             _yn(scr.get("irregular_heartbeat"))])
        if disease == "ckd":
            # UCI real dm/htn binary — inference `diabetes_risk>=50 → 1` (model card note)
            dia_flag = 1 if float(extras.get("diabetes_risk") or 0) >= 50 else 0
            htn_flag = 1 if float(extras.get("hypertension_risk") or 0) >= 50 else 0
            scr = extras.get("screening", {}).get("ckd", {})
            return np.array([age, bp_sys, dia_flag, htn_flag,
                             _yn(scr.get("ankle_swelling")), _yn(scr.get("urination_changes")),
                             _yn(scr.get("ckd_fatigue"))])
        if disease == "liver":
            scr = extras.get("screening", {}).get("liver", {})
            return np.array([age, gender, bmi, alcohol,
                             _yn(scr.get("jaundice")), _yn(scr.get("abdominal_pain")),
                             _yn(scr.get("liver_fatigue"))])
        if disease == "thyroid":
            scr = extras.get("screening", {}).get("thyroid", {})
            fatigue = _yn(scr.get("fatigue"))
            return np.array([age, gender, bmi, fatigue,
                             _yn(scr.get("weight_change")), _yn(scr.get("temperature_issues")),
                             _yn(scr.get("hair_skin"))])
        if disease == "pcos":
            scr = extras.get("screening", {}).get("pcos", {})
            irr = _yn(scr.get("irregular_periods"))
            gain = _yn(scr.get("weight_gain"))
            return np.array([age, bmi, irr, gain,
                             _yn(scr.get("excess_hair")), _yn(scr.get("acne"))])
        if disease == "anemia":
            scr = extras.get("screening", {}).get("anemia", {})
            diet = {"good": 0, "average": 1, "poor": 2}.get(str(p.get("diet_quality", "average")).lower(), 1)
            fat = _yn(scr.get("frequent_fatigue"))
            pale = _yn(scr.get("pale_cold"))
            return np.array([gender, age, diet, fat, pale,
                             _yn(scr.get("lightheadedness")), _yn(scr.get("brittle_nails"))])
        if disease == "colorectal":
            scr = extras.get("screening", {}).get("colorectal", {})
            diet = {"good": 0, "average": 1, "poor": 2}.get(str(p.get("diet_quality", "average")).lower(), 1)
            return np.array([age, fam[3], diet, exercise, smoking, alcohol,
                             _yn(scr.get("blood_in_stool")), _yn(scr.get("bowel_change")),
                             _yn(scr.get("colorectal_weight_loss"))])
        if disease == "lung_cancer":
            scr = extras.get("screening", {}).get("lung_cancer_exposure", {})
            passive = _yn(scr.get("passive_smoke"))
            return np.array([smoking, passive, age, fam[3],
                             _yn(scr.get("persistent_cough")), _yn(scr.get("coughing_blood")),
                             _yn(scr.get("breath_shortness"))])
        raise ValueError(f"No vector builder for {disease}")

    _FEATURE_NAMES = {
        "stroke": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking", "alcohol",
                   "family_diabetes", "family_heart", "family_hypertension", "family_cancer",
                   "bp_systolic", "bp_diastolic", "tia_symptoms", "speech_difficulty",
                   "irregular_heartbeat"],
        "ckd": ["age", "bp_systolic", "diabetes_flag", "hypertension_flag", "ankle_swelling",
                "urination_changes", "ckd_fatigue"],
        "liver": ["age", "gender", "bmi", "alcohol", "jaundice", "abdominal_pain", "liver_fatigue"],
        "thyroid": ["age", "gender", "bmi", "fatigue", "weight_change", "temperature_issues",
                    "hair_skin"],
        "pcos": ["age", "bmi", "irregular_periods", "weight_gain", "excess_hair", "acne"],
        "anemia": ["gender", "age", "diet_quality", "frequent_fatigue", "pale_cold",
                   "lightheadedness", "brittle_nails"],
        "colorectal": ["age", "family_cancer", "diet_quality", "exercise_level", "smoking",
                       "alcohol", "blood_in_stool", "bowel_change", "colorectal_weight_loss"],
        "lung_cancer": ["smoking", "passive_smoke", "age", "family_cancer", "persistent_cough",
                        "coughing_blood", "breath_shortness"],
    }

    def feature_names(self, disease: str) -> list:
        """SHAP labels ke liye — `_build_vector` ke column order (model cards se aligned)."""
        return list(self._FEATURE_NAMES.get(disease, []))

    # ── MLModel interface ──────────────────────────────────────────────────────
    def train(self, X, y):
        return {"auc_roc": 0.0, "macro_f1": 0.0, "n_models": 0}

    def evaluate(self, X_test, y_test) -> Dict[str, float]:
        return {}

    def predict_proba(self, X):
        raise NotImplementedError("Use predict(disease, profile, extras)")

    def save(self, path: str = None):
        path = path or _PKL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.models, f)
        self.is_loaded = True

    def load(self, path: str = None):
        path = path or _PKL_PATH
        with open(path, "rb") as f:
            self.models = pickle.load(f)
        self.is_loaded = True