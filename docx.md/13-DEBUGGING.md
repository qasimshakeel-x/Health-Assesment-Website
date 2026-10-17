# Debugging Guide — AI Longevity Intelligence Platform

Standalone troubleshooting reference. For the quick version embedded in the sprint workflow, see
`07-DEV-WORKFLOW.md` §5 — this doc goes deeper per subsystem and includes tooling/commands.

## 1. General Debugging Setup
- Run backend with `--reload` and `LOG_LEVEL=DEBUG` locally (never in production — see
  `11-DEPLOYMENT-ENV.md` §1).
- Swagger UI (`/docs`) is the fastest way to manually hit any endpoint with a known JWT during
  dev — grab a token from `/auth/login`, click "Authorize" in Swagger, then exercise routes directly.
- Structured JSON logs to stdout — pipe through `jq` locally for readability:
  `uvicorn app.main:app --reload | jq .` (if logs are JSON-per-line).
- Every log line should carry `request_id` — when a user reports an error, ask for the `request_id`
  if the frontend surfaces one, and grep logs by it instead of by timestamp guessing.

## 2. Auth / JWT Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `401` immediately after login | Clock skew between client/server, or `JWT_SECRET` mismatch across restarts | Check server time; confirm `JWT_SECRET` is stable (not regenerated per restart) |
| Works locally, `401` everywhere in staging | `CORS_ALLOWED_ORIGIN` doesn't match the deployed frontend URL exactly (including protocol/subdomain) | Fix the env var, redeploy backend |
| Silent infinite redirect loop to `/login` | Refresh interceptor retrying on every `401` without a cap | Confirm the "retry once" rule from `12-INTEGRATION.md` §1 is actually implemented |
| Admin route returns `401` for an admin user | `require_role("admin")` checking the wrong claim, or role not included in the JWT payload at issue time | Decode the token (jwt.io or a script) and check the `role` claim is present and correct |
| Reused refresh token succeeds (should fail) | Rotation not implemented — old token not marked revoked | Add `revoked_at`/token-hash check per `03-AUTH.md` §2–3 |

Useful command: decode a JWT without verifying, to inspect claims during dev:
```bash
python -c "import jwt; print(jwt.decode('<token>', options={'verify_signature': False}))"
```

## 3. ML Pipeline Issues

| Symptom | Likely cause | Debug steps |
|---|---|---|
| `503` on `/predict` | A `.pkl` model failed to load at startup | Check startup logs for the `lifespan` event; confirm the file exists at the path `registry.py` expects |
| `422` on `/predict` with a confusing field error | Feature mismatch between `UserProfile`/`screening_responses` and what the engine's `validate_features()` expects | Log (dev only) the exact feature dict being passed into the failing engine; diff against its training feature list in the model card |
| One disease's risk is always 0% or always near 100% | Feature scaling mismatch (e.g. age passed as a string, or a percentage passed as 0–1 instead of 0–100) | Write a quick unit test feeding a known fixture profile and print the raw feature vector before it hits `predict_proba()` |
| CKD (or other dependent disease) missing from response | Orchestrator ran it before its `depends_on` engines finished, or `depends_on` isn't declared | Check `registry.py` entry; add an integration test asserting wave ordering (IT-07) |
| Pipeline exceeds 8s | A blocking (sync) call inside an `async def` engine serializes the whole `asyncio.gather()` batch | Profile per-engine timing; look for a synchronous `requests` call, blocking file I/O, or a non-async DB call hiding inside an engine |
| Same user, same inputs, different results on repeat calls within 30 min | Redis cache not being checked/written correctly | Verify cache key includes `user_id` + a hash of the input profile; confirm TTL is 30 min, not 0 |

### Reproducing an ML bug safely
1. Never debug against production user data directly.
2. Pull the exact input profile from logs (feature values only, never PHQ-9/GAD-7 raw answers in
   logs per the no-health-data-in-logs rule — if they're missing, reconstruct via DB with proper
   access controls instead).
3. Feed it through a local unit test fixture, not a live API call, so you can step through with a
   debugger (`pdb`/`ipdb`) inside the engine itself.

## 4. SHAP Issues

| Symptom | Likely cause |
|---|---|
| Bar direction (dark/light) flipped for one disease vs the others | A new engine's feature scale is inverted relative to the convention (e.g. "healthy_score" instead of "risk_score") — normalize before passing to `TreeExplainer`, or flip the sign at render time consistently |
| SHAP values exist but dashboard shows nothing | `disease_key` mismatch between `shap_explanations` rows and what the frontend requests via `GET /shap/{predictionId}?disease=X` — confirm the string literally matches `DISEASE_REGISTRY` key (see `12-INTEGRATION.md` §5) |
| SHAP computation itself throws | `TreeExplainer` was pointed at the ensemble wrapper instead of the raw underlying RF model object — confirm `shap_explainer.py` unwraps to the actual `RandomForestClassifier` instance |
| Top-5 factors list looks nonsensical in plain language | The feature-name → human-sentence translation map (`08-FRONTEND-UI-SPEC.md`, SHAP screen) is missing an entry for a new feature and is falling back to the raw column name | Add the missing translation entry, don't ship raw feature names to users |

## 5. Diet Chat Issues

| Symptom | Likely cause |
|---|---|
| Generic, non-risk-aware responses | System prompt built from a stale `prediction_id`, or context-injection rules (`09-ML-TRAINING-SPEC.md` §2) didn't fire because risk thresholds weren't actually crossed — verify the specific `disease_risk_results.risk_percent` value against the rule's threshold |
| `504` on every chat message | Anthropic API key invalid/expired, or network egress blocked from the backend's host | Test the key directly with a minimal `curl` against the Anthropic API outside the app first, to isolate app bug vs account/network issue |
| Disclaimer footer missing from a response | Rendered only as a backend-appended string and something in formatting (e.g. markdown stripping) removed it — or the frontend safety-net append (`08-FRONTEND-UI-SPEC.md`) was removed in a refactor | Check both the API response body and the rendered DOM |
| Contraindicated food not flagged | The conflict-detection rule set hasn't been updated for a newly-added disease (e.g. Anemia's iron-rich rule from Phase 4) | Cross-check `09-ML-TRAINING-SPEC.md` §2 step list against what's actually implemented in `diet_chat_engine.py` |

## 6. PDF Generation Issues

| Symptom | Likely cause |
|---|---|
| `202` returned but status never flips to `success`/`failed` | `BackgroundTask` silently threw an unhandled exception | Wrap the PDF compile step in try/except, always write to `report_log.status` even on failure, with the exception message captured |
| PDF generation blocks the request (defeats the 10s async budget) | Generation accidentally running synchronously instead of as a true background task | Confirm it's registered via FastAPI's `BackgroundTasks` dependency, not called inline before the response is returned |
| PDF missing a section (e.g. no SHAP charts) | One upstream module failed per REL-1 (partial results allowed) but the PDF template doesn't handle a `None`/missing section gracefully | Template should render a "data not available for this section" note rather than crashing the whole compile |
| Disclaimer missing from some pages | Disclaimer rendering hardcoded onto only the first page instead of a per-page template element | Fix at the ReportLab template/canvas level so it applies to every page automatically |

## 7. Database / Migration Issues

| Symptom | Likely cause |
|---|---|
| `alembic upgrade head` fails in CI but works locally | Migration depends on data state that doesn't exist in a fresh CI DB (e.g. a backfill migration assuming old columns have data) | Write migrations to handle an empty table case too, or split schema-change and backfill into separate migrations per `04-DATA-MODEL.md` §6 |
| Foreign key violation on `disease_risk_results` insert | `prediction_id` not committed yet when a dependent engine's wave tries to write | Confirm orchestrator persists `prediction_results` row and gets its ID before any `disease_risk_results` insert that references it |
| Slow `/predict/{userId}/latest` at scale | Missing index on `prediction_results.user_id` or `disease_risk_results.prediction_id` | Verify indexes from `04-DATA-MODEL.md` §5 actually exist — check with `\d+ table_name` in `psql` |

## 8. Frontend Issues

| Symptom | Likely cause |
|---|---|
| Blank screen during pipeline run | Missing loading state on the specific async call — not all screens may have it wired, check each one individually per `08-FRONTEND-UI-SPEC.md` loading-state rule |
| Dashboard shows stale data after a new assessment | App state not invalidated/replaced after a new `POST /predict`, screen reading from an old cached prediction | Confirm the cache-update step in `12-INTEGRATION.md` §1 "Data flow" actually replaces, not merges |
| Simulator sliders don't update instantly | Accidentally wired a slider's `onChange` to re-call the backend instead of recalculating client-side | Should use the cached coefficients from the initial `/simulate` response only (Observer pattern, `02-ARCHITECTURE.md` §3) |
| Keyboard navigation skips a form section | Missing/incorrect `tabIndex` or a custom component not using a semantically focusable element | Audit with browser dev tools' accessibility tree, not just visual tab order |

## 9. Environment / Deployment Issues
See `11-DEPLOYMENT-ENV.md` §6 "Pre-deployment Checklist" first — most "works locally, broken in
staging/prod" issues trace back to one unset or mismatched env var (CORS origin, API base URL,
missing `.pkl` files not included in the deployed image, or `ENVIRONMENT` flag not set).

## 10. When All Else Fails
1. Reproduce with the smallest possible input (minimal valid profile, one disease active).
2. Check `request_id` in logs end-to-end — does it appear in frontend network tab, backend access
   log, and (if relevant) the orchestrator's per-engine timing log?
3. Bisect: comment out engines in `DISEASE_REGISTRY` one at a time (in a local branch, never in
   `main`) to isolate which module is actually responsible for a pipeline-wide failure.
4. If it's intermittent, suspect Redis cache staleness or a race condition in `asyncio.gather()`
   ordering before suspecting the ML models themselves.
