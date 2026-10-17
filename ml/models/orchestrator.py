"""ML Pipeline Orchestrator — Facade pattern, single entrypoint for all ML inference."""
import warnings
import numpy as np
from typing import Dict, Any, Optional
from ml.models.disease_risk import DiseaseRiskEngine
from ml.models.phase2_risk import Phase2RiskEngine
from ml.models.screening_classifier import ScreeningClassifier
from ml.models.bio_age import BioAgeEngine
from ml.models.longevity_score import LongevityScoreEngine
from ml.models.depression import DepressionClassifier
from ml.models.registry import DISEASE_REGISTRY
from ml.predict import has_artifact, explain as explain_artifact, tree_explainer

# sklearn joblib ThreadingBackend har predict pe ye harmless warning deta hai (log spam ho
# jata hai — 1.7MB). Sirf is specific message ko suppress karo — ML inference kuch bhi
# affect nahi hota (sirf warning hai, model kaam wahi karta hai).
warnings.filterwarnings(
    "ignore",
    message=r".*sklearn\.utils\.parallel\.delayed.*",
    category=UserWarning,
)


class MLPipelineOrchestrator:
    """Single entrypoint that coordinates all ML modules."""

    def __init__(self):
        self.disease_engine = DiseaseRiskEngine()
        self.phase2_engine = Phase2RiskEngine()
        self.screen_engine = ScreeningClassifier()
        self.bio_age_engine = BioAgeEngine()
        self.longevity_engine = LongevityScoreEngine()
        self.depression_classifier = DepressionClassifier()
        self.models_loaded = False

    def load_models(self):
        """Load all pre-trained models. Called once at FastAPI startup."""
        self.disease_engine.load()
        self.phase2_engine.load()
        self.bio_age_engine = BioAgeEngine()  # Formula-based, no persistence needed
        self.longevity_engine = LongevityScoreEngine()  # Formula-based
        self.depression_classifier.load()
        self.models_loaded = True

    def run_pipeline(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full pipeline. Returns complete results dict (16-disease registry)."""
        if not self.models_loaded:
            raise RuntimeError("Models not loaded")

        # Normalized profile — bmi computed if missing (phase-2 engines bmi pe depend karte hain)
        norm_profile = dict(profile_data)
        norm_profile.setdefault("bmi", self._compute_bmi(profile_data["height"], profile_data["weight"]))

        screening = profile_data.get("screening_responses", {})
        extras = {"screening": screening}

        # Phase-1 per-disease vectors (base 11 + har disease ke screening questions, WS-7)
        raw_results = self.disease_engine.predict_all(norm_profile, extras)

        # Phase-2/5 engines ko pipeline outputs + screening responses
        extras["diabetes_risk"] = raw_results.get("diabetes", {}).get("risk_percent", 0)
        extras["hypertension_risk"] = raw_results.get("hypertension", {}).get("risk_percent", 0)

        # Registry-driven dispatch (02-ARCHITECTURE §5) — engine per disease, wave-graph:
        # depends_on vars (diabetes/hypertension) phase-1 se compute kar liye (ckd).
        disease_results = {}
        for key, cfg in DISEASE_REGISTRY.items():
            if not cfg.active:
                continue
            if cfg.engine == "disease_risk" and key in raw_results:
                item = dict(raw_results[key])
                # Phase-1 engine ka "category" raw risk label hai ("Very High Risk") → risk_label
                item["risk_label"] = item.pop("category", None)
                item["disease_key"] = key
                item["label"] = cfg.label
                item["category"] = cfg.category
                item["confidence"] = None
                disease_results[key] = item
            elif cfg.engine == "phase2":
                out = self.phase2_engine.predict(key, norm_profile, extras)
                if out is None:
                    continue
                out["disease_key"] = key
                out["label"] = cfg.label
                out["category"] = cfg.category
                disease_results[key] = out
            elif cfg.engine == "screening":
                rule_results = self.screen_engine.predict_all(norm_profile, extras["screening"])
                if key in rule_results:
                    item = dict(rule_results[key])
                    item["disease_key"] = key
                    item["label"] = cfg.label
                    item["category"] = cfg.category
                    disease_results[key] = item

        # Average disease risk (flat across active) for bio age and longevity calculations
        avg_risk = np.mean([d["risk_percent"] for d in disease_results.values()]) \
            if disease_results else 0.0

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

        # SHAP per ML disease (12: 4 phase1 + 8 phase2) — har disease apna model + apna
        # feature vector (rule-based gad7/burnout/sleep_apnea/metabolic_syndrome ka model nahi).
        shap_all = self.compute_shap_all(norm_profile, extras, list(disease_results.keys()))

        return {
            "disease_risks": disease_results,
            "biological_age": bio_age,
            "longevity_score": longevity,
            "depression": depression_result,
            "shap_explanations": shap_all,
            "avg_disease_risk": round(float(avg_risk), 2)
        }

    def build_feature_vector(self, data: Dict) -> list:
        return self._build_feature_vector(data)

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
        """Legacy single-vector SHAP (diabetes) — production path compute_shap_all() hai."""
        return self._compute_shap_for("diabetes", self.disease_engine, feature_vector,
                                      self.disease_engine.feature_names("diabetes"))

    def compute_shap_all(self, profile: Dict, extras: Dict, disease_keys: list) -> Dict[str, list]:
        """Per-disease SHAP — sab ML diseases ke apne models + feature vectors se.

        Rule-based diseases (gad7/burnout/sleep_apnea/metabolic_syndrome) ka koi sklearn
        model nahi → SHAP nahi banta (wo scoring hain). Output: {disease_key: [top-5 rows]}.
        """
        out: Dict[str, list] = {}
        for disease in disease_keys:
            models = None
            engine = None
            if disease in self.disease_engine.models:
                engine = self.disease_engine
                models = self.disease_engine.models[disease]
            elif disease in self.phase2_engine.models:
                engine = self.phase2_engine
                models = self.phase2_engine.models[disease]
            if engine is None or models is None:
                continue
            try:
                vec = engine._build_vector(disease, profile, extras)
                names = engine.feature_names(disease)
                # Prefer the trained artifact so the dashboard explains the model that
                # actually produced the prediction (ML_TRAINING.md §7-8). Falls back to the
                # legacy pkl stack for diseases with no artifact (e.g. colorectal NO_REAL_DATA).
                rows = []
                if has_artifact(disease) and names and len(names) == len(vec):
                    payload = dict(zip(names, [float(v) for v in vec]))
                    try:
                        rows = explain_artifact(disease, payload)
                    except Exception:
                        # Artifact unreadable in this process (e.g. MemoryError on a small-RAM
                        # box) — fall through to the legacy path instead of silently dropping
                        # this disease's explanation.
                        rows = []
                if not rows:
                    rows = self._compute_shap_for(disease, engine, list(vec),
                                                  engine.feature_names(disease))
                if rows:
                    out[disease] = rows
            except Exception:
                continue
        return out

    def _compute_shap_for(self, disease: str, engine, feature_vector: list,
                          feature_names: list) -> list:
        """Disease-specific SHAP: tree models → TreeExplainer, sirf LR (colorectal) →
        LinearExplainer. NOTE 3D ndarray + [-1,1] normalize wahi hai jo diabetes wala path.

        NOTE: +1 — TreeExplainer tree models ke liye correct hai (RF/XGBoost/DT/GB),
        Linear sharten sirf LR stacks ke liye (phase-2 colorectal).
        """
        try:
            import shap
            models = getattr(engine, "models", {}).get(disease, {})
            if not models:
                return []
            row = np.array([feature_vector])

            tree_model = None
            for name in ("random_forest", "xgboost", "decision_tree", "gradient_boosting"):
                if name in models:
                    tree_model = models[name]
                    break
            if tree_model is not None:
                explainer = tree_explainer(tree_model)
                shap_vals = explainer.shap_values(row)
            else:
                lr = models.get("logistic_regression")
                if lr is None:
                    return []
                explainer = shap.LinearExplainer(lr, row)
                shap_vals = explainer.shap_values(row)

            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1] if len(shap_vals) > 1 else shap_vals[0]
            elif getattr(shap_vals, "ndim", 0) == 3:
                shap_vals = shap_vals[:, :, 1]

            shap_vals = np.asarray(shap_vals)[0]

            # Normalize to [-1, 1] — DB CHECK constraint + frontend width scale
            max_abs = float(np.max(np.abs(shap_vals))) if shap_vals.size else 1.0
            if max_abs > 1.0:
                shap_vals = shap_vals / max_abs

            results = []
            for i, name in enumerate(feature_names):
                val = float(shap_vals[i]) if i < len(shap_vals) else 0.0
                results.append({
                    "feature": name,
                    "shap_value": round(val, 6),
                    "impact": "increases risk" if val > 0 else "decreases risk"
                })
            results.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            return results[:5]
        except Exception:
            return []
