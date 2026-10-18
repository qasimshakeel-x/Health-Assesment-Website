# ml/train_config.py
"""Config-driven training registry (ML_TRAINING.md §6).

One entry per disease = one real dataset + the exact feature list the app sends at inference
time (Ground Rule 6/8, BUG-5: training columns == inference columns).

Feature lists mirror:
  * ml/models/disease_risk.py  `_build_vector`  (diabetes/heart/hypertension/obesity)
  * ml/models/phase2_risk.py   `_FEATURE_NAMES` (stroke/ckd/liver/thyroid/pcos/anemia/
                                                 lung_cancer/colorectal)
  * ml/models/screening_classifier.py           (gad7/sleep_apnea/metabolic_syndrome)
  * ml/models/depression.py                     (PHQ-9 items)

Data files are produced by `python ml/data/prepare_real.py` from the raw downloads in
`ml/data/real/raw/` (sources + licences: ml/data/README.md).

`zero_is_missing` is only used for datasets where 0 is a sentinel (Pima labs). App-aligned
NHANES/Kaggle values already use NaN for "not measured", so it stays empty.

Ground Rule 1: no model is trained on synthetic data — every entry here reads a real dataset.

Decision threshold (§7 step 5, 2026-10): common diseases use the out-of-fold argmax-F2 cut-off.
Rare diseases (positive rate < 10%) maximise F2 **subject to a 0.30 precision floor** — the plain
F2 optimum degenerated on rare outcomes (thyroid: cut-off 0.042, precision 0.046, i.e. almost
everyone flagged). The applied rule is stored per disease in `ml/reports/<disease>_metrics.json`
(`threshold_rule`).

`label_from_features: True` (gad7/depression) means the label is the sum of these very columns, so
the "model" is mathematically the clinical rule. Those entries are trained for back-compatibility
but reported as `RULE_SERVED`, **not** as an accuracy result — the app serves the rule directly.
Remaining dataset upgrades (stronger app-aligned sources) are tracked in `TODO.md` / `opencode.md`.

`colorectal` is trained on the real NHANES sample. `burnout` has no real, app-aligned
questionnaire (the Mendeley dataset's columns are nominal questionnaire codes, not the app's
work_hours / job_satisfaction / exhaustion items), so it is served by the clinically-validated
rule `ScreeningClassifier.score_burnout()` and deliberately has NO ML artifact.
"""
TARGET_AUC = 0.85
TARGET_MACRO_F1 = 0.80
SEED = 42

_TARGET = "target"

DISEASES = {
    # ── Phase 1: DiseaseRiskEngine (ml/models/disease_risk.py) ─────────────────────────────
    "diabetes": {
        "data": "ml/data/real/diabetes.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking",
                    "alcohol", "family_diabetes", "family_heart", "family_hypertension",
                    "family_cancer", "freq_urination", "excess_thirst", "weight_loss"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2017-2018 (J) — label DIQ010 doctor-diagnosed diabetes; "
                       "family history DIQ170. Symptoms not collected in NHANES (NaN).",
    },
    "heart": {
        "data": "ml/data/real/heart.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking",
                    "alcohol", "family_diabetes", "family_heart", "family_hypertension",
                    "family_cancer", "chest_pain", "short_breath", "palpitations"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "CDC BRFSS 2025 (356,158 US adults, 6,000-row seeded stratified cap) - "
                       "label _MICHD = ever told coronary heart disease or heart attack (8.9% of "
                       "the source). 7 of the 14 app columns are real (age, gender, BMI, sleep, "
                       "physical activity, smoking, alcohol); family history and the "
                       "chest-pain/shortness-of-breath/palpitations are not surveyed in BRFSS "
                       "(NaN) -> still LOW_FEATURE_MODEL, but 3 predictors -> 7. "
                       "Legacy fallback when the BRFSS download is missing: UCI Cleveland "
                       "(303 rows, age/gender/chest-pain only).",
    },
    "hypertension": {
        "data": "ml/data/real/hypertension.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking",
                    "alcohol", "family_diabetes", "family_heart", "family_hypertension",
                    "family_cancer", "headaches", "dizziness", "blurred_vision"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2017-2018 (J) — label = measured BP (mean SBP>=130 or DBP>=80); "
                       "BP deliberately excluded from features (ML_TRAINING §5 label-from-feature).",
    },
    "obesity": {
        "data": "ml/data/real/obesity.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking",
                    "alcohol", "family_diabetes", "family_heart", "family_hypertension",
                    "family_cancer", "sugary_diet", "freq_hunger", "hard_lose_weight"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2017-2018 (J) — label = measured BMI>=30; BMI deliberately excluded "
                       "from features (ML_TRAINING §5). LOW_FEATURE_MODEL.",
        # TODO(S18 audit): the label IS BMI>=30, so the ML model can only guess obesity from
        # lifestyle with BMI withheld (test AUC ~0.72, barely above chance for a clinical cut-off).
        # Correct fix = serve the clinical BMI rule instead of the ML artifact (burnout pattern:
        # `ScreeningClassifier.score_obesity()` + registry `engine="screening"`), or swap in a
        # dataset with richer predictors (BRFSS). NOT done now: it introduces a new pattern
        # (rule-served Phase-1 disease) → Golden Rule 2 = comment first, don't restructure.
    },

    # ── Phase 2/3/4/5: Phase2RiskEngine (ml/models/phase2_risk.py) ─────────────────────────
    "stroke": {
        "data": "ml/data/real/stroke.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking",
                    "alcohol", "family_diabetes", "family_heart", "family_hypertension",
                    "family_cancer", "bp_systolic", "bp_diastolic", "tia_symptoms",
                    "speech_difficulty", "irregular_heartbeat"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "CDC BRFSS 2025 (356,158 US adults, 6,000-row seeded stratified cap) - "
                       "label CVDSTRK3 = ever told stroke (4.6% of the source). 7 of the 16 app "
                       "columns are real; family history, BP and the TIA/speech/palpitations "
                       "symptoms are not surveyed (NaN) - deliberately: the previous Kaggle "
                       "mapping stored the respondent's OWN hypertension/heart_disease in the "
                       "family_* columns while the app asks the user for FAMILY history, so the "
                       "model learned a personal-history effect and applied it to a family flag. "
                       "Legacy fallback: Kaggle fedesoriano (5,110 rows).",
    },
    "ckd": {
        "data": "ml/data/real/ckd.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "bp_systolic", "diabetes_flag", "hypertension_flag", "ankle_swelling",
                    "urination_changes", "ckd_fatigue"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2013-2018 (H+I+J, 17,032 rows, 3.8% positive) - label KIQ022 = "
                       "ever told weak/failing kidneys; age / measured BP (BPX) / diabetes (DIQ010) "
                       "/ high-BP history (BPQ020) / nocturia>=2 (KIQ480) are real app columns; "
                       "ankle-swelling & fatigue are not collected in NHANES (NaN). Replaces the "
                       "400-row UCI CKD set whose AUC 0.955 was inflated.",
    },
    "liver": {
        "data": "ml/data/real/liver.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "alcohol", "jaundice", "abdominal_pain",
                    "liver_fatigue"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2013-2018 (H+I+J, 17,020 rows, 4.6% positive) - label MCQ160L = "
                       "ever told any liver condition; age / gender / BMI / alcohol (ALQ "
                       "ever-drink) / jaundice (MCQ203) are real app columns; abdominal-pain & "
                       "fatigue are not collected in NHANES (NaN). Replaces the 583-row UCI ILPD "
                       "set (age/gender only). LOW_FEATURE_MODEL.",
    },
    "thyroid": {
        "data": "ml/data/real/thyroid.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "fatigue", "weight_change", "temperature_issues",
                    "hair_skin"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "UCI hypothyroid (3163 rows) — only age/gender app-available; TSH/T3/TT4 "
                       "labs are not collected by the app. LOW_FEATURE_MODEL.",
    },
    "pcos": {
        "data": "ml/data/real/pcos.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "bmi", "irregular_periods", "weight_gain", "excess_hair", "acne"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "Kaggle PCOS (541 rows) — Age/BMI/cycle/weight-gain/hair/acne.",
    },
    "anemia": {
        "data": "ml/data/real/anemia.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["gender", "age", "diet_quality", "frequent_fatigue", "pale_cold",
                    "lightheadedness", "brittle_nails"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2013-2018 (H+I+J pooled, 3,000-row seeded cap) - label = "
                       "haemoglobin < WHO cut-off (13.0 M / 12.0 F); multi-cycle pool (was "
                       "2017-18 only); no lab features used (app-aligned). LOW_FEATURE_MODEL.",
    },
    "lung_cancer": {
        "data": "ml/data/real/lung_cancer.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["smoking", "passive_smoke", "age", "family_cancer", "persistent_cough",
                    "coughing_blood", "breath_shortness"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "Kaggle lung-cancer survey (309 rows) — SMALL_DATASET; passive-smoke/blood "
                       "symptoms not surveyed (NaN).",
    },

    # ── Rule-based screeners, trained anyway on real questionnaire data (same pipeline) ────
    "gad7": {
        "data": "ml/data/real/gad7.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["gad1", "gad2", "gad3", "gad4", "gad5", "gad6", "gad7"],
        "categorical": [],
        "zero_is_missing": [],
        "label_from_features": True,
        "source_note": "Real GAD-7 questionnaire (776 rows, Figshare CC BY) — label = GAD-7 total "
                       ">=10 (moderate+). Label is derived from the items BY DESIGN (mirrors the "
                       "clinical rule the app uses), so an EXPECTED_LEAKAGE_LABEL_FROM_FEATURES "
                       "flag is expected.",
    },
    "sleep_apnea": {
        "data": "ml/data/real/sleep_apnea.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "snoring", "wake_tired", "witnessed_apnea",
                    "daytime_sleepy"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "Kaggle Sleep Health & Lifestyle survey (374 rows, CC0) — Sleep Disorder=="
                       "Sleep Apnea label; BMI derived from BMI category, wake_tired<-sleep quality, "
                       "daytime_sleepy<-stress. SMALL_DATASET.",
    },
    "metabolic_syndrome": {
        "data": "ml/data/real/metabolic_syndrome.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "waist_circumference", "bp_systolic", "bp_diastolic",
                    "diet_quality", "exercise_level", "doctor_high_bp", "doctor_high_sugar",
                    "frequent_thirst_urination"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2017-2018 (J) — IDF metabolic syndrome label (>=3 of 5). Label and "
                       "features share clinical inputs BY DESIGN (documented §5 overlap); a "
                       "SUSPICIOUS_POSSIBLE_LEAKAGE flag may appear.",
    },
    "depression": {
        "data": "ml/data/real/depression.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["phq1", "phq2", "phq3", "phq4", "phq5", "phq6", "phq7", "phq8", "phq9"],
        "categorical": [],
        "zero_is_missing": [],
        "label_from_features": True,
        "source_note": "Real PHQ-9 questionnaire (776 rows, Figshare CC BY) — label = PHQ-9 total "
                       ">=10 (moderate+). Label derived from the items BY DESIGN (mirrors the app's "
                       "PHQ-9 severity rule); an EXPECTED_LEAKAGE_LABEL_FROM_FEATURES flag is expected.",
    },

    # ── colorectal — REAL (found after the first search pass; see ml/data/README.md) ────────
    "colorectal": {
        "data": "ml/data/real/colorectal.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "family_cancer", "diet_quality", "exercise_level", "smoking", "alcohol",
                    "blood_in_stool", "bowel_change", "colorectal_weight_loss"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "NHANES 2009-2018 pooled (F+G+H+I+J) - MCQ230A-D, code 16 (colon) / 31 "
                       "(rectum), age>=40 (app gate). Only 4 of the 9 app features exist in "
                       "NHANES; 19,201 rows / 215 cases (1.1%) -> LOW_FEATURE_MODEL + "
                       "HEAVY_IMBALANCE. S18 pooled H+I+J (11,463 rows / 120 cases); this pass "
                       "added the 2009-2012 cycles F/G. The earlier single-cycle test AUC 0.694 "
                       "was small-sample luck; judge the pooled score as the honest estimate.",
    },

    # NOTE: `burnout` is intentionally absent here — there is no real, app-aligned
    # questionnaire (see the module docstring), so it is served by the clinically-validated
    # rule ScreeningClassifier.score_burnout() (registry: engine="screening", scoring="rule")
    # and deliberately has no ML artifact.
}
