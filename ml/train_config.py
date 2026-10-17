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

Diseases with no usable real dataset would normally be marked NO_REAL_DATA and left out (Ground
Rule 1: no model trained on synthetic data). Two of them (`colorectal`, `burnout`) are instead
trained on a clearly-labelled SYNTHETIC dataset at the project owner's request — an explicit,
documented deviation from Ground Rule 1 — so that all 17 registry diseases have an artifact.
Any entry with `"synthetic": True` must be reported as synthetic everywhere.
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
        "source_note": "UCI Cleveland heart disease (303 rows) — age/gender/chest-pain only; "
                       "Cleveland has no smoking/BMI/sleep/exercise columns (NaN). LOW_FEATURE_MODEL.",
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
        "source_note": "Kaggle stroke prediction (5110 rows, fedesoriano) — age/gender/bmi/smoking "
                       "plus hypertension/heart_disease history flags; TIA/speech symptoms NaN.",
    },
    "ckd": {
        "data": "ml/data/real/ckd.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "bp_systolic", "diabetes_flag", "hypertension_flag", "ankle_swelling",
                    "urination_changes", "ckd_fatigue"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "UCI Chronic Kidney Disease (400 rows) — age/bp/dm/htn mapped to app vector; "
                       "swelling/urination/fatigue symptoms not in UCI (NaN).",
    },
    "liver": {
        "data": "ml/data/real/liver.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["age", "gender", "bmi", "alcohol", "jaundice", "abdominal_pain",
                    "liver_fatigue"],
        "categorical": [],
        "zero_is_missing": [],
        "source_note": "UCI ILPD liver patients (583 rows) — only age/gender app-available; "
                       "ILPD has no alcohol/symptom columns. LOW_FEATURE_MODEL.",
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
        "source_note": "NHANES 2017-2018 (J) — label = haemoglobin < WHO cut-off (13.0 M / 12.0 F); "
                       "no lab features used (app-aligned). LOW_FEATURE_MODEL.",
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
        "source_note": "Real GAD-7 questionnaire (776 rows, Figshare CC BY) — label = GAD-7 total "
                       ">=10 (moderate+). Label is derived from the items BY DESIGN (mirrors the "
                       "clinical rule the app uses), so a SUSPICIOUS_POSSIBLE_LEAKAGE flag is expected.",
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
        "source_note": "Real PHQ-9 questionnaire (776 rows, Figshare CC BY) — label = PHQ-9 total "
                       ">=10 (moderate+). Label derived from the items BY DESIGN (mirrors the app's "
                       "PHQ-9 severity rule); a SUSPICIOUS_POSSIBLE_LEAKAGE flag is expected.",
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
        "source_note": "NHANES 2017-2018 (J) MCQ_J MCQ230A-D, code 16 (colon) / 31 (rectum), "
                       "age>=40 (app gate). Only 4 of the 9 app features exist in NHANES and there "
                       "are just 55 cases (1.4%) -> LOW_FEATURE_MODEL + HEAVY_IMBALANCE and a weak "
                       "AUC, exactly as ML_TRAINING §6 predicts for a dataset this small.",
    },

    # ── burnout — SYNTHETIC (Ground Rule 1 deviation, project-owner request) ───────────────
    "burnout": {
        "data": "ml/data/synthetic/burnout.csv",
        "target": _TARGET,
        "target_map": None,
        "numeric": ["work_hours", "job_satisfaction", "exhaustion_1", "exhaustion_2",
                    "exhaustion_3"],
        "categorical": [],
        "zero_is_missing": [],
        "synthetic": True,
        "source_note": "SYNTHETIC (ml/data/generate_synthetic.py, SEED=42). A real burnout dataset "
                       "exists (Mendeley 'Burnout Risks Bangladeshi Physicians', CC BY 4.0, 1434 "
                       "rows) but is NOT app-aligned: Working_Hour / Dissatisfaction / "
                       "Mental_Disturbances are nominal questionnaire codes, not the app's "
                       "work_hours, job_satisfaction (1-5) and 3 exhaustion items (0-3). Metrics "
                       "here are NOT real-world evidence; the app still serves the rule-based "
                       "score_burnout() (ml/models/screening_classifier.py).",
    },
}
