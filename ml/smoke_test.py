"""Smoke test — acceptance criteria §10: call `predict_risk` for every trained disease.

Run:  python -m ml.smoke_test
      python -m ml.smoke_test --disease ckd     # single disease

Exits non-zero if a trained artifact cannot be loaded or does not return the documented
response shape (`disease`, `risk`, `band`, `see_doctor`, `disclaimer`).
"""
import argparse
import sys

from ml.predict import has_artifact, predict_risk
from ml.train_config import DISEASES

# One "typical middle-aged adult with a few risk factors" value per app feature name.
# Anything not listed defaults to 1 (i.e. "yes"/mild) so every branch gets exercised.
DEFAULTS = {
    "age": 52, "gender": 1, "bmi": 29.5, "sleep_hours": 6.5, "exercise_level": 1,
    "smoking": 1, "alcohol": 1, "bp_systolic": 132, "bp_diastolic": 85,
    "waist_circumference": 96, "diet_quality": 1,
    "doctor_high_bp": 0, "doctor_high_sugar": 0, "family_diabetes": 0, "family_heart": 0,
    "family_hypertension": 0, "family_cancer": 0,
    "gad1": 1, "gad2": 1, "gad3": 1, "gad4": 1, "gad5": 1, "gad6": 1, "gad7": 1,
    "phq1": 1, "phq2": 1, "phq3": 1, "phq4": 1, "phq5": 1, "phq6": 1, "phq7": 1,
    "phq8": 1, "phq9": 1,
}
REQUIRED_KEYS = {"disease", "risk", "band", "see_doctor", "disclaimer"}
VALID_BANDS = {"low", "moderate", "high"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disease")
    args = ap.parse_args()
    names = [args.disease] if args.disease else list(DISEASES)
    failures, skipped = [], []

    for name in names:
        cfg = DISEASES[name]
        if not has_artifact(name):
            skipped.append(name)
            print(f"[skip] {name:18s} no ml/models/{name}.joblib")
            continue
        payload = {col: DEFAULTS.get(col, 1) for col in cfg["numeric"] + cfg.get("categorical", [])}
        try:
            out = predict_risk(name, payload)
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"[FAIL] {name:18s} {type(exc).__name__}: {exc}")
            continue
        missing = REQUIRED_KEYS - set(out)
        if missing or out["band"] not in VALID_BANDS:
            failures.append((name, f"bad shape (missing={missing}, band={out.get('band')})"))
            print(f"[FAIL] {name:18s} bad shape: {out}")
            continue
        print(f"[ ok ] {name:18s} risk={out['risk']:<6} band={out['band']:<8} "
              f"see_doctor={out['see_doctor']}")

    print(f"\n{len(names) - len(failures) - len(skipped)} ok, {len(skipped)} skipped, "
          f"{len(failures)} failed")
    if failures:
        for name, why in failures:
            print(f"  - {name}: {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
