# ML Training Spec — AI Longevity Intelligence Platform

Covers training pipeline, feature engineering, and algorithm pseudocode (PDL) for every model in
the platform — Phase 1 (original 5) and Phase 2–5 (the 16-disease expansion).

## 1. General Training Pipeline (applies to every disease/screening model)
```
1. Load dataset (public source — see per-model table below)
2. Clean: handle missing values, drop/impute per dataset's standard practice
3. Feature engineer: derive BMI, normalize numeric ranges, encode categoricals
4. Split: 80% train / 20% held-out test (stratified on target class)
5. Apply SMOTE on the training split only (never on the test split) if classes are imbalanced
6. Train model(s) per the Strategy-pattern interface: fit(X_train, y_train)
7. Evaluate on held-out test: AUC-ROC, F1 (macro/weighted as specified), confusion matrix
8. If thresholds met (see 06-DISEASE-MODULES.md / 07-DEV-WORKFLOW.md §4) → serialize to .pkl
9. Register in DISEASE_REGISTRY with its category, dependencies, and feature list
10. Write a model card: training date, dataset version, metrics, known limitations
```
All training scripts live outside the FastAPI runtime (offline, `/training/` directory — see
`10-PROJECT-STRUCTURE.md`). The API only ever loads pre-trained `.pkl` files at startup.

## 2. Phase 1 Algorithms (PDL)

### Disease Risk Ensemble (Diabetes / Heart / Hypertension / Obesity)
```
Algorithm DiseaseRiskPrediction
Input: User Health Profile
Output: Disease Risk Probabilities
Begin
  1. Extract health features from profile
  2. Normalize feature values
  3. Apply Random Forest → RF_result
  4. Apply XGBoost → XGB_result
  5. Apply Logistic Regression → LR_result
  6. For each disease:
     Probability = 0.40×RF_result + 0.40×XGB_result + 0.20×LR_result
     Category: <25% Low | 25–50% Moderate | 50–75% High | >75% Very High
  7. Generate SHAP explanation values (TreeExplainer on the RF model)
  8. Return probabilities + explanations
End
```

### Longevity Score
```
Algorithm CalculateLongevityScore
Input: User Profile, Disease Risks (category-grouped, see note below)
Output: Longevity Score, Health Category
Begin
  1. Calculate BMI Score, Sleep Score, Activity Score, Mental Health Score, Disease Risk Score
  2. LongevityScore = BMI(0.20) + Sleep(0.15) + Activity(0.20) + Mental(0.20) + Risk(0.25)
  3. Category: <40 Poor | 40–60 Moderate | 60–80 Good | >80 Excellent
  4. Return score + category
End
```
> **Update for 16-disease expansion:** step 1's "Disease Risk Score" must become the average of
> the 5 per-category averages (Cardiovascular, Metabolic, Mental Wellness, Lifestyle-Linked,
> Cancer Screening), not a flat average across however many diseases happen to be active — see
> `01-PRD.md` §6 and `06-DISEASE-MODULES.md` final note. Finalize exact category weights with
> the supervisor before this changes from the Phase-1 flat average.

### Biological Age
```
Algorithm EstimateBiologicalAge
Input: User Profile
Output: Biological Age, Age Difference
Begin
  1. BiologicalAge = ChronologicalAge
  2. For each risk factor (BMI deviation from 22, smoking, alcohol, sleep <6h, activity below max,
     family history, mental health, average disease risk):
     Add/subtract predefined penalty value
  3. AgeDifference = BiologicalAge − ChronologicalAge
  4. Return BiologicalAge, AgeDifference
End
```

### Depression (PHQ-9) — 5-tier, authoritative version (see `01-PRD.md` open-items note)
```
Algorithm PHQ9Classification
Input: PHQ-9 Responses (9 items, 0–3 each)
Output: Depression Level, Confidence Score
Begin
  1. Sum all 9 responses (0–27)
  2. Classify:
     0–4   → No Depression
     5–9   → Mild
     10–14 → Moderate
     15–19 → Moderately Severe
     20–27 → Severe
  3. Identify contributing symptoms (highest-scoring individual items)
  4. Calculate confidence score (model probability of predicted class)
  5. Return level, confidence, contributing symptoms
  6. If level == Severe → flag for crisis-resource surfacing in the API response
End
```

### Future Health Simulation
```
Algorithm FutureHealthSimulation
Input: Current Profile, Lifestyle Changes, Prediction Horizon
Output: Future Health Projection
Begin
  1. Load current profile
  2. Apply lifestyle deltas: weight reduction, increased exercise, improved sleep,
     smoking cessation, dietary improvement
  3. Recalculate: Disease Risks, Biological Age, Longevity Score (re-run Phase-1+active-phase
     engines against the modified profile)
  4. Compare projected vs current
  5. Return projected outcomes for both scenarios (Current, Improved)
End
```

### Diet Chat Context Injection
```
Algorithm GenerateDietChatContext
Input: User ID
Output: Personalized system prompt for Claude API
Begin
  1. Retrieve user profile + latest disease_risk_results + depression/anxiety levels
  2. Initialize base dietary guidance
  3. If Diabetes risk > 50% → add low-sugar / no-high-GI rules
  4. If Hypertension risk > 40% → add DASH diet recommendations
  5. If Cardiovascular (composite) risk > 45% → add Mediterranean diet recommendations
  6. If Depression level is Moderate or worse → add magnesium-rich food recommendations
  7. If Anemia risk is elevated (once Phase 4 ships) → add iron-rich food recommendations
  8. Append medical disclaimer + "consult a registered dietitian" footer rule
  9. Generate final system prompt, return with greeting message
End
```

## 3. Phase 2–5 Model Notes (summary — full input/dataset detail in `06-DISEASE-MODULES.md`)
| Disease | Model(s) | Key training note |
|---|---|---|
| Stroke | LR + RF | Reuses most Phase-1 features; verify no leakage from Hypertension/Heart labels if datasets overlap |
| Sleep Apnea | LR | Use STOP-BANG scoring as a validated feature, not just a raw yes/no |
| GAD-7 (Anxiety) | Scoring classifier | Threshold-based, can start as rule-based scoring before an ML upgrade |
| CKD | RF + XGB | **Input includes Diabetes/Hypertension risk outputs** — train on simulated or real ensemble outputs, not just raw labels, to match production inference inputs |
| Liver Disease | LR + XGB | Small dataset (583 records) — watch for overfitting, use cross-validation not a single split |
| Metabolic Syndrome | Rule-based + ML | Rule-based component (5-condition cluster) should be implemented first and validated against clinical criteria before the ML layer is added |
| Thyroid | RF | Fatigue is self-reported — document as a soft signal, not a hard clinical marker |
| PCOS | LR + RF | Train/serve only for `gender == Female`; exclude male records from training entirely |
| Anemia | Decision Tree + RF | WHO criteria should define the ground-truth labels, not just the Kaggle dataset's raw labels |
| Burnout | Scoring classifier | Start rule-based (like Metabolic Syndrome); revisit ML upgrade only if enough labeled data is available |
| Colorectal Cancer | LR | Age ≥40 gate — do not run/display for under-40 profiles |
| Lung Cancer | RF | Smoking status already exists — this model should meaningfully outperform a naive "smoker = high risk" baseline or it isn't worth shipping |

## 4. Validation Thresholds (gate for entering `DISEASE_REGISTRY`)
| Model | Metric | Minimum |
|---|---|---|
| Any disease ensemble | AUC-ROC | ≥ 0.85 |
| Any disease ensemble | F1 (macro) | ≥ 0.80 |
| Depression (PHQ-9) | F1 (weighted) | ≥ 0.80 |
| Depression, Severe class | Recall | ≥ 0.88 |
| Bio Age | MAE vs reference formula | ≤ 3.0 years |
| SHAP | Top-3 features clinically plausible | manual review pass |
| New Phase 2–5 models | Same AUC/F1 bar as Phase 1 unless explicitly scoring-based (rule-based modules are reviewed for clinical correctness instead of AUC) |

A model that doesn't meet its threshold does not get registered — ship the platform without that
disease rather than with an unreliable one (see `01-PRD.md` §5.1 phased rollout — this is exactly
why diseases are phased rather than all-at-once).

## 5. Dataset Source Reference
| Dataset | Used for | Source |
|---|---|---|
| PIMA Indians Diabetes | Diabetes | Kaggle / NIDDK |
| UCI Heart Disease | Heart Disease, feeds Stroke | UCI ML Repository |
| UCI Hypertension | Hypertension, feeds Stroke/CKD | UCI ML Repository |
| NHANES Biomarker Data | Bio-age calibration, Metabolic Syndrome | CDC / Kaggle |
| PHQ-9 dataset | Depression | generated via `train_models.py` if no fitting public set exists |
| GAD-7 scoring | Anxiety | clinically validated threshold scoring, not necessarily an ML dataset |
| Kaggle Stroke Prediction Dataset | Stroke | Kaggle (5,110 records) |
| UCI Chronic Kidney Disease | CKD | UCI ML Repository |
| Indian Liver Patient Dataset | Liver Disease | UCI (583 records) |
| UCI Thyroid Disease Dataset | Thyroid | UCI ML Repository |
| Kaggle PCOS Dataset | PCOS | Kaggle |
| WHO Anemia criteria + Kaggle Anemia Dataset | Anemia | WHO / Kaggle |
| CDC SEER / Kaggle Cancer Risk Dataset | Colorectal Cancer | CDC / Kaggle |
| NLST-derived features | Lung Cancer | National Lung Screening Trial |
| SMOTE (imbalanced-learn) | Class balancing | applied to M-2 and M-5, and any new imbalanced classifier |
