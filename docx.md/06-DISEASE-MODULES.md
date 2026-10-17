# Disease Modules — Full 16-Disease Spec

Registry format for `DISEASE_REGISTRY` (see `02-ARCHITECTURE.md` §5). Rollout order per
`01-PRD.md` §5.1. Every entry below gets one `DiseaseConfig` row.

## Dashboard Categories
| Category | Diseases |
|---|---|
| Cardiovascular | Heart Disease, Hypertension, Stroke, Metabolic Syndrome |
| Metabolic | Diabetes, Obesity, CKD, Liver Disease, Thyroid Disorder |
| Mental Wellness | Depression, Anxiety (GAD-7), Burnout |
| Lifestyle-Linked | Sleep Apnea, Anemia, PCOS |
| Cancer Screening | Colorectal Cancer Risk, Lung Cancer Risk |

---

## Phase 1 — already spec'd (see `01-PRD.md`, original SRS/SDD)
Diabetes, Heart Disease, Hypertension, Obesity (RF+XGB+LR ensemble), Depression (PHQ-9,
Gradient Boosting).

---

## Phase 2 — highest ROI, lowest new-input cost

### Stroke
- **New inputs needed:** none — age, BMI, blood-pressure indicators, smoking, family history,
  activity level already collected.
- **Model:** Logistic Regression + Random Forest
- **Dataset:** Kaggle Stroke Prediction Dataset (5,110 records, public)
- **Output:** Stroke Risk % + confidence
- **Why Phase 2:** 2nd leading global cause of death; directly connected to existing Hypertension
  and Heart Disease modules — reuses their feature set almost entirely.

### Sleep Apnea
- **New inputs needed:** "Do you snore?" (Y/N), "Do you wake up tired even after 8 hours?" (Y/N)
- **Inputs:** BMI, Age, Gender, sleep_hours (existing) + 2 new
- **Model:** Logistic Regression
- **Dataset/scoring:** STOP-BANG questionnaire scoring (clinically validated)
- **Output:** Low / Intermediate / High Sleep Apnea Risk
- **Why Phase 2:** sleep_hours already exists in the form; 2 extra questions unlock a validated
  clinical screen.

### Anxiety (GAD-7)
- **New inputs needed:** 7 standardized GAD-7 questions (own `screening_responses` row,
  `screening_key = "gad7"`)
- **Model:** scoring-based classifier on GAD-7 validated thresholds
- **Output:** Minimal / Mild / Moderate / Severe anxiety classification
- **Why Phase 2:** ~60% of people with depression also have anxiety — current mental-health
  module is missing half the picture; pairs naturally with the existing PHQ-9 flow in the same
  "Mental Wellness" UI section.

---

## Phase 3 — zero/low new-input, downstream of Phase 1 outputs

### Chronic Kidney Disease (CKD)
- **Inputs needed:** Age, BMI, **Diabetes risk output**, **Hypertension risk output**, family history
- **Model:** Random Forest + XGBoost
- **Dataset:** UCI Chronic Kidney Disease Dataset
- **Output:** CKD Risk % — Low / Moderate / High
- **Dependency:** `depends_on = ["diabetes", "hypertension"]` in the registry — must run after
  those two engines complete (see `02-ARCHITECTURE.md` §5 for the ordering mechanism).

### Liver Disease Risk
- **Inputs needed:** Age, BMI, **alcohol consumption (already collected, currently unused)**,
  family history
- **Model:** Logistic Regression + XGBoost
- **Dataset:** Indian Liver Patient Dataset (UCI, 583 records)
- **Output:** Liver Disease Risk %

### Metabolic Syndrome
- **New inputs needed:** waist circumference (one measurement)
- **Inputs:** BMI, waist circumference, blood-pressure indicators, activity level, diet quality
- **Model:** rule-based scoring + ML classifier (cluster of 5 conditions: high blood sugar, high BP,
  excess waist fat, low HDL, high triglycerides)
- **Dataset:** NHANES
- **Output:** Metabolic Syndrome Risk Score
- **Why valuable:** predicts CVD, diabetes, and stroke simultaneously — one prediction, multiple
  pathways. Lives in the Cardiovascular category per the dashboard grouping.

---

## Phase 4 — needs 2–3 new form questions

### Thyroid Disorder
- **New inputs needed:** fatigue level (1 new question)
- **Inputs:** Age, Gender, BMI, fatigue, family history
- **Model:** Random Forest
- **Dataset:** UCI Thyroid Disease Dataset
- **Output:** Hypothyroid / Hyperthyroid / Normal classification
- **Note:** heavily affects biological age and energy levels — feed into `BioAgeEngine` penalty
  calculation as a future enhancement.

### PCOS (Polycystic Ovary Syndrome)
- **New inputs needed:** gender filter (female only — gate the module), irregular periods (Y/N),
  unexplained weight gain (Y/N)
- **Inputs:** Age, BMI, 2 new questions, family history
- **Model:** Logistic Regression + Random Forest
- **Dataset:** Kaggle PCOS Dataset
- **Output:** PCOS Risk % + symptom flags
- **UI note:** only render this module's intake fields when `gender == Female` — don't show it as a
  blank/irrelevant section to male users.

### Anemia
- **New inputs needed:** 3 questions — frequent fatigue, pale skin / feels cold often, (+ diet
  quality signal)
- **Inputs:** Gender, Age, diet quality, fatigue indicators
- **Model:** Decision Tree + Random Forest
- **Dataset:** WHO Anemia criteria + Kaggle Anemia Dataset
- **Output:** Anemia Risk % + dietary iron-deficiency flag
- **Integration point:** if anemia risk is elevated, `DietChatEngine` context injection must add an
  iron-rich-foods rule — same pattern as the existing Diabetes/Hypertension diet rules in
  `01-PRD.md`/original SDD §5.3.

### Burnout
- **New inputs needed:** work hours/week, job satisfaction (1–5 scale), 3 PHQ-style emotional-
  exhaustion questions
- **Model:** scoring-based classifier
- **Output:** No Burnout / At Risk / Burnout Detected
- **Why it matters:** WHO-classified occupational phenomenon; affects sleep, depression, heart
  disease, immune function — all things the platform already measures, strengthens cross-module
  narrative in the PDF report.

---

## Phase 5 — cancer screening (ship last, needs disclaimer/legal review)

> Every output in this phase must carry, in addition to the standard disclaimer, an explicit
> "population-level risk estimate, not a diagnostic tool" statement — in the API response, the
> dashboard card, and the PDF. Do not phase this in without that copy reviewed and in place.

### Colorectal Cancer Risk
- **Inputs:** Age (40+ gate), family history of colorectal cancer, diet quality (red meat
  consumption), physical activity, smoking, alcohol — all largely already collected
- **Model:** Logistic Regression
- **Dataset:** CDC SEER data / Kaggle Cancer Risk Dataset
- **Output:** Low / Moderate / High lifetime risk estimate

### Lung Cancer Risk
- **New inputs needed:** passive smoke exposure (1 new question)
- **Inputs:** smoking status (existing, currently only feeds Heart Disease), age, family history, +1 new
- **Model:** Random Forest
- **Dataset:** NLST (National Lung Screening Trial)-derived features
- **Output:** risk classification + smoking-cessation urgency flag

---

## Longevity Score Impact
Once Phase 2+ ships, `LongevityScoreEngine` must move from averaging 4 flat risk percentages to
the category-weighted model described in `01-PRD.md` §6 — average risk per category first, then
combine categories. Finalize category weights with the supervisor/committee before Phase 2's
Stroke module ships, since it's the first new category member (Cardiovascular) to land.
