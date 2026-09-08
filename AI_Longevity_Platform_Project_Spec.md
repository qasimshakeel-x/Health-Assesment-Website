# AI Longevity Intelligence Platform — Project Build Spec

> Combined from: SRS (Software Requirements Specification) + SDD (Software Design Description)
> Purpose: Give this file to a coding agent (Claude Code, Cursor, etc.) as the single source of truth to scaffold and build the project.

---

## 1. Project Summary

A full-stack AI-powered health intelligence platform. The user fills **one** structured health form
(biomarkers, lifestyle, medical history, PHQ-9 mental health questionnaire) and the system runs it
through a multi-model ML pipeline to produce a complete, explainable, actionable health report.

Nine interconnected modules, each output feeding the next:

| # | Module | What it does |
|---|--------|---------------|
| M-1 | User Health Profile | Intake form, validation, save to DB |
| M-2 | Disease Risk Prediction | RF + XGBoost + Logistic Regression ensemble → Diabetes, Heart Disease, Hypertension, Obesity risk % |
| M-3 | Biological Age Estimation | Penalty-based formula → "body age" vs real age |
| M-4 | Longevity Score Engine | Weighted 0–100 composite health score |
| M-5 | Depression Risk Detection | PHQ-9 questionnaire → Gradient Boosting classifier → severity level |
| M-6 | Explainable AI (SHAP) Dashboard | SHAP TreeExplainer bar charts, "why" behind every risk score |
| M-7 | Future Health Simulation | 10-year projection: current lifestyle vs improved lifestyle |
| M-8 | Risk-Conditional Diet Plan Chat | Anthropic Claude API, injected with full risk profile as system context, before user types anything |
| M-9 | PDF Health Report Generation | One-click clinical-grade PDF via ReportLab |

The platform does **not** diagnose disease — it estimates risk using ML models trained on public
datasets (Kaggle, UCI, NHANES/CDC).

---

## 2. Tech Stack (fixed constraints — do not substitute)

| Layer | Technology |
|---|---|
| Frontend | React.js 18+, Tailwind CSS 3, Recharts + Chart.js |
| Backend | Python 3.11+, FastAPI 0.110+, Uvicorn ASGI |
| ML — classification | Scikit-learn 1.4+, XGBoost 2.x (no deep learning frameworks) |
| ML — explainability | SHAP 0.45+ (TreeExplainer only) |
| ML — class balancing | imbalanced-learn 0.12+ (SMOTE) |
| AI Chat | Anthropic Claude API (Claude 3 Sonnet referenced in SDD — use current model string) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x + Alembic migrations |
| Cache | Redis 7.x (30-min prediction cache) |
| PDF | ReportLab 4.x (server-side) |
| Auth | JWT (python-jose, HS256), 24h access token / 7-day refresh token, bcrypt password hashing |
| HTTP client (frontend) | Axios |
| Deployment | Frontend → Vercel; Backend → Render.com; DB → Railway.app; or local Docker Compose |
| Containerization | 2 Docker containers: FastAPI (python:3.11-slim) + React/Nginx (node:20) |

**Design constraints:**
- All ML inference runs server-side; nothing heavy on the client.
- All training datasets must be public (Kaggle, UCI, NHANES, CDC).
- Anthropic API key must be an environment variable only — never in frontend code or repo.
- PDF must be generated with ReportLab only.
- Depression module must always show a prominent medical disclaimer.
- Responsive from 375px (mobile) to 1920px (desktop).
- Internet required only for the diet-chat module (Claude API); everything else works offline.

---

## 3. Architecture (Layered MVC)

```
PRESENTATION LAYER (React.js 18 + Tailwind)
  ↓ HTTPS / REST (JWT bearer)
APPLICATION LAYER (FastAPI — routes, JWT middleware, Pydantic v2 schemas,
                    ML Pipeline Orchestrator, Context Injector, Report Controller)
  ↓
ML / BUSINESS LOGIC LAYER (RandomForest, XGBoost, LogisticRegression,
                            SHAP Explainer, PHQ-9 GradBoost Classifier,
                            Bio Age Engine, Longevity Score Engine,
                            Future Simulator, Anthropic Claude client)
  ↓
DATA PERSISTENCE LAYER (PostgreSQL 16 + SQLAlchemy 2.x + Alembic,
                         Redis session/result cache, ReportLab PDF output)
```

Each layer only talks to the layer directly next to it (no skipping layers).

### Design patterns to use
- **Strategy** — RF / XGB / LR are interchangeable strategies behind a common `predict_proba()` interface.
- **Facade** — `MLPipelineOrchestrator.run_pipeline()` is the single entrypoint FastAPI calls; it hides the 3 models + SHAP + persistence.
- **Observer** — Future Simulator recalculates on frontend slider change without hitting the backend (client-side cached coefficients).
- **OOP base class** — `MLModel` abstract base (`train()`, `evaluate()`) → `DiseaseRiskEngine` and `DepressionClassifier` inherit from it.
- **Composition** — `UserProfile` contains `PHQ9Response`.
- **Aggregation** — `PDFReportGenerator` aggregates outputs of all other module classes.

### Core domain classes
`UserProfile`, `MLModel` (abstract), `DiseaseRiskEngine(MLModel)`, `DepressionClassifier(MLModel)`,
`BioAgeEngine`, `LongevityScoreEngine`, `FutureSimulator`, `DietChatEngine`, `SHAPDashboard`, `PDFReportGenerator`.

---

## 4. Functional Requirements (detailed)

### FR-1 — Patient Health Data Entry & Validation
Structured intake form: name, age (18–120), gender, height (cm), weight (kg), sleep hours (3–12),
exercise level (0–4), smoking status, alcohol level (0–7), family history of Diabetes / Heart Disease /
Hypertension / Cancer (booleans), and all 9 PHQ-9 answers (0=Never, 1=Several days, 2=More than
half the days, 3=Nearly every day). All fields validated before pipeline runs.

### FR-2 — ML-Based Disease Risk Ensemble Classification
Ensemble of RF (40%) + XGBoost (40%) + Logistic Regression (20%) predicts risk % for Diabetes,
Heart Disease, Hypertension, Obesity.

```
Probability = 0.40×RF + 0.40×XGB + 0.20×LR

Risk category:
  <25%        → Low Risk
  25–50%      → Moderate Risk
  50–75%      → High Risk
  >75%        → Very High Risk
```
Trained on public Kaggle/UCI/NHANES datasets, SMOTE applied for class balance. Target: AUC-ROC ≥ 0.85, macro F1 ≥ 0.80.

### FR-3 — Biological Age Estimation
```
BiologicalAge = ChronologicalAge + Σ(penalties)
penalties from: BMI deviation from 22, each hr sleep below 6,
  each exercise level below max(4), smoking, alcohol, family history,
  average disease risk score
AgeDifference = BiologicalAge − ChronologicalAge
```
Always displayed next to real age; gap clearly labeled positive/negative.

### FR-4 — Longevity Score Engine
```
LongevityScore = BMI(20%) + Sleep(15%) + Exercise(20%) + AvgDiseaseRisk(25%) + Depression(20%)
Categories: 0–39 Poor | 40–59 Moderate | 60–79 Good | 80–100 Excellent
```

### FR-5 — Depression Risk Detection (PHQ-9)
Sum of 9 PHQ-9 answers (0–27) → Gradient Boosting classifier.
```
0–4   → No Depression
5–9   → Mild
10–14 → Moderate
15–19 → Moderately Severe   (SDD version has 5 tiers; SRS has 4 — reconcile: use 5-tier SDD version)
20–27 → Severe
```
Output: severity label, confidence %, contributing risk factors, tiered intervention recommendations.
**Always show disclaimer:** "This tool does not diagnose depression. It estimates risk only."
Severe classification must prominently surface crisis resources.
Target: weighted F1 ≥ 0.80, Severe-class recall ≥ 0.88.

> ⚠️ Build note: this module screens for depression risk and must be implemented with real clinical
> care — accurate crisis-resource surfacing for severe results, no dismissive copy, and the disclaimer
> must render on every relevant screen, not just once.

### FR-6 — Explainable AI (SHAP) Dashboard
SHAP `TreeExplainer` on the Random Forest model → horizontal bar chart per disease + waterfall plot.
Dark bars = increase risk, light bars = decrease risk. Top 5 factors listed in plain language.

### FR-7 — Future Health Simulation
10-year projection, two scenarios:
- **A. Current lifestyle** — no change.
- **B. Improved lifestyle** — sleep 8h, exercise 4/4, BMI −3, no smoking, minimal alcohol.

Both show projected Biological Age, Diabetes Risk, Heart Risk, Longevity Score as grouped bar chart.
Frontend recalculates in real time via sliders (year horizon 1/5/10, sleep +0–3h, activity +0–2 levels,
smoking cessation toggle, diet improvement none/moderate/strict) using cached model coefficients —
no API round-trip needed for slider changes.

### FR-8 — Risk-Conditional Diet Plan Chat
Full risk profile injected into Claude API **system context** before the user sends a single message.

```
Context injection rules:
  Diabetes risk > 50%        → add low-sugar / no high-GI food rules
  Hypertension risk > 40%    → add DASH diet recommendations
  Cardiovascular risk > 45%  → add Mediterranean diet recommendations
  Depression = Moderate/Severe → add magnesium-rich food recommendations
  Always append medical disclaimer to every response
```
Conflicting/contraindicated food requests must be flagged with safer alternatives (yellow alert UI).
Every AI response ends with: "Consult a registered dietitian."

### FR-9 — PDF Health Report Generation
One-click download containing: cover page, health summary, disease risks, biological age, longevity
score, depression assessment, SHAP explanations, 10-year simulation, diet plan summary, medical
disclaimers on every page. Must generate within 10 seconds (async via FastAPI `BackgroundTask`,
frontend polls `/api/v1/reports/{id}/status`).

---

## 5. Data Model (PostgreSQL 16, 3NF, SQLAlchemy 2.x + Alembic)

### `user_profiles`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| name | VARCHAR(100) | |
| age | INTEGER | 18–120 |
| gender | INTEGER | 0=Female, 1=Male |
| height, weight | FLOAT | cm, kg |
| bmi | FLOAT | computed: weight / (height/100)² |
| sleep_hours | FLOAT | 3.0–12.0 |
| exercise_level | INTEGER | 0–4 |
| smoking | BOOLEAN | |
| alcohol | INTEGER | 0–7 drinks/week |
| family_history | INTEGER[] | [diabetes, heart, hypertension, cancer] flags |
| phq1..phq9 | INTEGER[9] (JSONB) | 0–3 each |
| created_at | TIMESTAMP | |

### `prediction_results`
id PK, `user_id` FK → user_profiles, diabetes_risk / heart_risk / hypertension_risk / obesity_risk
(FLOAT 0–100), biological_age (FLOAT), longevity_score (FLOAT 0–100), depression_level
(VARCHAR — No/Mild/Moderate/Mod-Severe/Severe), depression_confidence (FLOAT), created_at.

### `shap_explanations`
id PK, `prediction_id` FK → prediction_results, disease (VARCHAR), feature_name (VARCHAR),
shap_value (FLOAT −1.0 to +1.0), rank (INT). Up to 14 features × 4 diseases = 56 rows per prediction.

### `chat_sessions`
id PK, `prediction_id` FK → prediction_results (lazy-created on first message), messages (JSONB —
array of `{role, content, timestamp}`), system_prompt (TEXT), created_at, last_message_at.

### `report_log`
id PK, `user_id` FK → user_profiles, pdf_path (VARCHAR 512), generated_at, file_size_kb,
status (success/failed).

Relationships: `user_profiles` 1—N `prediction_results` 1—N `shap_explanations`;
`prediction_results` 1—1(lazy) `chat_sessions`; `user_profiles` 1—N `report_log`.

### Datasets to use for training
| Dataset | Used for | Source |
|---|---|---|
| PIMA Indians Diabetes | Diabetes classifier | Kaggle / NIDDK |
| UCI Heart Disease | Cardiovascular risk | UCI ML Repository |
| UCI Hypertension | Hypertension risk | UCI ML Repository |
| NHANES Biomarker Data | Bio-age calibration | CDC / Kaggle |
| PHQ-9 dataset | Depression classifier | generate synthetic via `train_models.py` if no public one fits |
| — | Class balancing | SMOTE (imbalanced-learn), on M-2 and M-5 |

---

## 6. REST API (all under `/api/v1`, OpenAPI docs auto at `/docs`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register user |
| POST | `/auth/login` | No | Returns access + refresh JWT |
| POST | `/auth/refresh` | No (refresh token) | Rotates refresh token, issues new access token |
| POST | `/predict` | Yes | Submit health profile, runs full ML pipeline |
| GET | `/predict/{userId}/latest` | Yes | Latest prediction results |
| GET | `/shap/{predictionId}` | Yes | SHAP values for a prediction |
| GET | `/simulate` | Yes | Future health simulation with lifestyle deltas |
| POST | `/chat/{userId}/message` | Yes | Send message to diet chatbot |
| GET | `/chat/{userId}/history` | Yes | Chat history |
| POST | `/reports/{userId}/generate` | Yes | Trigger async PDF generation (returns 202) |
| GET | `/reports/{reportId}/status` | Yes | Poll generation status |
| GET | `/reports/{reportId}/download` | Yes | Download finished PDF |

**Auth flow:** login → bcrypt password check → issue access (24h) + refresh (7d) JWT (HS256, python-jose)
→ protected routes use `Depends(get_current_user)` → 401 on invalid/expired → client calls
`/auth/refresh` → old refresh token invalidated, new one issued (rotation).

---

## 7. Non-Functional Requirements

**Performance**
- Full 9-module pipeline returns within 8 seconds (use `asyncio.gather()` to run Disease Risk / Bio Age /
  Depression / Longevity concurrently — ~3.2× speedup).
- Diet chat responds within 5 seconds under normal API conditions.
- 95% of pages load within 4 seconds.
- PDF ready within 10 seconds (async `BackgroundTask` + polling).
- Models + SHAP explainer pre-loaded once at FastAPI startup (`lifespan` event) — no per-request load.
- Redis caches prediction results 30 minutes per user.
- B-tree indexes on `user_profiles.id`, `prediction_results.user_id`; hash index on `chat_sessions.prediction_id`.

**Reliability**
- One module failing must not block the others — display partial results with a note.
- No crash on empty inputs — highlight fields, block submission, wait for correction.
- All `.pkl` model files pre-loaded at startup.
- If Anthropic API is down, diet chat shows a graceful fallback; other modules unaffected.

**Security**
- HTTPS + TLS 1.3 in production everywhere (frontend↔backend, backend↔DB).
- JWT bearer auth on all protected routes; python-jose, HS256.
- Anthropic key + DB URL + JWT secret via environment variables only.
- SQLAlchemy ORM parameterized queries everywhere; raw SQL forbidden.
- CORS restricted to the registered frontend origin only.
- Privacy notice shown before any health data entry.
- Encryption at rest (PostgreSQL pgcrypto/TDE) and in transit (TLS 1.3, cert pinning).
- React DOMPurify on any rendered user input (XSS prevention).

**Usability / Accessibility**
- Full assessment completable in under 10 minutes with no instructions.
- Plain-language results, no unexplained medical jargon.
- Actionable error messages (what's wrong + how to fix).
- Responsive 375px–1920px.
- Loading indicators everywhere ML is running — no blank screens.
- WCAG 2.1 AA: keyboard navigation, ARIA labels, `aria-describedby` on error messages.

**Error handling** (FastAPI exception handlers + structured JSON logging to stdout)
| Error | HTTP | User message |
|---|---|---|
| Invalid form input | 422 | Field-specific inline errors |
| Auth failure | 401 | "Session expired. Please log in again." |
| Model not loaded | 503 | "Health assessment service temporarily unavailable." |
| Claude API timeout (30s) | 504 | "Diet advisor is temporarily unavailable. Please try again." |
| DB connection error | 500 | "Unable to save your results. Please try again." |
| PDF generation failure | 500 | "PDF generation failed. Your results are saved and visible on screen." |

Log every WARNING+ with: ISO-8601 timestamp, request_id (UUID), user_id, endpoint, error_type, stack_trace.

---

## 8. UI Screens

1. **Health Profile Form** — age/gender/height/weight (auto-BMI), sleep slider (3–12), exercise select,
   smoking toggle, alcohol select, family history checkboxes, PHQ-9 (9 rows, 0–3 radio), Submit.
2. **Risk Dashboard** — 4 gauge charts (color-coded risk zones), bio-age comparison card, longevity
   score meter with badge, Download PDF + Open Diet Chat buttons. Yellow warning banner on any
   risk > 60%: *"This is an AI prediction, not a medical diagnosis. Consult a qualified doctor."*
3. **SHAP Explainability Dashboard** — per-disease accordion, horizontal bar chart + waterfall plot,
   green(protective)/red(risk-increasing) color coding, plain-language top-5 list.
4. **Future Health Simulator** — Current vs Improved dual panel, sliders, year-horizon selector,
   instant client-side recalculation.
5. **Diet Chat** — chat bubble UI, risk-context badge ("High Diabetes Risk Active"), typing indicator,
   yellow conflict-warning cards for contraindicated foods.

Palette: primary `#2E7D32`, accent `#81C784` (green medical theme).

Admin panel (UC-6, optional/secondary scope): view user profiles & predictions, delete records,
trigger model retraining, all actions logged with timestamp, 401 on unauthorized access.

---

## 9. Testing Targets

- Unit tests (pytest + pytest-cov), ≥85% line coverage per module class:
  `UserProfile`, `DiseaseRiskEngine`, `BioAgeEngine`, `LongevityScoreEngine`, `DepressionClassifier`,
  `DietChatEngine`, `PDFReportGenerator`, `FutureSimulator`, `SHAPDashboard`.
- Integration tests (FastAPI `TestClient` + Docker test Postgres): full predict pipeline, SHAP
  persistence, diet chat with risk injection, PDF generation flow, JWT protection, future simulator.
- ML validation (held-out 20% split): Disease ensemble AUC-ROC ≥0.85 & macro F1 ≥0.80; Depression
  classifier weighted F1 ≥0.80 & Severe-class recall ≥0.88; Bio Age MAE ≤3.0 years vs reference formula;
  SHAP top-3 features manually reviewed against clinical literature.

---

## 10. Suggested Build Order (maps to original 6-sprint plan)

1. **Sprint 1** — Repo scaffold, Postgres schema + Alembic, dataset collection/cleaning, Docker Compose skeleton.
2. **Sprint 2** — Train RF+XGB+LR disease ensemble, SHAP integration, hit AUC-ROC ≥0.85.
3. **Sprint 3** — Bio Age engine, Longevity Score engine, PHQ-9 depression classifier (F1 ≥0.80).
4. **Sprint 4** — FastAPI backend: all REST endpoints, JWT auth middleware, Pydantic v2 schemas, PDF generator — testable via Swagger `/docs`.
5. **Sprint 5** — React frontend: all 5 screens, dashboard charts, diet chat UI wired to Claude API, WCAG 2.1 AA pass.
6. **Sprint 6** — Integration tests, ML validation, deployment (Vercel/Render/Railway or Docker Compose), docs.

---

## 11. Open items to decide before/while building
- Depression severity tiers: SRS says 4 tiers, SDD says 5 (adds "Moderately Severe" 15–19). **Use the SDD 5-tier version** as authoritative (it's the more detailed/later document).
- Admin auth model (separate role flag vs separate table) — not fully specified, pick simplest (role column on a users/admins table).
- Exact Claude model string for the diet chat — confirm current available model at build time rather than hardcoding an old one.
