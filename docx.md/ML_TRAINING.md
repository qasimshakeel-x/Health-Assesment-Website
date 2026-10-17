# ML Training Guide: AI Longevity Intelligence Platform

> **Audience:** the coding agent building and training the disease-risk models.
> **Goal:** replace the synthetic-data training with a **real-data, leakage-free, honestly evaluated** pipeline that works for every ML-based disease, using one config-driven script.

---

## 1. Ground Rules (read first, do not skip)

1. **Real data only for training.** `generate_datasets.py` (synthetic) may stay in the repo for unit tests and smoke tests, but **no production model is trained on synthetic data**. If a disease has no usable real dataset, mark it `NO_REAL_DATA` and keep its current rule-based or old model, clearly labelled.
2. **Split first, resample later.** Train/test split happens before anything else. SMOTE lives **inside the pipeline** so it only touches training folds. Never apply SMOTE to the test set or before the split.
3. **The test set is touched once**, at the very end, for the final report. Never tune on it.
4. **Never force a pass.** The old gates (AUC >= 0.85, macro F1 >= 0.80) are **targets, not requirements**. If a disease does not reach them on real data, report the true numbers with status `BELOW_TARGET`. Do not lower thresholds silently, do not leak labels, do not tune on the test set to hit a number.
5. **Suspiciously high score = bug until proven otherwise.** Test AUC above 0.97 must raise the flag `SUSPICIOUS_POSSIBLE_LEAKAGE` and be investigated (leaky column, duplicated rows, label encoded in a feature).
6. **Features must be available in the app.** Only train on inputs a user can realistically enter (age, BMI, BP, lab values they have, lifestyle answers). No diagnosis columns, no columns derived from the label.
7. **This is a screening tool, not a diagnosis tool.** Every API response that contains a risk must be able to carry a disclaimer and a `see_doctor` flag.
8. **Do not break the existing API contract.** Keep `DiseaseRiskEngine`, `Phase2RiskEngine`, `DepressionClassifier` public interfaces; only swap their internals to load the new artifacts.

---

## 2. Scope

| Group | Diseases | Approach |
|---|---|---|
| `DiseaseRiskEngine` | diabetes, heart, hypertension, obesity | RF + XGBoost + Logistic Regression soft-voting ensemble, weights 0.40 / 0.40 / 0.20 |
| `Phase2RiskEngine` | stroke, ckd, liver, thyroid, pcos, anemia, colorectal, lung_cancer | same ensemble |
| `DepressionClassifier` | depression (PHQ-9) | same pipeline (Gradient Boosting may be kept as a 4th option, compare via CV) |
| **Rule-based, do not train** | gad7, sleep_apnea, metabolic_syndrome, burnout | keep as is |

---

## 3. Environment

Local machine or free Google Colab is enough. **No GPU needed** (tabular data).

```bash
pip install pandas numpy scikit-learn xgboost imbalanced-learn shap optuna joblib matplotlib pyyaml
```

Add these to `requirements.txt` / `ml/requirements.txt`.

---

## 4. Folder Structure

```
ml/
  __init__.py
  train.py                 # the single training script (Section 7)
  train_config.py          # per-disease config (Section 6)
  predict.py               # inference helper (Section 9)
  data/
    real/                  # real datasets (CSV), one per disease
    README.md              # source, URL, license, date downloaded for every file
  models/
    <disease>.joblib       # trained artifact
  reports/
    <disease>_metrics.json
    <disease>_shap.png
    SUMMARY.md             # auto-generated table of all diseases
```

`ml/data/README.md` must list, for every dataset: name, source URL, license, number of rows, download date. This feeds the FYP report.

---

## 5. Datasets

Candidate sources (**verify availability, license and column names before use**; do not assume):

| Disease | Candidate real data | Notes |
|---|---|---|
| diabetes | Pima Indians Diabetes (UCI/Kaggle); NHANES | Pima is small and one population; zeros in Glucose, BP, SkinThickness, Insulin, BMI mean "missing" |
| heart | UCI Heart Disease (Cleveland); Framingham; BRFSS | check which columns are app-available |
| hypertension | NHANES (blood pressure readings) | label from BP thresholds: do **not** also use BP as a feature |
| obesity | NHANES (BMI) | label from BMI: do **not** use BMI/weight/height as features if the label is derived from them |
| ckd | UCI Chronic Kidney Disease | small; contains `?` as missing; some columns have stray whitespace/tabs |
| liver | Indian Liver Patient Dataset (UCI); NHANES | |
| thyroid | UCI Thyroid; NHANES | |
| anemia | NHANES (hemoglobin) | same label-from-feature caution as above |
| depression | NHANES PHQ-9 | |
| stroke | Kaggle stroke dataset; BRFSS | strongly imbalanced |
| pcos, colorectal, lung_cancer | Kaggle datasets | often tiny; some are synthetic. Flag `SMALL_DATASET`; do not trust high scores |

If a candidate dataset is itself synthetic, SMOTE-generated, or under ~500 rows, say so in `ml/data/README.md` and in the metrics flags.

**Label-from-feature trap:** if the target is defined by a threshold on a column (e.g. hypertension from systolic BP, obesity from BMI, anemia from hemoglobin), that column **must be excluded from the features**, otherwise the model just rediscovers the rule and the score is meaningless.

---

## 6. Config: `ml/train_config.py`

One entry per disease. Adding a disease = adding one entry.

```python
# ml/train_config.py
TARGET_AUC = 0.85
TARGET_MACRO_F1 = 0.80
SEED = 42

DISEASES = {
    "diabetes": {
        "data": "ml/data/real/diabetes.csv",
        "target": "Outcome",
        "target_map": None,                      # or {"ckd": 1, "notckd": 0}
        "numeric": ["Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
                    "Insulin", "BMI", "DiabetesPedigreeFunction", "Age"],
        "categorical": [],
        "zero_is_missing": ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"],
        "source_note": "Pima Indians Diabetes",
    },
    "ckd": {
        "data": "ml/data/real/ckd.csv",
        "target": "class",
        "target_map": {"ckd": 1, "notckd": 0},
        "numeric": ["age", "bp", "sg", "al", "su", "bgr", "bu", "sc",
                    "sod", "pot", "hemo", "pcv", "wc", "rc"],
        "categorical": ["htn", "dm", "cad", "appet", "pe", "ane"],
        "zero_is_missing": [],
        "source_note": "UCI Chronic Kidney Disease",
    },
    # Add the remaining diseases the same way.
    # Inspect each CSV first (df.head(), df.dtypes, df.isna().mean(), target value counts)
    # and only then write numeric/categorical lists. Do not guess column names.
}
```

Config keys:

| Key | Meaning |
|---|---|
| `data` | CSV path |
| `target` | target column |
| `target_map` | map string labels to 0/1 (or `None` if already 0/1) |
| `numeric` / `categorical` | feature lists (only app-available features) |
| `zero_is_missing` | numeric columns where 0 really means missing |
| `source_note` | free text for the report |

---

## 7. Training Script: `ml/train.py`

Run: `python -m ml.train --disease diabetes` or `python -m ml.train --all`
Optional: `--trials 30` for Optuna tuning (default 0 = no tuning).

```python
# ml/train.py
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import shap
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (brier_score_loss, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import (StratifiedKFold, cross_val_predict,
                                     cross_val_score, train_test_split)
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from ml.train_config import DISEASES, SEED, TARGET_AUC, TARGET_MACRO_F1

MODELS_DIR = Path("ml/models")
REPORTS_DIR = Path("ml/reports")
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------- data ----------
def load_data(cfg):
    df = pd.read_csv(cfg["data"], na_values=["?", "", "NA", "nan"], skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan})

    y = df[cfg["target"]]
    if cfg.get("target_map"):
        y = y.map(cfg["target_map"])
    keep = y.notna()
    df, y = df[keep], y[keep].astype(int)

    feats = cfg["numeric"] + cfg.get("categorical", [])
    X = df[feats].copy()
    for c in cfg["numeric"]:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    for c in cfg.get("zero_is_missing", []):
        X.loc[X[c] == 0, c] = np.nan
    return X, y


# ---------- model ----------
def make_preprocessor(cfg):
    transformers = [("num", SkPipeline([("imp", SimpleImputer(strategy="median")),
                                        ("sc", StandardScaler())]), cfg["numeric"])]
    if cfg.get("categorical"):
        transformers.append(("cat", SkPipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
            cfg["categorical"]))
    return ColumnTransformer(transformers)


def build_model(cfg, params=None, n_min=50):
    p = {"rf_n": 300, "rf_depth": None, "xgb_n": 300, "xgb_depth": 4,
         "xgb_lr": 0.05, "lr_C": 1.0}
    p.update(params or {})
    ens = VotingClassifier(
        [("rf", RandomForestClassifier(n_estimators=p["rf_n"], max_depth=p["rf_depth"],
                                       class_weight="balanced", random_state=SEED, n_jobs=-1)),
         ("xgb", XGBClassifier(n_estimators=p["xgb_n"], max_depth=p["xgb_depth"],
                               learning_rate=p["xgb_lr"], eval_metric="logloss",
                               random_state=SEED, n_jobs=-1)),
         ("lr", LogisticRegression(C=p["lr_C"], max_iter=2000, class_weight="balanced"))],
        voting="soft", weights=[0.4, 0.4, 0.2])
    k = max(1, min(5, int(n_min * 0.6) - 1))
    return ImbPipeline([("prep", make_preprocessor(cfg)),
                        ("smote", SMOTE(k_neighbors=k, random_state=SEED)),
                        ("clf", ens)])


def tune(cfg, X, y, n_min, n_trials):
    cv = StratifiedKFold(3, shuffle=True, random_state=SEED)

    def objective(trial):
        params = {
            "rf_n": trial.suggest_int("rf_n", 150, 500),
            "rf_depth": trial.suggest_int("rf_depth", 3, 14),
            "xgb_n": trial.suggest_int("xgb_n", 150, 500),
            "xgb_depth": trial.suggest_int("xgb_depth", 2, 7),
            "xgb_lr": trial.suggest_float("xgb_lr", 0.01, 0.2, log=True),
            "lr_C": trial.suggest_float("lr_C", 0.01, 10, log=True),
        }
        return cross_val_score(build_model(cfg, params, n_min), X, y,
                               cv=cv, scoring="roc_auc").mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=n_trials)
    return study.best_params


# ---------- explainability ----------
def shap_report(cfg, X_tr, y_tr, name):
    """Proxy importance: XGBoost alone on the preprocessed training data."""
    prep = make_preprocessor(cfg)
    Xt = prep.fit_transform(X_tr)
    names = [n.split("__", 1)[-1] for n in prep.get_feature_names_out()]
    xgb = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                        eval_metric="logloss", random_state=SEED).fit(Xt, y_tr)
    sv = shap.TreeExplainer(xgb).shap_values(Xt)
    imp = np.abs(sv).mean(axis=0)
    top = sorted(zip(names, imp), key=lambda t: -t[1])[:10]
    plt.figure(figsize=(6, 4))
    plt.barh([t[0] for t in top][::-1], [float(t[1]) for t in top][::-1])
    plt.title(f"{name}: mean |SHAP| (top 10)")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / f"{name}_shap.png", dpi=120)
    plt.close()
    return {n: round(float(v), 4) for n, v in top}


# ---------- main ----------
def train(name, trials=0):
    cfg = DISEASES[name]
    X, y = load_data(cfg)
    flags = []
    if len(y) < 500:
        flags.append("SMALL_DATASET")
    if y.mean() < 0.10 or y.mean() > 0.90:
        flags.append("HEAVY_IMBALANCE")

    # 1) split FIRST
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)
    n_min = int(y_tr.value_counts().min())

    # 2) optional tuning (training data only)
    params = tune(cfg, X_tr, y_tr, n_min, trials) if trials > 0 else {}

    # 3) cross-validation on training data
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    cv_scores = cross_val_score(build_model(cfg, params, n_min), X_tr, y_tr,
                                cv=cv, scoring="roc_auc", n_jobs=-1)

    # 4) calibrated final model (SMOTE stays inside the pipeline)
    model = CalibratedClassifierCV(build_model(cfg, params, n_min),
                                   method="sigmoid", cv=cv)

    # 5) decision threshold from out-of-fold predictions (favours recall, F2)
    oof = cross_val_predict(model, X_tr, y_tr, cv=cv, method="predict_proba")[:, 1]
    prec, rec, thr = precision_recall_curve(y_tr, oof)
    f2 = (5 * prec * rec) / (4 * prec + rec + 1e-9)
    threshold = float(thr[int(np.argmax(f2[:-1]))])

    # 6) fit on all training data, evaluate ONCE on the untouched test set
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= threshold).astype(int)

    test_auc = float(roc_auc_score(y_te, proba))
    macro_f1 = float(f1_score(y_te, pred, average="macro"))
    if test_auc > 0.97:
        flags.append("SUSPICIOUS_POSSIBLE_LEAKAGE")
    status = "PASS" if (test_auc >= TARGET_AUC and macro_f1 >= TARGET_MACRO_F1) else "BELOW_TARGET"

    metrics = {
        "disease": name,
        "dataset": cfg.get("source_note", cfg["data"]),
        "rows": int(len(y)),
        "positive_rate": round(float(y.mean()), 4),
        "features": cfg["numeric"] + cfg.get("categorical", []),
        "cv_auc_mean": round(float(cv_scores.mean()), 4),
        "cv_auc_std": round(float(cv_scores.std()), 4),
        "test_auc": round(test_auc, 4),
        "test_recall": round(float(recall_score(y_te, pred)), 4),
        "test_precision": round(float(precision_score(y_te, pred, zero_division=0)), 4),
        "test_macro_f1": round(macro_f1, 4),
        "brier_score": round(float(brier_score_loss(y_te, proba)), 4),
        "threshold": round(threshold, 4),
        "targets": {"auc": TARGET_AUC, "macro_f1": TARGET_MACRO_F1},
        "status": status,
        "flags": flags,
        "top_features_shap": shap_report(cfg, X_tr, y_tr, name),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    joblib.dump({"model": model, "numeric": cfg["numeric"],
                 "categorical": cfg.get("categorical", []),
                 "threshold": threshold, "meta": metrics},
                MODELS_DIR / f"{name}.joblib")
    (REPORTS_DIR / f"{name}_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"[{name}] AUC={test_auc:.3f} recall={metrics['test_recall']:.3f} "
          f"F1={macro_f1:.3f} -> {status} {flags}")
    return metrics


def write_summary(all_metrics):
    lines = ["# Training Summary", "",
             "| Disease | Rows | CV AUC | Test AUC | Recall | Macro F1 | Status | Flags |",
             "|---|---|---|---|---|---|---|---|"]
    for m in all_metrics:
        lines.append(f"| {m['disease']} | {m['rows']} | {m['cv_auc_mean']} | {m['test_auc']} | "
                     f"{m['test_recall']} | {m['test_macro_f1']} | {m['status']} | "
                     f"{', '.join(m['flags']) or '-'} |")
    (REPORTS_DIR / "SUMMARY.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--disease")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--trials", type=int, default=0)
    a = ap.parse_args()
    names = list(DISEASES) if a.all else [a.disease]
    results = [train(n, a.trials) for n in names]
    write_summary(results)
```

**Why it is built this way**

| Step | Reason |
|---|---|
| Split before anything else | prevents leakage |
| SMOTE inside `ImbPipeline` | resamples only training folds, so CV scores are honest |
| Imputer + scaler inside the pipeline | fitted on training folds only |
| Sigmoid calibration | "70% risk" should mean roughly 70% (isotonic needs more data; use it only for large datasets) |
| Threshold from out-of-fold F2 | missing a high-risk person is worse than a false alarm |
| SHAP | sanity check: if one odd feature dominates, suspect leakage |
| Metrics JSON + SUMMARY.md | feeds the FYP report with real, reproducible numbers |

---

## 8. Execution Order

1. Create the folders, `ml/__init__.py`, `ml/train_config.py`, `ml/train.py`.
2. Put the **diabetes** CSV in `ml/data/real/`, add its config, run `python -m ml.train --disease diabetes`.
3. Confirm the pipeline works end to end (artifact, metrics JSON, SHAP image created). Fix bugs here before scaling out.
4. Add **ckd**, then the lab-based diseases (anemia, thyroid, liver), then heart, hypertension, obesity, stroke, depression, then the small-dataset ones (pcos, colorectal, lung_cancer).
5. For each disease: inspect the CSV, check the label-from-feature trap, write the config, train, read the flags.
6. Optionally re-run with `--trials 30` to tune; keep the tuned model only if the **CV AUC** improves (never judge by test AUC).
7. Run `python -m ml.train --all` and commit `ml/reports/SUMMARY.md`.

---

## 9. Inference: `ml/predict.py`

```python
# ml/predict.py
import joblib
import pandas as pd

_cache = {}

def load(name):
    if name not in _cache:
        _cache[name] = joblib.load(f"ml/models/{name}.joblib")
    return _cache[name]

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
```

Integration notes:
- `DiseaseRiskEngine` / `Phase2RiskEngine` / `DepressionClassifier` should call `predict_risk` internally and keep returning the same response shape the API already uses (add `band`, `see_doctor`, `disclaimer` if missing).
- **Doctor referral is decided in code** from `band`, the number of high-risk diseases, and red-flag inputs. The diet/exercise chatbot (LLM) only **explains** that decision; it never makes it.
- If a disease model file is missing, fall back to the existing implementation and log a warning.

---

## 10. Acceptance Criteria (Definition of Done)

For **each** ML disease:

- [ ] Trained on a real dataset listed in `ml/data/README.md` (source, license, rows, date)
- [ ] Label-from-feature columns excluded; no leakage columns
- [ ] Split before SMOTE; SMOTE only inside the pipeline
- [ ] 5-fold CV AUC (mean and std), plus test AUC, recall, precision, macro F1, Brier score in `<disease>_metrics.json`
- [ ] Calibrated probabilities and a stored decision threshold
- [ ] SHAP top-10 saved; no suspicious dominant feature
- [ ] `status` is `PASS` or an honest `BELOW_TARGET`; every flag recorded
- [ ] Artifact saved at `ml/models/<disease>.joblib`
- [ ] Engine class loads the artifact and returns the usual response plus `band`, `see_doctor`, `disclaimer`

Global:

- [ ] `python -m ml.train --all` runs clean and writes `ml/reports/SUMMARY.md`
- [ ] A smoke test calls `predict_risk` for every trained disease with a sample payload
- [ ] Rule-based modules (gad7, sleep_apnea, metabolic_syndrome, burnout) untouched

---

## 11. Expected Results (set honest expectations)

- On real public data, **AUC 0.75 to 0.88 is normal.** Lab-based diseases (CKD, anemia, thyroid, diabetes) usually score higher; small Kaggle datasets (PCOS, lung cancer, colorectal) are less reliable.
- Public datasets are small and from specific populations (for example Pima is a single population), so performance on other populations, including Pakistani users, may differ. State this as a limitation.
- Do not chase 0.95+ AUC. It almost always means leakage, duplicates or a synthetic dataset.

---

## 12. Report Template (for the FYP / documentation)

For each disease write: dataset name and source, number of rows, positive rate, features used, preprocessing, CV and test metrics, top SHAP features, flags, and limitations. State clearly that the system is a **screening and awareness tool, not a diagnostic device**, and that models should be revalidated on local clinical data before any real-world use.

---

## 13. Troubleshooting

| Problem | Likely cause / fix |
|---|---|
| `ValueError: Expected n_neighbors <= n_samples` in SMOTE | too few minority samples; `k_neighbors` is auto-reduced, but if the minority class has under ~10 rows, skip SMOTE and rely on `class_weight` |
| Test AUC > 0.97 | leakage, duplicated rows, label derived from a feature, or synthetic data. Investigate before accepting |
| Big gap between CV AUC and test AUC | dataset too small / lucky split; report both, try repeated CV |
| `KeyError` on a column | column names differ or have whitespace; inspect `df.columns` and fix the config |
| Calibration error on tiny data | use `cv=3`, or drop calibration for that disease and note it in flags |
| Very slow run | lower `--trials`, or reduce `n_estimators`; nested CV (threshold + calibration) is the heavy part |
