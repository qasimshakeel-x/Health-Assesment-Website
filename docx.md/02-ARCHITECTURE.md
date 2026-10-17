# Architecture — AI Longevity Intelligence Platform

## 1. Tech Stack (fixed)
| Layer | Technology |
|---|---|
| Frontend | React.js 18+, Tailwind CSS 3, Recharts + Chart.js, Axios |
| Backend | Python 3.11+, FastAPI 0.110+, Uvicorn ASGI |
| ML — classification | Scikit-learn 1.4+, XGBoost 2.x (no deep learning) |
| ML — explainability | SHAP 0.45+ (TreeExplainer only) |
| ML — balancing | imbalanced-learn 0.12+ (SMOTE) |
| AI Chat | Anthropic Claude API — confirm current model string at build time |
| Database | PostgreSQL 16 |
| ORM / migrations | SQLAlchemy 2.x + Alembic |
| Cache | Redis 7.x |
| PDF | ReportLab 4.x (server-side only) |
| Auth | JWT — see `03-AUTH.md` |
| Deployment | Vercel (frontend) / Render.com (backend) / Railway.app (DB), or Docker Compose locally |
| Containers | `python:3.11-slim` (FastAPI) + `node:20` → Nginx (React) |

## 2. Layered MVC Architecture
```
PRESENTATION LAYER (View)
  React.js 18 + Tailwind | Chart.js + Recharts | SHAP visualizations
  Diet Chat UI | PDF download | Future Simulator sliders
        │  HTTPS/REST, JWT bearer
        ▼
APPLICATION LAYER (Controller — FastAPI)
  Routes | JWT Auth Middleware (python-jose) | Pydantic v2 schemas
  ML Pipeline Orchestrator | Context Injector | Report Controller
        │
        ▼
ML / BUSINESS LOGIC LAYER (Model)
  RandomForest / XGBoost / LogisticRegression per-disease models
  SHAP Explainer | PHQ-9 / GAD-7 / STOP-BANG classifiers
  Bio Age Engine | Longevity Score Engine | Future Simulator
  Anthropic Claude client (diet chat only — the single external API call)
        │
        ▼
DATA PERSISTENCE LAYER
  PostgreSQL 16 + SQLAlchemy 2.x + Alembic
  Redis 7.x (30-min prediction cache)
  ReportLab 4.x (PDF output)
```
**Rule:** a layer only talks to the layer directly adjacent to it. Presentation never calls the ML layer
directly; it always goes through FastAPI. This keeps each layer independently testable and swappable.

## 3. Design Patterns
- **Strategy** — every disease model (RF / XGB / LR, and later Decision Tree / rule-based scorers for
  Group 2–4 diseases) implements a common `predict_proba()` interface so the ensemble voter treats
  them interchangeably.
- **Facade** — `MLPipelineOrchestrator.run_pipeline()` is the single entrypoint FastAPI calls. It hides
  every disease engine, SHAP explainer, and persistence call behind one method. **This is the
  integration point for all new diseases** — adding a disease means registering a new engine with
  the orchestrator, not touching the FastAPI route.
- **Observer** — Future Simulator recalculates on frontend slider change using cached model
  coefficients, no backend round-trip.
- **Template method via abstract base** — `MLModel` (`train()`, `evaluate()`, `predict_proba()`) is the
  parent for every classifier class, old and new.
- **Composition** — `UserProfile` composes `PHQ9Response`, and (new) `GAD7Response`, optional
  disease-specific sub-forms (e.g. `PCOSScreeningResponse`), so new per-disease inputs don't bloat
  the core `UserProfile` object.
- **Aggregation** — `PDFReportGenerator` aggregates outputs from every module class.

## 4. Core Domain Classes
```
MLModel (abstract: train(), evaluate(), predict_proba())
 ├── DiseaseRiskEngine(MLModel)        # multi-disease ensemble, category-aware
 ├── DepressionClassifier(MLModel)     # PHQ-9
 ├── AnxietyClassifier(MLModel)        # GAD-7  (new)
 └── ScreeningClassifier(MLModel)      # generic base for sleep apnea / anemia / PCOS /
                                        # burnout / thyroid / cancer screeners (new)

UserProfile
 ├── PHQ9Response (composition)
 ├── GAD7Response (composition, new)
 └── ScreeningExtras (composition, new — holds the Phase 2–5 extra questions)

BioAgeEngine
LongevityScoreEngine        # now category-weighted, see 01-PRD.md §6
FutureSimulator
DietChatEngine               # only class making external API calls
SHAPDashboard
PDFReportGenerator           # aggregates all of the above
```

## 5. Disease-Engine Registration Pattern (for the 16-disease expansion)
To keep `MLPipelineOrchestrator` from becoming a god-object as diseases grow from 4 to 16, each
disease is registered as a small config entry, not a hardcoded branch:

```python
# pseudocode — exact implementation left to the agent building it
DISEASE_REGISTRY = {
    "diabetes":   DiseaseConfig(engine=DiseaseRiskEngine, category="metabolic", inputs=[...]),
    "stroke":     DiseaseConfig(engine=DiseaseRiskEngine, category="cardiovascular", inputs=[...]),
    "ckd":        DiseaseConfig(engine=DiseaseRiskEngine, category="metabolic",
                                 depends_on=["diabetes", "hypertension"]),   # downstream engine
    "sleep_apnea":DiseaseConfig(engine=ScreeningClassifier, category="lifestyle", inputs=[...]),
    # ... all 16 entries, see 05-DISEASE-MODULES.md
}
```
`run_pipeline()` iterates the registry, resolves `depends_on` ordering (e.g. CKD must run after
Diabetes + Hypertension), runs independent engines concurrently via `asyncio.gather()`, and feeds
every result into `LongevityScoreEngine` grouped by category.

## 6. Activity Flow (Health Assessment)
```
[START]
User fills Health Profile Form (age, BMI, sleep, activity, smoking, PHQ-9, GAD-7, phase-gated extras)
   │
Valid? ──No──→ show validation errors, loop back
   │Yes
Store validated profile (PostgreSQL)
   │
<<parallel>> asyncio.gather over DISEASE_REGISTRY (respecting depends_on order)
   Disease Risk × up to 16 | Bio Age | Depression | Anxiety | Longevity Score
<<all results collected>>
   │
Render SHAP dashboard (bar + waterfall, per disease)
   │
Diet Chat initialized with risk-conditional system prompt
   │
User option: Download PDF (async via ReportLab + BackgroundTask)
[END]
```

## 7. Component Interaction Channels
1. Direct Python function calls within the ML/Business Logic layer.
2. REST calls, React frontend → FastAPI gateway.
3. SQLAlchemy ORM reads/writes to PostgreSQL.
4. The **only** external network call from the backend is `DietChatEngine` → Anthropic Claude API.
   Every disease/screening model runs on-premise — this must stay true even after the 16-disease
   expansion (no cloud ML APIs for any disease engine).

## 8. Performance Design
- `asyncio.gather()` for concurrent disease engines — target ~3x+ speedup, keeping total pipeline
  ≤8s even at 16 diseases (budget ~0.5s/engine average once parallelized).
- Models + SHAP explainer pre-loaded once at FastAPI startup (`lifespan` event).
- Redis caches prediction results 30 minutes per user; repeated dashboard loads skip inference.
- B-tree index on `user_profiles.id`, `prediction_results.user_id`; hash index on
  `chat_sessions.prediction_id`.
- PDF generation via `BackgroundTask`, returns 202 immediately, frontend polls status endpoint.

## 9. Scalability / Deployment
- Two Docker containers: FastAPI backend, React+Nginx frontend. `docker-compose.yml` adds
  PostgreSQL 16 and Redis 7 for local/single-server deployment.
- Secrets (`JWT_SECRET`, `DATABASE_URL`, `ANTHROPIC_API_KEY`) via environment variables only.
- `/health` endpoint per service, monitored by Docker healthcheck; unhealthy containers auto-restart.
- Alembic migrations run automatically on container startup via entrypoint script.
