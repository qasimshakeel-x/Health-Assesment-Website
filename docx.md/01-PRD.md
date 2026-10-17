# PRD — AI Longevity Intelligence Platform

## 1. Product Vision
A full-stack AI health-intelligence platform where a user fills **one** structured health profile
(biomarkers, lifestyle, medical history, PHQ-9) and receives a complete, explainable, longitudinal
health report: disease risk across 5 categories, biological age, a single longevity score, a 10-year
future projection, and a risk-aware AI diet coach — all exportable as a clinical-grade PDF.

The platform does **not** diagnose. It estimates population-level risk using ML models trained on
public datasets, clearly disclaimed throughout.

## 2. Target Users
- Primary: health-conscious individuals with no medical background who want a plain-language,
  data-driven view of their long-term health trajectory.
- Secondary: an admin who manages user records, monitors predictions, and retrains models.

## 3. Core Value Proposition
Unlike single-purpose health apps (one disease, one calculator), every output in this platform feeds
the next: disease risks → biological age → longevity score → diet chat context → PDF report. Every
prediction is explained via SHAP, not a black box.

## 4. Original Module Set (M-1 → M-9)
| # | Module | Summary |
|---|---|---|
| M-1 | User Health Profile | One intake form, validated, saved |
| M-2 | Disease Risk Prediction | RF+XGB+LR ensemble → Diabetes, Heart Disease, Hypertension, Obesity |
| M-3 | Biological Age Estimation | Penalty-formula "body age" vs real age |
| M-4 | Longevity Score Engine | Weighted 0–100 composite score |
| M-5 | Depression Risk Detection | PHQ-9 → Gradient Boosting severity classifier |
| M-6 | Explainable AI (SHAP) | Bar + waterfall charts, top-5 plain-language factors |
| M-7 | Future Health Simulation | 10-year current-vs-improved lifestyle projection |
| M-8 | Risk-Conditional Diet Chat | Claude API, full risk profile injected as system context |
| M-9 | PDF Health Report | One-click clinical-grade export (ReportLab) |

Full detail for M-1–M-9 (formulas, business rules, data model, API, NFRs) lives in the companion
files: `02-ARCHITECTURE.md`, `03-AUTH.md`, `04-DATA-MODEL.md`, `05-API-SPEC.md`.

## 5. Expansion: Disease Coverage (16 total)
The platform expands from 4 diseases to **16**, organized into 5 dashboard categories so the UI
stays legible. Full per-disease spec (inputs, model, dataset, output) is in `05-DISEASE-MODULES.md`.

| Category | Diseases |
|---|---|
| Cardiovascular | Heart Disease, Hypertension, **Stroke**, **Metabolic Syndrome** |
| Metabolic | Diabetes, Obesity, **CKD**, **Liver Disease**, **Thyroid Disorder** |
| Mental Wellness | Depression, **Anxiety (GAD-7)**, **Burnout** |
| Lifestyle-Linked | **Sleep Apnea**, **Anemia**, **PCOS** |
| Cancer Screening | **Colorectal Cancer Risk**, **Lung Cancer Risk** |

New items are bold. Cancer screening outputs must carry an explicit "population-level estimate,
not diagnostic" disclaimer, stricter even than the general disclaimer.

### 5.1 Rollout priority
Ship incrementally, not all 16 at once:
1. **Phase 1 (already spec'd):** Diabetes, Heart Disease, Hypertension, Obesity, Depression.
2. **Phase 2 — highest ROI, lowest new-input cost:**
   - Stroke (zero new inputs, dataset ready)
   - Sleep Apnea (2 new yes/no questions, clinically validated STOP-BANG style scoring)
   - Anxiety / GAD-7 (7 standardized questions, doubles mental-health module value)
3. **Phase 3 — zero/low new-input, downstream of Phase 1 outputs:**
   - CKD (consumes Diabetes + Hypertension risk outputs)
   - Liver Disease (reuses existing alcohol field)
   - Metabolic Syndrome (needs 1 new input: waist circumference)
4. **Phase 4 — needs 2–3 new form questions:**
   - Thyroid Disorder (+1 fatigue question)
   - PCOS (female-only filter, +2 questions)
   - Anemia (+3 fatigue/diet questions)
   - Burnout (+work-hours, job-satisfaction, +3 exhaustion questions)
5. **Phase 5 — cancer screening, ship last, needs legal/clinical disclaimer review:**
   - Colorectal Cancer Risk (+0 new inputs if age≥40 gate used)
   - Lung Cancer Risk (+1 passive-smoke-exposure question)

## 6. Impact on Longevity Score (M-4)
With 16 diseases the Longevity Score moves from averaging 4 raw risk percentages to a **category-
weighted** composite: average risk is computed per category (Cardiovascular, Metabolic, Mental
Wellness, Lifestyle-Linked, Cancer Screening) first, then combined. This keeps one noisy disease
(e.g. a rare-condition false positive) from swinging the whole score, and is more defensible to a
reviewing committee than a flat average. Exact category weights are a design decision to finalize in
`05-DISEASE-MODULES.md` before Phase 2 ships — do not hardcode until reviewed.

## 7. Non-Goals
- No real-time wearable/device integration (out of scope for this version).
- No multi-language support in v1.
- No clinician-facing portal — admin panel is for platform operators, not doctors.
- Cancer modules are screening-flavor only, never diagnostic language anywhere in UI/PDF.

## 8. Success Criteria
- Disease ensembles: AUC-ROC ≥ 0.85, macro F1 ≥ 0.80 per phase before it ships.
- Depression classifier: weighted F1 ≥ 0.80, Severe-class recall ≥ 0.88.
- Full pipeline response ≤ 8s; PDF ready ≤ 10s.
- WCAG 2.1 AA pass before Phase 1 frontend ships.
- Every new disease module reuses the existing `MLModel` abstract base — no parallel pipeline.

## 9. Related Docs
- `02-ARCHITECTURE.md` — layers, patterns, class model
- `03-AUTH.md` — auth/security design
- `04-DATA-MODEL.md` — full DB schema incl. new disease tables
- `05-API-SPEC.md` — REST endpoint catalogue
- `05-DISEASE-MODULES.md` — per-disease input/model/dataset spec for all 16
- `06-DEV-WORKFLOW.md` — local setup, branching, testing, debugging playbook
