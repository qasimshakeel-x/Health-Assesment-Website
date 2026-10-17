# Project Structure — AI Longevity Intelligence Platform

Reference repo layout. An agent scaffolding the project should follow this unless a specific
constraint in another doc says otherwise.

```
ai-longevity-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app, lifespan event (model pre-loading)
│   │   ├── config.py                   # env var loading (pydantic-settings)
│   │   ├── dependencies.py             # get_current_user, require_role, etc.
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py             # /auth/* routes
│   │   │       ├── predict.py          # /predict/* routes
│   │   │       ├── shap.py             # /shap/* routes
│   │   │       ├── simulate.py         # /simulate route
│   │   │       ├── diseases.py         # /diseases, /screenings/* (metadata)
│   │   │       ├── chat.py             # /chat/* routes
│   │   │       ├── reports.py          # /reports/* routes
│   │   │       ├── admin.py            # /admin/* routes
│   │   │       └── health.py           # /health
│   │   │
│   │   ├── core/
│   │   │   ├── security.py             # JWT encode/decode, bcrypt
│   │   │   └── logging.py              # structured JSON logging setup
│   │   │
│   │   ├── ml/
│   │   │   ├── base.py                 # MLModel abstract class
│   │   │   ├── registry.py             # DISEASE_REGISTRY + DiseaseConfig
│   │   │   ├── orchestrator.py         # MLPipelineOrchestrator (Facade), run_pipeline()
│   │   │   ├── engines/
│   │   │   │   ├── disease_risk_engine.py      # DiseaseRiskEngine(MLModel)
│   │   │   │   ├── depression_classifier.py    # DepressionClassifier(MLModel)
│   │   │   │   ├── anxiety_classifier.py       # AnxietyClassifier(MLModel)
│   │   │   │   └── screening_classifier.py     # generic base for Phase 2–5 screeners
│   │   │   ├── bio_age_engine.py
│   │   │   ├── longevity_score_engine.py
│   │   │   ├── future_simulator.py
│   │   │   ├── shap_explainer.py
│   │   │   └── models/                 # trained .pkl files, one per disease_key
│   │   │       ├── diabetes_rf.pkl, diabetes_xgb.pkl, diabetes_lr.pkl
│   │   │       ├── stroke_lr.pkl, stroke_rf.pkl
│   │   │       ├── ckd_rf.pkl, ckd_xgb.pkl
│   │   │       ├── depression_gb.pkl
│   │   │       └── ... (one set per disease_key in the registry)
│   │   │
│   │   ├── chat/
│   │   │   └── diet_chat_engine.py     # DietChatEngine — only class calling Anthropic API
│   │   │
│   │   ├── reports/
│   │   │   ├── pdf_report_generator.py # PDFReportGenerator (ReportLab)
│   │   │   └── templates/              # PDF section templates
│   │   │
│   │   ├── db/
│   │   │   ├── base.py                 # SQLAlchemy Base, session
│   │   │   ├── models.py               # ORM models — auth_users, user_profiles,
│   │   │   │                           #   prediction_results, disease_risk_results,
│   │   │   │                           #   shap_explanations, chat_sessions, report_log,
│   │   │   │                           #   screening_responses, admin_action_log
│   │   │   └── crud.py                 # reusable query functions
│   │   │
│   │   └── schemas/                    # Pydantic v2 request/response models
│   │       ├── auth.py, profile.py, prediction.py, chat.py, report.py, admin.py
│   │
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── training/                       # OFFLINE — never imported by the running API
│   │   ├── datasets/                   # raw + cleaned public datasets (gitignored if large)
│   │   ├── train_disease_models.py
│   │   ├── train_depression_model.py
│   │   ├── train_anxiety_model.py
│   │   ├── train_<disease>_model.py    # one per Phase 2–5 disease
│   │   └── model_cards/                # training metadata per model (see 09-ML-TRAINING-SPEC.md §1)
│   │
│   ├── tests/
│   │   ├── unit/                       # mirrors app/ structure
│   │   └── integration/                # IT-01..IT-07 from 07-DEV-WORKFLOW.md
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/                      # one per route in 08-FRONTEND-UI-SPEC.md §2
│   │   │   ├── Login.jsx, Register.jsx
│   │   │   ├── AssessmentForm.jsx
│   │   │   ├── RiskDashboard.jsx
│   │   │   ├── ShapDashboard.jsx
│   │   │   ├── FutureSimulator.jsx
│   │   │   ├── DietChat.jsx
│   │   │   ├── Reports.jsx
│   │   │   └── admin/
│   │   │       ├── AdminUsers.jsx
│   │   │       └── AdminActionLog.jsx
│   │   │
│   │   ├── components/
│   │   │   ├── forms/                  # dynamic screening-question renderer, form fields
│   │   │   ├── charts/                 # gauge, SHAP bar/waterfall, simulation bar chart
│   │   │   ├── cards/                  # disease risk card, disclaimer banner
│   │   │   └── chat/                   # chat bubble, typing indicator, conflict alert
│   │   │
│   │   ├── api/
│   │   │   ├── axiosClient.js          # Axios instance + auth interceptor (refresh-on-401)
│   │   │   └── endpoints.js            # thin wrappers per API in 05-API-SPEC.md
│   │   │
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   │
│   │   └── App.jsx, main.jsx
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── .env.example
│
├── docs/                               # this doc set lives here in the actual repo
│   ├── 01-PRD.md
│   ├── 02-ARCHITECTURE.md
│   ├── 03-AUTH.md
│   ├── 04-DATA-MODEL.md
│   ├── 05-API-SPEC.md
│   ├── 06-DISEASE-MODULES.md
│   ├── 07-DEV-WORKFLOW.md
│   ├── 08-FRONTEND-UI-SPEC.md
│   ├── 09-ML-TRAINING-SPEC.md
│   ├── 10-PROJECT-STRUCTURE.md
│   └── 11-DEPLOYMENT-ENV.md
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Notes
- `backend/app/ml/models/*.pkl` should be gitignored if large; training scripts regenerate them,
  or they're pulled from object storage in CI/CD — don't commit multi-MB binary files to git.
- `training/` is intentionally outside `app/` so it's never accidentally imported into the running
  API process — the API only ever loads finished `.pkl` files.
- Every new Phase 2–5 disease touches exactly: one engine file (or reuses `screening_classifier.py`),
  one registry entry, one training script, one `.pkl` output, and optionally one new frontend
  screening-question set — it should never require editing existing disease files.
