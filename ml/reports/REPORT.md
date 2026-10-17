# ML Training Report (ML_TRAINING.md §12)

Generated `2026-10-14 19:26 UTC` from `ml/reports/*_metrics.json` + `ml/models/model_cards/*.json` — regenerate with `python -m ml.report`.

**17 diseases trained · 3 PASS · 14 BELOW_TARGET** (targets: AUC ≥ 0.85 and macro F1 ≥ 0.80 — a missed target is reported, not hidden).

## Summary

| Disease | Dataset | Rows | Pos. rate | Features | CV AUC | Test AUC | Recall | Macro F1 | Status | Flags |
|---|---|---|---|---|---|---|---|---|---|---|
| `anemia` | NHANES 2017-2018 | 3000 | 15.90% | 7 | 0.759 ± 0.032 | 0.756 | 0.747 | 0.553 | BELOW_TARGET | LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): diet_quality, frequent_fatigue, pale_cold, lightheadedness, brittle_nails |
| `burnout` | **SYNTHETIC** | 1200 | 42.83% | 5 | 0.818 ± 0.025 | 0.877 | 0.942 | 0.745 | BELOW_TARGET | SYNTHETIC_DATA |
| `ckd` | UCI Chronic Kidney Disease | 400 | 62.50% | 7 | 0.936 ± 0.030 | 0.955 | 0.980 | 0.677 | BELOW_TARGET | SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): ankle_swelling, urination_changes, ckd_fatigue |
| `colorectal` | NHANES 2017-2018 | 3882 | 1.42% | 9 | 0.579 ± 0.045 | 0.694 | 0.091 | 0.519 | BELOW_TARGET | HEAVY_IMBALANCE, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): family_cancer, diet_quality, blood_in_stool, bowel_change, colorectal_weight_loss |
| `depression` | Real PHQ-9 questionnaire | 776 | 24.74% | 9 | 0.996 ± 0.002 | 0.998 | 1.000 | 0.936 | PASS | SUSPICIOUS_POSSIBLE_LEAKAGE |
| `diabetes` | NHANES 2017-2018 | 3000 | 10.27% | 14 | 0.886 ± 0.024 | 0.875 | 0.855 | 0.654 | BELOW_TARGET | LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): family_heart, family_hypertension, family_cancer, freq_urination, excess_thirst, weight_loss |
| `gad7` | Real GAD-7 questionnaire | 776 | 24.23% | 7 | 0.997 ± 0.003 | 0.999 | 1.000 | 0.905 | PASS | SUSPICIOUS_POSSIBLE_LEAKAGE |
| `heart` | UCI Cleveland heart disease | 303 | 45.87% | 14 | 0.774 ± 0.034 | 0.701 | 0.821 | 0.598 | BELOW_TARGET | SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, short_breath, palpitations |
| `hypertension` | NHANES 2017-2018 | 3000 | 35.23% | 14 | 0.803 ± 0.016 | 0.810 | 0.967 | 0.622 | BELOW_TARGET | LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): family_diabetes, family_heart, family_hypertension, family_cancer, headaches, dizziness, blurred_vision |
| `liver` | UCI ILPD liver patients | 583 | 71.36% | 7 | 0.625 ± 0.026 | 0.649 | 0.940 | 0.478 | BELOW_TARGET | LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, alcohol, jaundice, abdominal_pain, liver_fatigue |
| `lung_cancer` | Kaggle lung-cancer survey | 309 | 87.38% | 7 | 0.614 ± 0.112 | 0.720 | 1.000 | 0.466 | BELOW_TARGET | SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): passive_smoke, family_cancer, coughing_blood |
| `metabolic_syndrome` | NHANES 2017-2018 | 3000 | 28.17% | 10 | 0.903 ± 0.007 | 0.898 | 0.935 | 0.725 | BELOW_TARGET | LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): diet_quality, frequent_thirst_urination |
| `obesity` | NHANES 2017-2018 | 3000 | 30.07% | 14 | 0.727 ± 0.024 | 0.722 | 0.944 | 0.536 | BELOW_TARGET | LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, family_diabetes, family_heart, family_hypertension, family_cancer, sugary_diet, freq_hunger, hard_lose_weight |
| `pcos` | Kaggle PCOS | 541 | 32.72% | 6 | 0.841 ± 0.026 | 0.872 | 0.861 | 0.752 | BELOW_TARGET | none |
| `sleep_apnea` | Kaggle Sleep Health & Lifestyle survey | 374 | 20.86% | 7 | 0.913 ± 0.064 | 0.953 | 1.000 | 0.910 | PASS | SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): snoring, witnessed_apnea |
| `stroke` | Kaggle stroke prediction | 5110 | 4.87% | 16 | 0.821 ± 0.017 | 0.814 | 0.820 | 0.506 | BELOW_TARGET | HEAVY_IMBALANCE, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): sleep_hours, exercise_level, alcohol, family_diabetes, family_cancer, bp_systolic, bp_diastolic, tia_symptoms, speech_difficulty, irregular_heartbeat |
| `thyroid` | UCI hypothyroid | 3163 | 4.77% | 7 | 0.588 ± 0.092 | 0.536 | 0.633 | 0.293 | BELOW_TARGET | HEAVY_IMBALANCE, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, fatigue, weight_change, temperature_issues, hair_skin |

> **This is a screening and awareness tool, not a diagnostic device.** Models must be revalidated on local clinical data before any real-world use.

## Per disease

### `anemia`

- **Dataset:** NHANES 2017-2018 (J) — label = haemoglobin < WHO cut-off (13.0 M / 12.0 F); no lab features used (app-aligned). LOW_FEATURE_MODEL.
- **Rows:** 3000 (positive rate 15.90%)
- **Features (7):** gender, age, diet_quality, frequent_fatigue, pale_cold, lightheadedness, brittle_nails
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.7594 ± 0.0321  |  **Test AUC:** 0.7558  |  **Recall:** 0.7474  |  **Precision:** 0.2572  |  **Macro F1:** 0.5533  |  **Brier:** 0.1130  |  **Threshold:** 0.1246
- **Top SHAP features:** `age` 0.8406, `gender` 0.3102
- **Flags:** LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): diet_quality, frequent_fatigue, pale_cold, lightheadedness, brittle_nails
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: diet_quality, frequent_fatigue, pale_cold, lightheadedness, brittle_nails — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `burnout`

- **Dataset:** SYNTHETIC (ml/data/generate_synthetic.py, SEED=42). A real burnout dataset exists (Mendeley 'Burnout Risks Bangladeshi Physicians', CC BY 4.0, 1434 rows) but is NOT app-aligned: Working_Hour / Dissatisfaction / Mental_Disturbances are nominal questionnaire codes, not the app's work_hours, job_satisfaction (1-5) and 3 exhaustion items (0-3). Metrics here are NOT real-world evidence; the app still serves the rule-based score_burnout() (ml/models/screening_classifier.py).
- **Rows:** 1200 (positive rate 42.83%)
- **Features (5):** work_hours, job_satisfaction, exhaustion_1, exhaustion_2, exhaustion_3
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.8180 ± 0.0253  |  **Test AUC:** 0.8773  |  **Recall:** 0.9417  |  **Precision:** 0.6382  |  **Macro F1:** 0.7448  |  **Brier:** 0.1420  |  **Threshold:** 0.1999
- **Top SHAP features:** `job_satisfaction` 0.7449, `exhaustion_3` 0.3, `exhaustion_2` 0.2977, `work_hours` 0.2621, `exhaustion_1` 0.2189
- **Flags:** SYNTHETIC_DATA
- **Status:** BELOW_TARGET
- **Limitations:**
  - SYNTHETIC DATA (ml/data/generate_synthetic.py, SEED=42) — ML_TRAINING.md Ground Rule 1 is deliberately deviated from here, at the project owner's request. Every metric in this card is produced from generated data, NOT real-world evidence.
  - All app features are present in the source dataset
  - Screening and awareness tool only, not a diagnostic device

*Trained on SYNTHETIC data (see the README) — every metric below is a property of generated data, NOT evidence of real-world performance. The app still serves the rule-based `ScreeningClassifier.score_burnout()`.*

### `ckd`

- **Dataset:** UCI Chronic Kidney Disease (400 rows) — age/bp/dm/htn mapped to app vector; swelling/urination/fatigue symptoms not in UCI (NaN).
- **Rows:** 400 (positive rate 62.50%)
- **Features (7):** age, bp_systolic, diabetes_flag, hypertension_flag, ankle_swelling, urination_changes, ckd_fatigue
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.9359 ± 0.0298  |  **Test AUC:** 0.9547  |  **Recall:** 0.9800  |  **Precision:** 0.7206  |  **Macro F1:** 0.6772  |  **Brier:** 0.0699  |  **Threshold:** 0.1556
- **Top SHAP features:** `hypertension_flag` 1.5317, `diabetes_flag` 0.9498, `bp_systolic` 0.766, `age` 0.352
- **Flags:** SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): ankle_swelling, urination_changes, ckd_fatigue
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: ankle_swelling, urination_changes, ckd_fatigue — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `colorectal`

- **Dataset:** NHANES 2017-2018 (J) MCQ_J MCQ230A-D, code 16 (colon) / 31 (rectum), age>=40 (app gate). Only 4 of the 9 app features exist in NHANES and there are just 55 cases (1.4%) -> LOW_FEATURE_MODEL + HEAVY_IMBALANCE and a weak AUC, exactly as ML_TRAINING §6 predicts for a dataset this small.
- **Rows:** 3882 (positive rate 1.42%)
- **Features (9):** age, family_cancer, diet_quality, exercise_level, smoking, alcohol, blood_in_stool, bowel_change, colorectal_weight_loss
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.5785 ± 0.0448  |  **Test AUC:** 0.6942  |  **Recall:** 0.0909  |  **Precision:** 0.0435  |  **Macro F1:** 0.5189  |  **Brier:** 0.0139  |  **Threshold:** 0.0177
- **Top SHAP features:** `age` 0.7173, `exercise_level` 0.2168, `smoking` 0.1522, `alcohol` 0.0699
- **Flags:** HEAVY_IMBALANCE, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): family_cancer, diet_quality, blood_in_stool, bowel_change, colorectal_weight_loss
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: family_cancer, diet_quality, blood_in_stool, bowel_change, colorectal_weight_loss — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `depression`

- **Dataset:** Real PHQ-9 questionnaire (776 rows, Figshare CC BY) — label = PHQ-9 total >=10 (moderate+). Label derived from the items BY DESIGN (mirrors the app's PHQ-9 severity rule); a SUSPICIOUS_POSSIBLE_LEAKAGE flag is expected.
- **Rows:** 776 (positive rate 24.74%)
- **Features (9):** phq1, phq2, phq3, phq4, phq5, phq6, phq7, phq8, phq9
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.9959 ± 0.0024  |  **Test AUC:** 0.9978  |  **Recall:** 1.0000  |  **Precision:** 0.8298  |  **Macro F1:** 0.9358  |  **Brier:** 0.0181  |  **Threshold:** 0.1802
- **Top SHAP features:** `phq3` 0.8948, `phq8` 0.8743, `phq5` 0.7854, `phq6` 0.6373, `phq7` 0.6133, `phq4` 0.6102
- **Flags:** SUSPICIOUS_POSSIBLE_LEAKAGE
- **Status:** PASS
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - All app features are present in the source dataset
  - Screening and awareness tool only, not a diagnostic device
  - SUSPICIOUS_POSSIBLE_LEAKAGE: test AUC > 0.97 — investigate before trusting

### `diabetes`

- **Dataset:** NHANES 2017-2018 (J) — label DIQ010 doctor-diagnosed diabetes; family history DIQ170. Symptoms not collected in NHANES (NaN).
- **Rows:** 3000 (positive rate 10.27%)
- **Features (14):** age, gender, bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, freq_urination, excess_thirst, weight_loss
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.8861 ± 0.0235  |  **Test AUC:** 0.8754  |  **Recall:** 0.8548  |  **Precision:** 0.3011  |  **Macro F1:** 0.6541  |  **Brier:** 0.0772  |  **Threshold:** 0.0761
- **Top SHAP features:** `age` 1.7129, `bmi` 0.6312, `family_diabetes` 0.3363, `exercise_level` 0.104, `smoking` 0.0591, `gender` 0.0555
- **Flags:** LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): family_heart, family_hypertension, family_cancer, freq_urination, excess_thirst, weight_loss
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: family_heart, family_hypertension, family_cancer, freq_urination, excess_thirst, weight_loss — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `gad7`

- **Dataset:** Real GAD-7 questionnaire (776 rows, Figshare CC BY) — label = GAD-7 total >=10 (moderate+). Label is derived from the items BY DESIGN (mirrors the clinical rule the app uses), so a SUSPICIOUS_POSSIBLE_LEAKAGE flag is expected.
- **Rows:** 776 (positive rate 24.23%)
- **Features (7):** gad1, gad2, gad3, gad4, gad5, gad6, gad7
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.9968 ± 0.0026  |  **Test AUC:** 0.9991  |  **Recall:** 1.0000  |  **Precision:** 0.7600  |  **Macro F1:** 0.9050  |  **Brier:** 0.0139  |  **Threshold:** 0.1555
- **Top SHAP features:** `gad3` 1.2859, `gad4` 0.8979, `gad1` 0.8907, `gad5` 0.8405, `gad2` 0.7315, `gad7` 0.6604
- **Flags:** SUSPICIOUS_POSSIBLE_LEAKAGE
- **Status:** PASS
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - All app features are present in the source dataset
  - Screening and awareness tool only, not a diagnostic device
  - SUSPICIOUS_POSSIBLE_LEAKAGE: test AUC > 0.97 — investigate before trusting

### `heart`

- **Dataset:** UCI Cleveland heart disease (303 rows) — age/gender/chest-pain only; Cleveland has no smoking/BMI/sleep/exercise columns (NaN). LOW_FEATURE_MODEL.
- **Rows:** 303 (positive rate 45.87%)
- **Features (14):** age, gender, bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, chest_pain, short_breath, palpitations
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.7742 ± 0.0338  |  **Test AUC:** 0.7008  |  **Recall:** 0.8214  |  **Precision:** 0.5476  |  **Macro F1:** 0.5978  |  **Brier:** 0.2210  |  **Threshold:** 0.3644
- **Top SHAP features:** `gender` 0.81, `age` 0.8068, `chest_pain` 0.5104
- **Flags:** SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, short_breath, palpitations
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, short_breath, palpitations — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `hypertension`

- **Dataset:** NHANES 2017-2018 (J) — label = measured BP (mean SBP>=130 or DBP>=80); BP deliberately excluded from features (ML_TRAINING §5 label-from-feature).
- **Rows:** 3000 (positive rate 35.23%)
- **Features (14):** age, gender, bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, headaches, dizziness, blurred_vision
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.8032 ± 0.0160  |  **Test AUC:** 0.8099  |  **Recall:** 0.9668  |  **Precision:** 0.4823  |  **Macro F1:** 0.6221  |  **Brier:** 0.1664  |  **Threshold:** 0.1117
- **Top SHAP features:** `age` 1.3899, `bmi` 0.3536, `gender` 0.2191, `sleep_hours` 0.0582, `exercise_level` 0.0291, `smoking` 0.0212
- **Flags:** LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): family_diabetes, family_heart, family_hypertension, family_cancer, headaches, dizziness, blurred_vision
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: family_diabetes, family_heart, family_hypertension, family_cancer, headaches, dizziness, blurred_vision — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `liver`

- **Dataset:** UCI ILPD liver patients (583 rows) — only age/gender app-available; ILPD has no alcohol/symptom columns. LOW_FEATURE_MODEL.
- **Rows:** 583 (positive rate 71.36%)
- **Features (7):** age, gender, bmi, alcohol, jaundice, abdominal_pain, liver_fatigue
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.6245 ± 0.0260  |  **Test AUC:** 0.6492  |  **Recall:** 0.9398  |  **Precision:** 0.7156  |  **Macro F1:** 0.4777  |  **Brier:** 0.1963  |  **Threshold:** 0.5173
- **Top SHAP features:** `age` 0.7043, `gender` 0.197
- **Flags:** LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, alcohol, jaundice, abdominal_pain, liver_fatigue
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: bmi, alcohol, jaundice, abdominal_pain, liver_fatigue — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `lung_cancer`

- **Dataset:** Kaggle lung-cancer survey (309 rows) — SMALL_DATASET; passive-smoke/blood symptoms not surveyed (NaN).
- **Rows:** 309 (positive rate 87.38%)
- **Features (7):** smoking, passive_smoke, age, family_cancer, persistent_cough, coughing_blood, breath_shortness
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.6135 ± 0.1123  |  **Test AUC:** 0.7199  |  **Recall:** 1.0000  |  **Precision:** 0.8710  |  **Macro F1:** 0.4655  |  **Brier:** 0.1066  |  **Threshold:** 0.5289
- **Top SHAP features:** `persistent_cough` 0.8049, `age` 0.6117, `smoking` 0.3624, `breath_shortness` 0.1789
- **Flags:** SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): passive_smoke, family_cancer, coughing_blood
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: passive_smoke, family_cancer, coughing_blood — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `metabolic_syndrome`

- **Dataset:** NHANES 2017-2018 (J) — IDF metabolic syndrome label (>=3 of 5). Label and features share clinical inputs BY DESIGN (documented §5 overlap); a SUSPICIOUS_POSSIBLE_LEAKAGE flag may appear.
- **Rows:** 3000 (positive rate 28.17%)
- **Features (10):** age, gender, waist_circumference, bp_systolic, bp_diastolic, diet_quality, exercise_level, doctor_high_bp, doctor_high_sugar, frequent_thirst_urination
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.9027 ± 0.0072  |  **Test AUC:** 0.8980  |  **Recall:** 0.9349  |  **Precision:** 0.5180  |  **Macro F1:** 0.7245  |  **Brier:** 0.1146  |  **Threshold:** 0.1465
- **Top SHAP features:** `waist_circumference` 1.1823, `bp_systolic` 0.6855, `doctor_high_bp` 0.5259, `doctor_high_sugar` 0.4553, `age` 0.4252, `bp_diastolic` 0.1136
- **Flags:** LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): diet_quality, frequent_thirst_urination
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: diet_quality, frequent_thirst_urination — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `obesity`

- **Dataset:** NHANES 2017-2018 (J) — label = measured BMI>=30; BMI deliberately excluded from features (ML_TRAINING §5). LOW_FEATURE_MODEL.
- **Rows:** 3000 (positive rate 30.07%)
- **Features (14):** age, gender, bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, sugary_diet, freq_hunger, hard_lose_weight
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.7272 ± 0.0244  |  **Test AUC:** 0.7218  |  **Recall:** 0.9444  |  **Precision:** 0.3881  |  **Macro F1:** 0.5362  |  **Brier:** 0.1833  |  **Threshold:** 0.1271
- **Top SHAP features:** `age` 1.3166, `gender` 0.1759, `sleep_hours` 0.071, `exercise_level` 0.0622, `smoking` 0.0498, `alcohol` 0.02
- **Flags:** LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, family_diabetes, family_heart, family_hypertension, family_cancer, sugary_diet, freq_hunger, hard_lose_weight
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: bmi, family_diabetes, family_heart, family_hypertension, family_cancer, sugary_diet, freq_hunger, hard_lose_weight — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `pcos`

- **Dataset:** Kaggle PCOS (541 rows) — Age/BMI/cycle/weight-gain/hair/acne.
- **Rows:** 541 (positive rate 32.72%)
- **Features (6):** age, bmi, irregular_periods, weight_gain, excess_hair, acne
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.8412 ± 0.0259  |  **Test AUC:** 0.8720  |  **Recall:** 0.8611  |  **Precision:** 0.5962  |  **Macro F1:** 0.7523  |  **Brier:** 0.1241  |  **Threshold:** 0.2221
- **Top SHAP features:** `weight_gain` 0.7836, `excess_hair` 0.7239, `age` 0.5263, `irregular_periods` 0.4533, `acne` 0.3403, `bmi` 0.3395
- **Flags:** none
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - All app features are present in the source dataset
  - Screening and awareness tool only, not a diagnostic device

### `sleep_apnea`

- **Dataset:** Kaggle Sleep Health & Lifestyle survey (374 rows, CC0) — Sleep Disorder==Sleep Apnea label; BMI derived from BMI category, wake_tired<-sleep quality, daytime_sleepy<-stress. SMALL_DATASET.
- **Rows:** 374 (positive rate 20.86%)
- **Features (7):** age, gender, bmi, snoring, wake_tired, witnessed_apnea, daytime_sleepy
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.9128 ± 0.0642  |  **Test AUC:** 0.9529  |  **Recall:** 1.0000  |  **Precision:** 0.7619  |  **Macro F1:** 0.9103  |  **Brier:** 0.0613  |  **Threshold:** 0.1501
- **Top SHAP features:** `bmi` 1.0679, `age` 1.0436, `daytime_sleepy` 0.4473, `gender` 0.3405, `wake_tired` 0.0737
- **Flags:** SMALL_DATASET, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): snoring, witnessed_apnea
- **Status:** PASS
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: snoring, witnessed_apnea — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `stroke`

- **Dataset:** Kaggle stroke prediction (5110 rows, fedesoriano) — age/gender/bmi/smoking plus hypertension/heart_disease history flags; TIA/speech symptoms NaN.
- **Rows:** 5110 (positive rate 4.87%)
- **Features (16):** age, gender, bmi, sleep_hours, exercise_level, smoking, alcohol, family_diabetes, family_heart, family_hypertension, family_cancer, bp_systolic, bp_diastolic, tia_symptoms, speech_difficulty, irregular_heartbeat
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.8210 ± 0.0167  |  **Test AUC:** 0.8142  |  **Recall:** 0.8200  |  **Precision:** 0.1171  |  **Macro F1:** 0.5058  |  **Brier:** 0.0433  |  **Threshold:** 0.0439
- **Top SHAP features:** `age` 2.0011, `bmi` 0.3019, `family_hypertension` 0.0933, `smoking` 0.064, `gender` 0.0481, `family_heart` 0.0268
- **Flags:** HEAVY_IMBALANCE, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): sleep_hours, exercise_level, alcohol, family_diabetes, family_cancer, bp_systolic, bp_diastolic, tia_symptoms, speech_difficulty, irregular_heartbeat
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: sleep_hours, exercise_level, alcohol, family_diabetes, family_cancer, bp_systolic, bp_diastolic, tia_symptoms, speech_difficulty, irregular_heartbeat — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

### `thyroid`

- **Dataset:** UCI hypothyroid (3163 rows) — only age/gender app-available; TSH/T3/TT4 labs are not collected by the app. LOW_FEATURE_MODEL.
- **Rows:** 3163 (positive rate 4.77%)
- **Features (7):** age, gender, bmi, fatigue, weight_change, temperature_issues, hair_skin
- **Preprocessing:** Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline (training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision threshold from out-of-fold F2 (recall-oriented). The test set is scored once.
- **CV AUC:** 0.5875 ± 0.0925  |  **Test AUC:** 0.5365  |  **Recall:** 0.6333  |  **Precision:** 0.0456  |  **Macro F1:** 0.2928  |  **Brier:** 0.0450  |  **Threshold:** 0.0421
- **Top SHAP features:** `age` 0.4859, `gender` 0.0859
- **Flags:** HEAVY_IMBALANCE, LOW_FEATURE_MODEL; columns unusable in training (all-NaN in the source): bmi, fatigue, weight_change, temperature_issues, hair_skin
- **Status:** BELOW_TARGET
- **Limitations:**
  - App-aligned projection of a real public dataset (ml/data/README.md) — not a local clinical sample; revalidate on local data before clinical use
  - Columns the source dataset never collected: bmi, fatigue, weight_change, temperature_issues, hair_skin — the app still asks these but the model cannot use them (LOW_FEATURE_MODEL)
  - Screening and awareness tool only, not a diagnostic device

