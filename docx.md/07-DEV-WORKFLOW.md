# Dev Workflow & Debugging Playbook — AI Longevity Intelligence Platform

## 1. Local Setup
```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill DATABASE_URL, JWT_SECRET, ANTHROPIC_API_KEY, REDIS_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
cp .env.example .env.local    # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev

# Full stack via Docker Compose
docker compose up --build
```
Swagger UI: `http://localhost:8000/docs`. Health check: `GET /health`.

## 2. Branching Model
- `main` — always deployable.
- `dev` — integration branch, merges from feature branches.
- `feature/<module>-<short-desc>` — e.g. `feature/stroke-risk-engine`,
  `feature/auth-jwt-rotation`, `feature/pdf-async-generation`.
- `fix/<short-desc>` for bug fixes.
- PR into `dev`, squash-merge. PR into `main` only from `dev`, after integration tests pass.
- Each new disease module (Phase 2–5 in `06-DISEASE-MODULES.md`) = its own feature branch, its
  own PR, so a bad model doesn't block shipping the others.

## 3. Sprint Plan (reference — adapt as needed)
| Sprint | Focus | Exit criteria |
|---|---|---|
| 1 | Repo scaffold, DB schema + Alembic, dataset collection/cleaning, Docker Compose skeleton | SDD/PRD approved, clean datasets ready |
| 2 | Phase-1 disease ensemble (RF+XGB+LR), SHAP integration | Ensemble AUC-ROC ≥ 0.85 |
| 3 | Bio Age engine, Longevity Score engine, PHQ-9 classifier | Depression classifier F1 ≥ 0.80 |
| 4 | FastAPI backend: all REST endpoints, JWT auth, PDF generator | All endpoints correct HTTP codes via Swagger |
| 5 | React frontend: all screens, dashboard charts, diet chat UI | WCAG 2.1 AA pass |
| 6 | Integration tests, deployment, docs | All FR pass integration tests |
| 7+ | Phase 2–5 disease rollout (see `06-DISEASE-MODULES.md`) | Each phase's AUC/F1 target met before merge to `main` |

## 4. Testing Strategy
- **Unit tests** (pytest + pytest-cov), target ≥85% line coverage per module class:
  `UserProfile`, `DiseaseRiskEngine`, `BioAgeEngine`, `LongevityScoreEngine`, `DepressionClassifier`,
  `AnxietyClassifier`, `DietChatEngine`, `PDFReportGenerator`, `FutureSimulator`, `SHAPDashboard`.
- **Integration tests** (FastAPI `TestClient` + Docker test Postgres):
  - IT-01 Full prediction pipeline → 200 with all active disease risks, bio_age, longevity_score
  - IT-02 SHAP persistence → rows exist for every active disease
  - IT-03 Diet chat risk injection → diabetes question returns low-GI guidance
  - IT-04 PDF generation → 202 → poll status → download returns valid PDF
  - IT-05 JWT protection → no token / expired token → 401
  - IT-06 Future simulator → improved bio_age < current bio_age
  - IT-07 *(new)* CKD depends_on ordering → CKD result only computed after diabetes +
    hypertension results exist in the same pipeline run
- **ML validation** (held-out 20% split, before any model enters the registry):
  | Model | Metric | Threshold |
  |---|---|---|
  | Disease ensembles | AUC-ROC | ≥ 0.85 |
  | Disease ensembles | F1 (macro) | ≥ 0.80 |
  | Depression (PHQ-9) | F1 (weighted) | ≥ 0.80 |
  | Depression, Severe class | Recall | ≥ 0.88 |
  | Bio Age | MAE vs reference formula | ≤ 3.0 years |
  | SHAP | Top-3 features clinically plausible | manual review pass |

## 5. Debugging Playbook

### ML pipeline returns wrong/missing risk for a disease
1. Check `DISEASE_REGISTRY` — is the disease's `depends_on` list correct and are those
   dependencies actually computed first? (`02-ARCHITECTURE.md` §5)
2. Check the model `.pkl` is loaded — look for a `503 Service Unavailable` in logs
   (`model not loaded at startup` case).
3. Check feature mismatch — Pydantic should raise `422` if the engine's expected feature list
   doesn't match what `UserProfile`/`screening_responses` actually provided. Compare the
   engine's `validate_features()` output against the incoming payload.
4. Reproduce with a known-good fixture from the unit test suite before touching production data.

### Pipeline exceeds the 8-second budget
1. Confirm `asyncio.gather()` is actually parallelizing — a blocking (non-async) call inside one
   engine will serialize the whole batch. Profile with `time` around each engine call.
2. Check Redis cache hit rate — repeated dashboard loads for the same user within 30 minutes
   should skip inference entirely.
3. If a new Phase 2–5 disease pushed the budget over, check whether it's unnecessarily
   `depends_on`-chained to something it doesn't need (false dependency serializes it).

### SHAP values look wrong / dashboard bars flipped
1. Confirm `TreeExplainer` is being run against the **Random Forest** model specifically (per
   CO-5 in the original SRS — SHAP is RF-only, not the ensemble average).
2. Confirm the dark/light bar convention is consistent: dark = increases risk, light = decreases
   risk, across every disease — a sign flip here is a common bug when adding a new disease
   engine with an inverted feature scale.

### Diet chat gives generic (non-risk-aware) answers
1. Confirm the system prompt is actually built from the **latest** `prediction_id`, not a stale
   cached one — check `chat_sessions.prediction_id` matches `prediction_results` latest row for
   that user.
2. Confirm the context-injection rules from `01-PRD.md`/original SDD §5.3 fired — log the
   assembled system prompt in dev (never in production, it contains health data) and check the
   expected rule strings are present (`RULE_NO_HIGH_GI`, DASH, Mediterranean, magnesium, etc.)
3. Check Anthropic API timeout (30s) isn't silently falling back — a fallback response that looks
   plausible but generic is the `504` fallback path, not a real model response.

### JWT / auth failures
1. Check access token hasn't just expired (24h) — client should be hitting `/auth/refresh`
   automatically on `401`, not surfacing the error to the user directly.
2. Reused refresh token → should be a hard `401`, forcing re-login. If it's silently succeeding,
   rotation isn't implemented correctly (see `03-AUTH.md` §2–3).
3. Admin route returning `401` instead of `403` for a valid-but-non-admin token — check
   `require_role("admin")` is checked separately from `get_current_user`.

### PDF generation fails or times out
1. Check `report_log.status` for the failure row — error should be logged there, not just in stdout.
2. Confirm it's running as a `BackgroundTask` — a synchronous PDF generation blocking the
   request thread is the most common cause of the 10-second budget being missed.
3. Partial-data case: if one module failed upstream (per REL-1, failures shouldn't cascade), the
   report should still generate with a note about the missing module — not fail entirely.

## 6. Logging Conventions
Every `WARNING`+ log line includes: ISO-8601 timestamp, `request_id` (UUID per request),
`user_id` (if authenticated), `endpoint`, `error_type`, `stack_trace`. JSON structured logs to stdout
for container log aggregation (Docker logs / CloudWatch / ELK). **Never log raw health data, PHQ-
9/GAD-7 answers, or full diet-chat system prompts** — log IDs and error types, not patient content.

## 7. Pre-merge Checklist (per feature branch, especially new disease modules)
- [ ] Unit tests added/passing, coverage ≥85% for touched classes
- [ ] Model meets its threshold in `06-DISEASE-MODULES.md`/§4 above before being wired into the registry
- [ ] SHAP explainability wired for the new disease (if it's a disease, not a screening-only module)
- [ ] Disclaimer text present in API response, dashboard card, and PDF template
- [ ] New `screening_responses` keys (if any) documented in `04-DATA-MODEL.md`
- [ ] Alembic migration included if schema changed, reversible (`downgrade()` implemented)
- [ ] No secrets committed; `.env.example` updated if a new env var was added
