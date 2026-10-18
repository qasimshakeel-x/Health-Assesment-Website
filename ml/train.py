"""ml/train.py — single config-driven training script (ML_TRAINING.md §7).

Pipeline per disease (ML_TRAINING.md ground rules):
  1. split FIRST (stratify) — test set touched once, at the very end
  2. SMOTE inside the imblearn pipeline (only training folds)
  3. imputer + scaler inside the pipeline (fit on training folds only)
  4. sigmoid calibration → "70% risk" means ~70%
  5. decision threshold from out-of-fold F2 (favours recall for a screening tool)
  6. metrics + flags (SUSPICIOUS_POSSIBLE_LEAKAGE / SMALL_DATASET / HEAVY_IMBALANCE)
  7. artifact → ml/models/<disease>.joblib  (band + see_doctor at serve time)
  8. report → ml/reports/<disease>_metrics.json + <disease>_shap.png + SUMMARY.md

Run:
    python -m ml.train --disease diabetes
    python -m ml.train --all
    python -m ml.train --all --trials 30     # Optuna (CV only; never on test)
    python -m ml.train --disease diabetes --no-shap   # low-RAM: skip shap/matplotlib
    python -m ml.train --summary                      # rebuild SUMMARY.md only
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score,
                             precision_recall_curve, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import (StratifiedKFold, cross_val_predict,
                                     cross_val_score, train_test_split)
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

# optional deps — missing ones degrade gracefully
try:
    import optuna
except Exception:  # pragma: no cover
    optuna = None
# NOTE: shap + matplotlib are imported *lazily* inside `shap_report()` below. On a low-RAM box
# (this one has ~4 GB) importing shap (numba/llvmlite) + matplotlib adds ~300 MB peak, which is
# enough to get the training process OOM-killed. `--no-shap` skips them entirely.

try:
    from ml.train_config import DISEASES, SEED, TARGET_AUC, TARGET_MACRO_F1
except Exception:  # allow running `python ml/train.py` directly
    from train_config import DISEASES, SEED, TARGET_AUC, TARGET_MACRO_F1  # type: ignore

_HERE = Path(__file__).resolve().parent
MODELS_DIR = _HERE / "models"
REPORTS_DIR = _HERE / "reports"
CARD_DIR = MODELS_DIR / "model_cards"
DATA_DIR = _HERE / "data"
for _d in (MODELS_DIR, REPORTS_DIR, CARD_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------- decision-threshold policy (ML_TRAINING.md §7 step 5) ----------
# F2 (β=2) favours recall — correct for a screening tool — but on a RARE positive class it
# degenerates: at 4.8% prevalence (thyroid) the F2-optimal cut-off landed at 0.042, which flags
# almost everybody (precision 0.046). So for rare diseases the threshold maximises F2 *subject to*
# a precision floor; if no cut-off can reach the floor we fall back to the highest-precision
# operating point instead of silently flagging the whole population. Common diseases keep the
# plain argmax-F2 rule.
PRECISION_FLOOR = 0.30
RARE_PREVALENCE = 0.10
# A rare-disease model is well-calibrated around its prevalence, so its probabilities are
# compressed near 0 (stroke: median 0.011, max 0.273). The precision floor then only holds in the
# extreme tail: the first S18 run picked stroke 0.2485 / colorectal 0.0299, which sit *above* every
# test probability → the model flagged nobody (recall 0). Restricting rare-disease operating points
# to those that flag at least MIN_FLAG_RATE of the population is the standard screening guard: it
# guarantees the tool actually alerts someone instead of silently returning "all low".
MIN_FLAG_RATE = 0.02


def choose_threshold(y_true, proba):
    """Return `(threshold, rule_name)` — see the policy note above.

    Fallback order for rare diseases: max F2 subject to (precision >= floor AND flag-rate >= 2 %);
    if the floor is unreachable, Youden's J (max sensitivity + specificity − 1) within the same
    flag-rate guard. Common diseases keep plain argmax-F2 (spec §7).
    """
    y_true = np.asarray(y_true)
    proba = np.asarray(proba)
    prec, rec, thr = precision_recall_curve(y_true, proba)
    if len(thr) == 0:                        # degenerate (constant probabilities)
        return 0.5, "default_0.5"
    f2 = (5 * prec * rec) / (4 * prec + rec + 1e-9)
    prevalence = float(np.mean(y_true))
    if prevalence < RARE_PREVALENCE:
        # flag_rate per candidate threshold = share of training rows at/above it
        ordered = np.sort(proba)
        n = len(proba)
        rate = lambda t: (n - np.searchsorted(ordered, t, side="left")) / n
        reaches = np.where((prec[:-1] >= PRECISION_FLOOR) & (rate(thr) >= MIN_FLAG_RATE))[0]
        if len(reaches):
            idx = int(reaches[np.argmax(f2[reaches])])
            return float(thr[idx]), f"max_f2_s.t._precision>={PRECISION_FLOOR}&rate>={MIN_FLAG_RATE}"
        fpr, tpr, rthr = roc_curve(y_true, proba)     # Youden's J fallback
        j = tpr - fpr
        cand = np.where(np.isfinite(rthr) & (rate(rthr) >= MIN_FLAG_RATE))[0]
        if len(cand):
            idx = int(cand[np.argmax(j[cand])])
            return float(rthr[idx]), f"max_youden_j&rate>={MIN_FLAG_RATE}(precision floor unreachable)"
        return 0.5, "default_0.5"
    return float(thr[int(np.argmax(f2[:-1]))]), "max_f2"


def expected_calibration_error(y_true, proba, bins=10):
    """|confidence − accuracy| averaged over equal-width probability bins (10 bins)."""
    y_true = np.asarray(y_true, dtype=float)
    proba = np.asarray(proba, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (proba > lo) & (proba <= hi) if lo > 0 else (proba >= lo) & (proba <= hi)
        if not np.any(m):
            continue
        ece += (m.sum() / len(proba)) * abs(y_true[m].mean() - proba[m].mean())
    return float(ece)


def bootstrap_ci(y_true, proba, threshold, n_boot=500):
    """Percentile 95% CI for test AUC + macro F1 — small test sets make a single point estimate
    look far more certain than it is (e.g. rare cancers with a few dozen test cases)."""
    rng = np.random.default_rng(SEED)
    y_true = np.asarray(y_true)
    proba = np.asarray(proba)
    aucs, f1s = [], []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yt, p = y_true[idx], proba[idx]
        if len(np.unique(yt)) < 2:
            continue
        aucs.append(roc_auc_score(yt, p))
        f1s.append(f1_score(yt, (p >= threshold).astype(int), average="macro"))
    ci = lambda v: ([round(float(np.percentile(v, 2.5)), 4),
                     round(float(np.percentile(v, 97.5)), 4)] if v else None)
    return {"test_auc_ci95": ci(aucs), "test_macro_f1_ci95": ci(f1s),
            "n_bootstrap": len(aucs)}


# ---------- data ----------
def _resolve(path: str) -> Path:
    p = Path(path)
    if p.is_absolute() or p.exists():
        return p
    if (DATA_DIR / p.name).exists():
        return DATA_DIR / p.name
    return _HERE.parent / p


def load_data(cfg):
    df = pd.read_csv(_resolve(cfg["data"]), na_values=["?", "", "NA", "nan"],
                     skipinitialspace=True)
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
    # NOTE (ML_TRAINING.md §7): tree depth/size is deliberately bounded — with
    # CalibratedClassifierCV(cv=3) the fitted ensemble is pickled 3x, so unbounded
    # full-depth 300-tree forests made each artifact ~275 MB. Bounded trees keep the
    # artifact in the low-MB range with no measurable AUC loss on these tabular sets.
    p = {"rf_n": 120, "rf_depth": 8, "xgb_n": 120, "xgb_depth": 4,
         "xgb_lr": 0.05, "lr_C": 1.0}
    p.update(params or {})
    ens = VotingClassifier(
        [("rf", RandomForestClassifier(n_estimators=p["rf_n"], max_depth=p["rf_depth"],
                                       min_samples_leaf=3, class_weight="balanced",
                                       random_state=SEED, n_jobs=1)),
         ("xgb", XGBClassifier(n_estimators=p["xgb_n"], max_depth=p["xgb_depth"],
                               learning_rate=p["xgb_lr"], eval_metric="logloss",
                               random_state=SEED, n_jobs=1)),
         ("lr", LogisticRegression(C=p["lr_C"], max_iter=2000, class_weight="balanced"))],
        voting="soft", weights=[0.4, 0.4, 0.2])
    k = max(1, min(5, int(n_min * 0.6) - 1)) if n_min > 0 else 5
    return ImbPipeline([("prep", make_preprocessor(cfg)),
                        ("smote", SMOTE(k_neighbors=k, random_state=SEED)),
                        ("clf", ens)])


def tune(cfg, X, y, n_min, n_trials):
    if n_trials <= 0 or optuna is None:
        return {}
    cv = StratifiedKFold(3, shuffle=True, random_state=SEED)

    def objective(trial):
        params = {
            "rf_n": trial.suggest_int("rf_n", 150, 400),
            "rf_depth": trial.suggest_int("rf_depth", 3, 12),
            "xgb_n": trial.suggest_int("xgb_n", 150, 400),
            "xgb_depth": trial.suggest_int("xgb_depth", 2, 6),
            "xgb_lr": trial.suggest_float("xgb_lr", 0.01, 0.15, log=True),
            "lr_C": trial.suggest_float("lr_C", 0.01, 5, log=True),
        }
        return cross_val_score(build_model(cfg, params, n_min), X, y,
                               cv=cv, scoring="roc_auc").mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=n_trials)
    return study.best_params


def shap_report(cfg, X_tr, y_tr, name):
    """Mean |SHAP| top-10 + a PNG, from a throwaway XGB on the training data (spec §8).

    shap/matplotlib are imported here (not at module level) so `--no-shap` / low-RAM runs never
    pay their ~300 MB import cost.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import shap
    except Exception:  # missing optional dep → no report, training unaffected
        return {}
    try:
        prep = make_preprocessor(cfg)
        Xt = prep.fit_transform(X_tr)
        names = [n.split("__", 1)[-1] for n in prep.get_feature_names_out()]
        xgb = XGBClassifier(n_estimators=120, max_depth=4, learning_rate=0.05,
                            eval_metric="logloss", random_state=SEED, n_jobs=1).fit(Xt, y_tr)
        sv = shap.TreeExplainer(xgb).shap_values(Xt)
        if isinstance(sv, list):
            sv = sv[1] if len(sv) > 1 else sv[0]
        imp = np.abs(sv).mean(axis=0)
        top = sorted(zip(names, imp), key=lambda t: -t[1])[:10]
        plt.figure(figsize=(6, 4))
        plt.barh([t[0] for t in top][::-1], [float(t[1]) for t in top][::-1])
        plt.title(f"{name}: mean |SHAP| (top 10)")
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / f"{name}_shap.png", dpi=120)
        plt.close()
        return {n: round(float(v), 4) for n, v in top}
    except Exception:
        return {}


# ---------- main ----------
def train(name, trials=0, shap=True):
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
    n_min = int(y_tr.value_counts().min()) if len(y_tr) else 0

    # Honesty flag: features the source dataset never collected are all-NaN in training, so the
    # imputer drops them and the model cannot use them even though the app asks for them.
    all_feats = cfg["numeric"] + cfg.get("categorical", [])
    missing_features = [c for c in all_feats if X_tr[c].isna().all()]
    if missing_features:
        flags.append("LOW_FEATURE_MODEL")

    # 2) optional tuning (training data only)
    params = tune(cfg, X_tr, y_tr, n_min, trials) if trials > 0 else {}

    # 3) cross-validation on training data (5 folds — ML_TRAINING.md §7 / acceptance §10)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    cv_scores = cross_val_score(build_model(cfg, params, n_min), X_tr, y_tr,
                                cv=cv, scoring="roc_auc", n_jobs=1)

    # 4) calibrated final model (SMOTE stays inside the pipeline).
    #    cal_cv=3 (not 5): CalibratedClassifierCV pickles one full ensemble per fold, and this
    #    box has ~4 GB RAM — 3 folds keeps peak memory + artifact size sane. The *reported*
    #    cv_auc above still uses 5 folds, so the acceptance metric is spec-compliant.
    cal_cv = StratifiedKFold(3, shuffle=True, random_state=SEED)
    model = CalibratedClassifierCV(build_model(cfg, params, n_min),
                                   method="sigmoid", cv=cal_cv)

    # 5) threshold from out-of-fold probabilities (rare-disease-aware, see `choose_threshold`)
    oof = cross_val_predict(model, X_tr, y_tr, cv=cal_cv, method="predict_proba",
                            n_jobs=1)[:, 1]
    threshold, threshold_rule = choose_threshold(y_tr, oof)

    # 6) fit on all training data, evaluate ONCE on the untouched test set
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= threshold).astype(int)

    test_auc = float(roc_auc_score(y_te, proba))
    macro_f1 = float(f1_score(y_te, pred, average="macro"))
    if test_auc > 0.97:
        # Label derived from the features BY DESIGN (gad7/depression PHQ-9/GAD-7 items -> sum>=10)
        # mirrors the clinical rule the app already implements — not accidental leakage, so it is
        # flagged distinctly from a genuine leak and reported as an expected property.
        flags.append("EXPECTED_LEAKAGE_LABEL_FROM_FEATURES" if cfg.get("label_from_features")
                     else "SUSPICIOUS_POSSIBLE_LEAKAGE")
    if cfg.get("label_from_features"):
        # The "model" is mathematically the rule (sum of the item scores), so it must not be
        # reported as a PASS/accuracy claim — the app serves the clinical rule directly and the
        # ML artifact adds no new signal. Kept trained so existing artifacts/DB rows stay valid.
        flags.append("RULE_EQUIVALENT_MODEL")

    # 7) honest test-set evaluation extras: imbalance-aware ranking (PR-AUC), probability quality
    #    against the trivial baseline (Brier skill), ECE, and percentile CIs from a bootstrap.
    n_pos = int(y_te.sum())
    n_neg = int(len(y_te) - n_pos)
    pr_auc = float(average_precision_score(y_te, proba))
    brier = float(brier_score_loss(y_te, proba))
    test_prevalence = float(np.mean(y_te))
    brier_baseline = float(brier_score_loss(y_te, np.full_like(proba, test_prevalence)))
    brier_skill = 1.0 - (brier / brier_baseline) if brier_baseline > 0 else 0.0
    tn = int(((pred == 0) & (y_te == 0)).sum())
    specificity = float(tn / n_neg) if n_neg else 0.0
    npv = float(tn / (tn + int(((pred == 0) & (y_te == 1)).sum()))) if (tn + int(((pred == 0) & (y_te == 1)).sum())) else 0.0
    ci = bootstrap_ci(y_te, proba, threshold)

    if cfg.get("label_from_features"):
        status = "RULE_SERVED"          # not an accuracy claim — see the flag above
    else:
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
        "test_pr_auc": round(pr_auc, 4),
        "test_recall": round(float(recall_score(y_te, pred, zero_division=0)), 4),
        "test_precision": round(float(precision_score(y_te, pred, zero_division=0)), 4),
        "test_specificity": round(specificity, 4),
        "test_npv": round(npv, 4),
        "test_macro_f1": round(macro_f1, 4),
        "test_positives": n_pos,
        "test_negatives": n_neg,
        "brier_score": round(brier, 4),
        "brier_baseline": round(brier_baseline, 4),
        "brier_skill_score": round(brier_skill, 4),
        "ece": round(expected_calibration_error(y_te, proba), 4),
        "test_auc_ci95": ci["test_auc_ci95"],
        "test_macro_f1_ci95": ci["test_macro_f1_ci95"],
        "threshold": round(threshold, 4),
        "threshold_rule": threshold_rule,
        "targets": {"auc": TARGET_AUC, "macro_f1": TARGET_MACRO_F1},
        "status": status,
        "flags": flags,
        "missing_features": missing_features,
        "top_features_shap": shap_report(cfg, X_tr, y_tr, name) if shap else {},
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    joblib.dump({"model": model, "numeric": cfg["numeric"],
                 "categorical": cfg.get("categorical", []),
                 "threshold": threshold, "meta": metrics},
                MODELS_DIR / f"{name}.joblib", compress=3)
    (REPORTS_DIR / f"{name}_metrics.json").write_text(json.dumps(metrics, indent=2),
                                                      encoding="utf-8")

    # model card (spec 09-ML-TRAINING-SPEC §1 step 10 shape)
    card = {
        "disease_key": name,
        "trained_at": metrics["trained_at"].replace("+00:00", "Z"),
        "dataset": metrics["dataset"],
        "dataset_version": "v1",
        "n_samples": metrics["rows"],
        "metrics": {"auc_roc": test_auc, "pr_auc": pr_auc, "macro_f1": macro_f1,
                    "test_recall": metrics["test_recall"],
                    "test_precision": metrics["test_precision"],
                    "test_specificity": metrics["test_specificity"],
                    "brier_score": metrics["brier_score"],
                    "brier_baseline": metrics["brier_baseline"],
                    "brier_skill_score": metrics["brier_skill_score"],
                    "ece": metrics["ece"],
                    "auc_ci95": metrics["test_auc_ci95"],
                    "macro_f1_ci95": metrics["test_macro_f1_ci95"]},
        "features": metrics["features"],
        "threshold": metrics["threshold"],
        "threshold_rule": metrics["threshold_rule"],
        "threshold_met": status == "PASS",
        "flags": flags,
        "known_limitations": [
            "App-aligned projection of a real public dataset (ml/data/README.md) — not a "
            "local clinical sample; revalidate on local data before clinical use",
            ("Columns the source dataset never collected: "
             + ", ".join(missing_features) + " — the app still asks these but the model "
             "cannot use them (LOW_FEATURE_MODEL)") if missing_features else
            "All app features are present in the source dataset",
            "Screening and awareness tool only, not a diagnostic device",
        ] + (["RULE_EQUIVALENT_MODEL: the label is derived from these very features by design "
              "(PHQ-9/GAD-7 item sum >= 10), so the 'model' is mathematically the clinical rule. "
              "It is trained for back-compatibility but is NOT an accuracy claim — the app serves "
              "the rule directly (status RULE_SERVED)."] if "RULE_EQUIVALENT_MODEL" in flags else [])
          + (["SUSPICIOUS_POSSIBLE_LEAKAGE: test AUC > 0.97 — investigate before trusting"]
             if "SUSPICIOUS_POSSIBLE_LEAKAGE" in flags else []),
    }
    (CARD_DIR / f"{name}.json").write_text(json.dumps(card, indent=2), encoding="utf-8")

    print(f"[{name}] AUC={test_auc:.3f} PR-AUC={pr_auc:.3f} recall={metrics['test_recall']:.3f} "
          f"prec={metrics['test_precision']:.3f} F1={macro_f1:.3f} thr={threshold:.4f} "
          f"({threshold_rule}) -> {status} {flags}")
    return metrics


def write_summary(all_metrics):
    lines = ["# Training Summary", "",
             "| Disease | Rows | CV AUC | Test AUC | PR-AUC | Recall | Precision | Macro F1 | Brier (skill) | Status | Flags |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in all_metrics:
        skill = m.get("brier_skill_score")
        brier = f"{m['brier_score']}"
        if skill is not None:
            brier += f" ({skill:+.3f})"
        lines.append(f"| {m['disease']} | {m['rows']} | {m['cv_auc_mean']}±{m['cv_auc_std']} | "
                     f"{m['test_auc']} | {m.get('test_pr_auc', '-')} | {m['test_recall']} | "
                     f"{m.get('test_precision', '-')} | {m['test_macro_f1']} | {brier} | "
                     f"{m['status']} | {', '.join(m['flags']) or '-'} |")
    lines += [
        "", "## Legend", "",
        f"- **PASS** = test AUC >= {TARGET_AUC} AND macro F1 >= {TARGET_MACRO_F1}",
        "- **BELOW_TARGET** = at least one target missed (mostly data-limited — see flags below)",
        "- **RULE_SERVED** = the ML artifact is mathematically the clinical rule (label derived "
        "from the same item scores), so it is NOT counted as an accuracy result; the app serves "
        "the rule (`ScreeningClassifier.score_gad7`, PHQ-9 severity rule)",
        "- **LOW_FEATURE_MODEL** = the source dataset does not collect some app features, so the "
        "model cannot use them (honest limitation, not a bug)",
        "- **SMALL_DATASET** = fewer than 500 rows",
        "- **HEAVY_IMBALANCE** = positive rate below 10% or above 90%",
        "- **RULE_EQUIVALENT_MODEL** = label derived from the features by design; ML adds no signal",
        "- **EXPECTED_LEAKAGE_LABEL_FROM_FEATURES** = the label is derived from the features by "
        "design (mirrors the app's clinical rule for the PHQ-9/GAD-7 screeners), so the near-perfect "
        "AUC is expected and the ML model adds no new signal over the rule",
        "- **SUSPICIOUS_POSSIBLE_LEAKAGE** = test AUC > 0.97 without a documented reason — "
        "investigate before trusting",
        "- **PR-AUC** = average precision — the imbalance-aware companion to ROC-AUC (the primary "
        "read for rare outcomes such as colorectal)",
        "- **Brier (skill)** = Brier score with its skill score in brackets; `+` means better than "
        "the trivial constant-probability baseline, `−` means worse",
        "- **Threshold rule** — rare diseases (positive rate < 10%) maximise F2 **subject to** a "
        "0.30 precision floor **and** a minimum flag rate of 2% (a well-calibrated rare-disease "
        "model sits near its prevalence, so without the rate guard the cut-off lands above every "
        "probability and the tool flags nobody — recall 0). Fallback when the floor is unreachable: "
        "**Youden's J** within the same rate guard. Common diseases keep plain argmax-F2 "
        "(per-disease value: `ml/reports/<disease>_metrics.json`, key `threshold_rule`)",
    ]
    # encoding pinned: the table carries "±" and the console locale on Windows is cp1252
    (REPORTS_DIR / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_all(trials=0, shap=True):
    """Train every ML disease (ML_TRAINING.md §2). Returns {disease: metrics}."""
    results = {}
    for name in DISEASES:
        try:
            results[name] = train(name, trials, shap=shap)
        except Exception as e:  # keep going, report the failure honestly
            print(f"[{name}] FAILED: {e!r}")
    write_summary(list(results.values()))
    return results


def rebuild_summary():
    """Rebuild SUMMARY.md from the existing `ml/reports/*_metrics.json` files.

    `--all` is the only writer of SUMMARY.md, so a per-disease run (the low-RAM workflow on this
    box: one `python -m ml.train --disease <name>` process at a time) would otherwise leave the
    summary stale. This reads whatever metrics exist and regenerates the table.
    """
    metrics = []
    for path in sorted(REPORTS_DIR.glob("*_metrics.json")):
        try:
            metrics.append(json.loads(path.read_text()))
        except Exception:
            continue
    metrics.sort(key=lambda m: m.get("disease", ""))
    write_summary(metrics)
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--disease")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--summary", action="store_true",
                    help="rebuild ml/reports/SUMMARY.md from existing *_metrics.json")
    ap.add_argument("--no-shap", action="store_true",
                    help="skip the SHAP report (saves ~300 MB peak on low-RAM machines)")
    ap.add_argument("--trials", type=int, default=0)
    args = ap.parse_args()
    use_shap = not args.no_shap
    if args.all:
        train_all(args.trials, shap=use_shap)
    elif args.summary:
        rebuild_summary()
    elif args.disease:
        train(args.disease, args.trials, shap=use_shap)
    else:
        ap.error("pass --disease <name> or --all")
