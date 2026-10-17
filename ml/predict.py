# ml/predict.py
"""Single entry point for serving the ml/train.py artifacts (ML_TRAINING.md §9).

Public API (`load`, `predict_risk`) is spec-verbatim. `_artifact_path` / `has_artifact` are
additions so the engines can (a) check availability before falling back to the legacy pkl
implementation and (b) not depend on the process cwd (same BUG-1 class as the pkl paths —
`python -m ml.train` always runs from the repo root, but the API server did not).
"""
import json
import os

import joblib
import numpy as np
import pandas as pd

_cache = {}

# Spec §9 verbatim wording — every response that carries a risk also carries this.
DISCLAIMER = "Screening estimate only, not a medical diagnosis."


def _ml_dir():
    """Absolute path of this `ml/` folder — the file's own dir. Do NOT use
    `dirname(dirname(...))` here: that lands on the repo root (`<repo>/models`,
    `<repo>/reports`) which does not exist, so `threshold()`/`band_for()` silently
    returned None and the reload path (`/latest`, `/history`) lost its
    band/see_doctor/disclaimer (fixed 2026-10-15)."""
    return os.path.dirname(os.path.abspath(__file__))


def _artifact_path(name):
    rel = f"ml/models/{name}.joblib"
    if os.path.exists(rel):
        return rel
    return os.path.join(_ml_dir(), "models", f"{name}.joblib")


def has_artifact(name) -> bool:
    return os.path.exists(_artifact_path(name))


def load(name):
    if name not in _cache:
        _cache[name] = joblib.load(_artifact_path(name))
    return _cache[name]


_threshold_cache = {}


def _metrics_path(name):
    return os.path.join(_ml_dir(), "reports", f"{name}_metrics.json")


def threshold(name):
    """Calibrated F2 decision threshold (ML_TRAINING.md §7 step 5), or None if untrained.

    Read from the small `ml/reports/<name>_metrics.json` (a few KB) instead of loading the
    multi-MB joblib — the dashboard recomputes `band`/`see_doctor` for stored rows."""
    if name in _threshold_cache:
        return _threshold_cache[name]
    t = None
    path = _metrics_path(name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                t = json.load(fh).get("threshold")
        except Exception:
            t = None
    _threshold_cache[name] = t
    return t


def band_for(name, p):
    """`low|moderate|high` from the artifact threshold (spec §9), or None when untrained."""
    if not has_artifact(name):
        return None
    t = threshold(name)
    if t is None:
        return None
    return "high" if p >= t else "moderate" if p >= t * 0.5 else "low"


def predict_risk(name, payload: dict):
    art = load(name)
    cols = art["numeric"] + art["categorical"]
    row = pd.DataFrame([payload], columns=cols)      # missing keys become NaN; imputer handles them
    p = float(art["model"].predict_proba(row)[0, 1])
    t = art["threshold"]
    band = "high" if p >= t else "moderate" if p >= t * 0.5 else "low"
    return {
        "disease": name,
        "risk": round(p, 3),
        "band": band,
        "see_doctor": band == "high",
        "disclaimer": "Screening estimate only, not a medical diagnosis.",
    }


# ---------- SHAP (ML_TRAINING.md §8) ----------
def _positive_shap_values(explainer, x):
    """TreeExplainer/LGBM differ: list-of-arrays / (n, f) / (n, f, classes) → (n, f)."""
    sv = explainer.shap_values(x)
    if isinstance(sv, list):
        sv = sv[1] if len(sv) > 1 else sv[0]
    sv = np.asarray(sv)
    if sv.ndim == 3:
        sv = sv[:, :, 1]
    return sv


_explainer_cache = {}


def tree_explainer(model):
    """Cached `shap.TreeExplainer` — constructing one walks the entire ensemble, which is the
    dominant cost when many models are explained in one request (12 diseases). Cached by object
    id, which is safe because the model lives in `_cache` for the whole process lifetime.
    """
    key = id(model)
    exp = _explainer_cache.get(key)
    if exp is None:
        import shap
        exp = shap.TreeExplainer(model)
        _explainer_cache[key] = exp
    return exp


def _tree_estimator(art):
    """Pull the fitted XGB (else RF) out of the calibrated imblearn VotingClassifier pipeline."""
    cal = art["model"]
    ccs = getattr(cal, "calibrated_classifiers_", None)
    if not ccs:
        return None, None
    pipe = getattr(ccs[0], "estimator", None) or getattr(ccs[0], "base_estimator", None)
    if pipe is None or not hasattr(pipe, "named_steps"):
        return None, None
    prep = pipe.named_steps.get("prep")
    clf = pipe.named_steps.get("clf")
    named = getattr(clf, "named_estimators_", None)
    if named is None:
        named = getattr(clf, "estimators_", None)
    if isinstance(named, dict):
        tree = named.get("xgb") or named.get("random_forest")
    else:  # pragma: no cover — older sklearn keeps a list
        tree = None
    return prep, tree


def explain(name, payload: dict, top_n: int = 5):
    """SHAP explanation FROM THE SERVED ARTIFACT (so the dashboard matches predictions).

    Returns [{feature, shap_value, impact}] (|shap_value| normalised to <= 1), top-N by |value|.
    Returns [] (caller falls back to the legacy pkl explainer) when shap/the artifact layout
    is unavailable.
    """
    try:
        import shap
    except Exception:      # shap optional — dashboard degrades, inference unaffected
        return []
    art = load(name)
    prep, tree = _tree_estimator(art)
    if prep is None or tree is None:
        return []
    cols = art["numeric"] + art["categorical"]
    row = pd.DataFrame([payload], columns=cols)
    xt = prep.transform(row)
    sv = _positive_shap_values(tree_explainer(tree), xt)[0]
    names = [n.split("__", 1)[-1] for n in prep.get_feature_names_out()]

    vals = np.asarray(sv, dtype=float)
    max_abs = float(np.max(np.abs(vals))) if vals.size else 1.0
    if max_abs > 1.0:
        vals = vals / max_abs
    rows = [{"feature": names[i] if i < len(names) else f"f{i}",
             "shap_value": round(float(v), 6),
             "impact": "increases risk" if v > 0 else "decreases risk"}
            for i, v in enumerate(vals)]
    rows.sort(key=lambda r: abs(r["shap_value"]), reverse=True)
    return rows[:top_n]
