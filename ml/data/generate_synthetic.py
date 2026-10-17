# ml/data/generate_synthetic.py
"""Synthetic datasets for the two registry diseases that have NO usable real dataset.

`docx.md/ML_TRAINING.md` Ground Rule 1 says: *"no production model is trained on synthetic
data"*. That rule is deliberately DEVIATED FROM here — at the project owner's explicit request —
so that all 17 registry diseases have a trained artifact:

    colorectal  — no credible real screening dataset (age + family history + lifestyle + symptoms)
    burnout     — no real questionnaire whose columns match the app's burnout inputs

**Only `burnout` is actually trained from this file** (see `ml/train_config.py`). For colorectal a
REAL dataset was found after all — NHANES 2017-2018 `MCQ_J` (doctor-diagnosed colon/rectum cancer,
55 cases among adults 40+) — and the real model beat this synthetic one (test AUC 0.694 vs 0.541),
so `colorectal.csv` here is kept only as the recorded comparison baseline (see `ml/data/README.md`).

Everything trained from this file is labelled SYNTHETIC so it can never be mistaken for real data:

  * ``"synthetic": True`` in ``ml/train_config.py``
  * ``SYNTHETIC_DATA`` flag in ``<disease>_metrics.json``, the model card and ``SUMMARY.md``
  * a ``source`` column inside the generated CSV
  * ``ml/data/README.md``

Generator (deterministic, ``SEED=42``). One latent risk factor ``z ~ Beta(2, 2)`` drives BOTH the
label and (noisily) every feature::

    z   ~ Beta(2, 2)
    y   ~ Bernoulli(sigmoid(b0 + b1 * (z - 0.5)))        label
    x_j = clip(mu_j + a_j * (z - 0.5) + eps_j)           feature,  eps_j ~ N(0, sd_j)

``b1`` (label slope) and ``signal`` (1/noise multiplier) were calibrated with a 3-fold
RandomForest sweep so the generated data lands in the same 0.75-0.95 AUC band as the real
datasets — a synthetic set scoring 0.99 would be a useless placeholder:

    signal=2.0, slope=8.0   -> burnout    cv AUC ~0.82, positive rate ~0.43
    signal=2.0, slope=10.0  -> colorectal cv AUC ~0.81, positive rate ~0.38

**The purpose of a synthetic model is API/UI completeness, NOT evidence**: its numbers say nothing
about real-world performance and must be reported as such.

Run:  python -m ml.data.generate_synthetic
Out:  ml/data/synthetic/colorectal.csv
      ml/data/synthetic/burnout.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
OUT_DIR = Path(__file__).resolve().parent / "synthetic"


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _bern(rng, p):
    return (rng.random(len(p)) < p).astype(float)


def _ordinal(rng, probs):
    """probs: (n_levels, n) array, columns sum to 1 -> sampled level 0..n_levels-1."""
    cum = np.cumsum(probs, axis=0)
    u = rng.random(probs.shape[1])
    return (u >= cum[:-1]).sum(axis=0).astype(float)


# ── colorectal ───────────────────────────────────────────────────────────────────────────────
# Feature order MUST match ml/models/phase2_risk.py `_FEATURE_NAMES["colorectal"]` /
# ml/train_config.py (BUG-5: training columns == inference columns).
# diet_quality encoding 0=good, 1=average, 2=poor; exercise_level 0..4 (sedentary..very active),
# both exactly as `Phase2RiskEngine._build_vector` encodes them.
def colorectal(rng, n=1500, signal=2.0, slope=10.0):
    z = rng.beta(2.0, 2.0, n)                       # latent risk in [0, 1]

    age = np.clip(np.round(62 + 16 * (z - 0.5) + rng.normal(0, 11 / signal, n)), 40, 88)
    family_cancer = _bern(rng, 0.10 + 0.30 * z)

    p_poor = 0.10 + 0.36 * z
    p_avg = 0.45 - 0.05 * z
    diet_quality = _ordinal(rng, np.vstack([1 - p_poor - p_avg, p_avg, p_poor]))

    p0 = 0.10 + 0.28 * z                            # sedentary
    p1 = np.full(n, 0.25)
    p2 = 0.30 - 0.05 * z
    p3 = 0.22 - 0.10 * z
    exercise_level = _ordinal(rng, np.vstack([p0, p1, p2, p3, 1 - p0 - p1 - p2 - p3]))

    smoking = _bern(rng, 0.14 + 0.32 * z)
    alcohol = np.clip(np.round(1.5 + 4.0 * z + rng.normal(0, 1.3 / signal, n)), 0, 7)
    blood_in_stool = _bern(rng, 0.03 + 0.30 * z)
    bowel_change = _bern(rng, 0.06 + 0.34 * z)
    colorectal_weight_loss = _bern(rng, 0.03 + 0.26 * z)

    target = _bern(rng, _sigmoid(-0.85 + slope * (z - 0.5)))

    return pd.DataFrame({
        "age": age, "family_cancer": family_cancer, "diet_quality": diet_quality,
        "exercise_level": exercise_level, "smoking": smoking, "alcohol": alcohol,
        "blood_in_stool": blood_in_stool, "bowel_change": bowel_change,
        "colorectal_weight_loss": colorectal_weight_loss,
        "target": target, "source": "SYNTHETIC",
    })


# ── burnout ──────────────────────────────────────────────────────────────────────────────────
# The app sends `work_hours`, `job_satisfaction` (1..5) and `exhaustion` (3 items, 0..3 each —
# see GET /screenings/burnout/questions). The training CSV flattens the list to
# exhaustion_1..exhaustion_3 so the model keeps a plain tabular interface.
def burnout(rng, n=1200, signal=2.0, slope=8.0):
    z = rng.beta(2.0, 2.0, n)

    work_hours = np.clip(np.round(35 + 30 * (z - 0.5) + rng.normal(0, 13 / signal, n)), 0, 80)
    job_satisfaction = np.clip(np.round(3.5 - 5.0 * (z - 0.5) + rng.normal(0, 1.0 / signal, n)), 1, 5)
    ex = [np.clip(np.round(0.9 + 3.2 * (z - 0.5) + rng.normal(0, 1.0 / signal, n)), 0, 3)
          for _ in range(3)]

    target = _bern(rng, _sigmoid(-0.55 + slope * (z - 0.5)))

    return pd.DataFrame({
        "work_hours": work_hours, "job_satisfaction": job_satisfaction,
        "exhaustion_1": ex[0], "exhaustion_2": ex[1], "exhaustion_3": ex[2],
        "target": target, "source": "SYNTHETIC",
    })


DATASETS = {"colorectal": colorectal, "burnout": burnout}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"SYNTHETIC data (SEED={SEED}) -> {OUT_DIR}")
    for name, fn in DATASETS.items():
        df = fn(np.random.default_rng(SEED))
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {name}: {len(df)} rows, positive_rate={df['target'].mean():.3f} -> {path.name}")
    print("  note: colorectal.csv is a comparison baseline only - the trained colorectal model "
          "uses the REAL NHANES data (ml/data/real/colorectal.csv)")


if __name__ == "__main__":
    main()
