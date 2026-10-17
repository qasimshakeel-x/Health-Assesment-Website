# Integration Guide — AI Longevity Intelligence Platform

How the modules, layers, and third-party services actually wire together. Read alongside
`02-ARCHITECTURE.md` (structure) and `05-API-SPEC.md` (contracts) — this doc is about the
runtime glue between them.

## 1. Frontend ↔ Backend Integration

### Axios client setup
- One shared Axios instance (`frontend/src/api/axiosClient.js`), base URL = `VITE_API_BASE_URL`.
- Request interceptor: attach `Authorization: Bearer {access_token}` from `AuthContext`.
- Response interceptor: on `401`, attempt exactly one silent `POST /auth/refresh` using the stored
  refresh token; on success, retry the original request once; on failure, clear auth state and
  redirect to `/login`. Never loop — cap at one retry to avoid infinite refresh storms.
- All endpoint calls go through `frontend/src/api/endpoints.js` wrappers, never raw `axios.get(...)`
  scattered through components — keeps the contract in one place when `05-API-SPEC.md` changes.

### Data flow: Assessment → Dashboard
```
AssessmentForm.jsx
  → POST /predict (full profile + active screening_responses)
  → response cached in app state (prediction_id, all results)
  → navigate to /dashboard
RiskDashboard.jsx / ShapDashboard.jsx / FutureSimulator.jsx / DietChat.jsx
  → all read from the SAME cached prediction in app state
  → only re-fetch (GET /predict/{userId}/latest) on hard page reload, not on every screen switch
```
This avoids refetching the same prediction 4 times across 4 screens and keeps dashboard screens
in sync with each other for a single assessment session.

### Loading / empty states
- Every screen that depends on a prediction existing must handle "no prediction yet" (new user) by
  redirecting to `/assessment`, not rendering a broken/empty dashboard.
- `USE-5` (no blank screen during ML execution) → every async call triggers a loading indicator
  component before the request fires, not only after a timeout.

## 2. Backend Internal Integration — `MLPipelineOrchestrator`

This is the single seam between the Application layer and the ML layer (Facade pattern,
`02-ARCHITECTURE.md` §3). `POST /predict` does nothing but:
```python
# pseudocode
@router.post("/predict")
async def predict(payload: HealthProfileIn, user=Depends(get_current_user)):
    profile = await save_profile(user.id, payload)
    result = await orchestrator.run_pipeline(profile)   # the ONLY ML-layer call from the route
    return result
```
`run_pipeline()` internally:
1. Resolves `DISEASE_REGISTRY` execution order (topological sort on `depends_on`).
2. Runs each independent "wave" of engines concurrently via `asyncio.gather()`.
3. Feeds each wave's output into dependent engines in the next wave (e.g. CKD waits for
   Diabetes + Hypertension — see `02-ARCHITECTURE.md` §5).
4. Runs `BioAgeEngine`, `DepressionClassifier`, `AnxietyClassifier` in the same first wave as the
   independent disease engines (none of them depend on disease outputs).
5. Runs `LongevityScoreEngine` last — it depends on the category-grouped disease results.
6. Persists everything (`prediction_results`, `disease_risk_results`, `shap_explanations`) in one
   transaction — if persistence fails, the whole prediction fails (don't return results the DB
   doesn't have, since downstream modules like Diet Chat and PDF rely on reading them back).
7. Returns the assembled response shaped per `05-API-SPEC.md` §9.

**Adding a disease = integration checklist:**
- [ ] New engine class implements `MLModel.predict_proba()`
- [ ] New entry in `DISEASE_REGISTRY` with correct `category` and `depends_on`
- [ ] If it depends on another disease's output, confirm that dependency is already registered
- [ ] SHAP wiring (if applicable) added to `shap_explainer.py`
- [ ] No changes needed to the FastAPI route, the orchestrator loop, or other engines — if a
      change WAS needed there, the registry pattern isn't being followed correctly.

## 3. Depression/Anxiety → Diet Chat Integration
`DietChatEngine.injectContext()` is a **dependency**, not a parallel read — it must run strictly after
the full `run_pipeline()` result is persisted, because it reads the latest `prediction_results` +
`disease_risk_results` rows, not the in-memory pipeline output directly. This decouples chat session
creation (which can happen much later than the original assessment) from the pipeline run itself.

```
User opens /chat
  → GET /chat/{userId}/history  (checks for an existing chat_session)
  → if none: backend builds system prompt from latest prediction_id, creates chat_sessions row
  → first user message sent to Claude WITH the system prompt already set
```

## 4. Anthropic Claude API Integration
- `DietChatEngine` is the **only** class in the codebase that calls an external API — this is a hard
  architectural rule (`02-ARCHITECTURE.md` §7), not just a convention. Any new feature that wants
  AI text generation goes through this class or a clearly separated sibling, never ad hoc from a
  route handler.
- Request timeout: 30s (`httpx` client config). On timeout → `504`, frontend shows the fallback
  chat UI (`08-FRONTEND-UI-SPEC.md` Diet Chat section), never a raw error or a frozen spinner.
- API key sourced only from `ANTHROPIC_API_KEY` env var, loaded once at startup, never passed
  through any request body or logged.
- Context injection assembles the system prompt **server-side** per
  `09-ML-TRAINING-SPEC.md` §2 "Diet Chat Context Injection" algorithm — the frontend never
  constructs or sees the raw system prompt, only the resulting conversation.
- Conversation history (`chat_sessions.messages`) is replayed on each call so Claude has full
  context — don't re-inject the full risk profile into every single message, only the initial system
  prompt; subsequent messages are normal turns.

## 5. SHAP ↔ Disease Engine Integration
- `TreeExplainer` is instantiated against the **Random Forest** model specifically for each disease
  (SHAP runs on RF only, per the original CO-5 constraint — not against XGBoost, LR, or the
  ensemble average).
- SHAP computation happens in the same pipeline wave as the disease prediction itself (not a
  separate later call) so results persist together and the SHAP dashboard never shows stale values
  for a newer prediction.
- `shap_explanations.disease` (or `disease_key` once normalized per `04-DATA-MODEL.md`) must
  use the exact same string as `disease_risk_results.disease_key` — this is the join key the
  SHAP dashboard route uses; a mismatch here is a common integration bug (see `13-DEBUGGING.md`).

## 6. PDF Report Integration
`PDFReportGenerator` aggregates (Aggregation pattern) the outputs of every other module — it does
not recompute anything. It reads:
- Latest `user_profiles` row
- Latest `prediction_results` + all `disease_risk_results` for that prediction
- All `shap_explanations` for that prediction
- Latest `chat_sessions` summary (optional section, can be omitted if no chat yet)
- A fresh `FutureSimulator` run at default deltas (or the user's last-viewed simulation, if cached)

Generation is triggered as a `BackgroundTask` so `POST /reports/{userId}/generate` returns `202`
immediately; the actual PDF compile reads everything above in one go, writes to disk/storage,
updates `report_log.status`, and the frontend polls `/reports/{reportId}/status` until it flips to
`success` or `failed`.

## 7. Admin Panel Integration
Admin routes reuse the exact same `MLPipelineOrchestrator`/training scripts as the main app — "trigger
model retraining" (`POST /admin/models/retrain`) should call the same `train_<disease>_model.py`
entrypoint used in `training/` (per `10-PROJECT-STRUCTURE.md`), not a separate admin-only training
path, so there's only one source of truth for how a model gets built.

## 8. Cross-Cutting: Disclaimer Propagation
The medical/clinical disclaimer is not a frontend-only string. It must be attached at the point data
is produced so it survives every surface:
- API response (`disclaimer` field, `05-API-SPEC.md` §8)
- PDF report (every page, per original BR-1 on FR-9)
- Diet chat (every AI message footer)
- Cancer-screening disease cards get the stricter "population-level estimate, not diagnostic"
  variant — this is a **different string**, not the general one; don't collapse them into one
  constant used everywhere.

## 9. Integration Test Coverage Map
| Integration point | Covered by |
|---|---|
| Orchestrator wave ordering (CKD after Diabetes/Hypertension) | IT-07 (`07-DEV-WORKFLOW.md`) |
| Full pipeline → persistence → response shape | IT-01 |
| SHAP persists with matching `disease_key` | IT-02 |
| Diet chat reads latest prediction correctly | IT-03 |
| PDF reads all aggregated sources | IT-04 |
| Auth attached correctly across all protected routes | IT-05 |
| Future Simulator re-running engines against modified profile | IT-06 |
