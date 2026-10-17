# AI Longevity Intelligence Platform — Project Details

Full-stack AI health platform: 16-disease screening, biological age, longevity score,
diet chatbot, SHAP explainability aur PDF health reports. Har chez ki short info neeche hai.

---

## 1. Frontend (React SPA)

- **React 18** — Component-based UI library, poore dashboard aur forms isi par bane hain.
- **Vite 5** — Super-fast dev server aur production bundler, React app build karta hai.
- **Tailwind CSS 3** — Utility-first CSS framework, styling PostCSS + Autoprefixer se process hoti hai.
- **React Router v6** — Client-side routing; Login, Dashboard, Simulator, Reports, Admin pages handle karta hai.
- **Axios** — HTTP client; JWT token auto-attach aur 401 pe refresh retry karta hai.
- **React Icons** — Ready-made icon set, poore UI mein visual icons ke liye use hota hai.
- **Three.js + @react-three/fiber** — 3D animated scrolling background render karta hai (ScrollBackground).
- **AuthContext** — React Context mein login/register/logout aur token state manage hoti hai.
- **Vite Env (`VITE_API_URL`)** — Backend base URL env se leta hai, `/api/v1` default hai.
- **nginx + Dockerfile** — Production build ko nginx container se serve karta hai.

## 2. ML — Models, Training & Inference

- **Ensemble Classifier (VotingClassifier)** — RandomForest (40%) + XGBoost (40%) + LogisticRegression (20%) soft-voting karta hai.
- **CalibratedClassifierCV (sigmoid)** — Probability calibration taake "70% risk" ka matlab sach mein ~70% ho.
- **SMOTE (imbalanced-learn)** — Sirf training folds ke andar minority class oversample karta hai, imbalance fix.
- **Pipeline (imputer + scaler + encoder)** — Preprocessing pipeline ke andar, sirf training data pe fit (leakage-free).
- **F2-based threshold** — Out-of-fold F2 se decision threshold, recall ko favour karta hai (screening tool).
- **Optuna (TPE)** — Bayesian hyperparameter tuning, sirf cross-validation pe, test set kabhi touch nahi.
- **SHAP (TreeExplainer)** — Per-disease top features explain karta hai; dashboard aur DB mein save hoti hain.
- **Joblib artifacts** — Trained model `ml/models/<disease>.joblib` mein compress hokar save hota hai.
- **train.py + train_config.py** — Single config-driven training script; har disease ek registry entry.
- **Regex-free AutoML flow** — Split-first, tune, 5-fold CV, calibrate, threshold, test-once, report.
- **Disease risk engines** — DiseaseRiskEngine (Phase-1), Phase2RiskEngine (8 diseases), ScreeningClassifier.
- **Rule-based screeners** — GAD-7, sleep apnea (STOP-BANG), metabolic syndrome, burnout clinical rules se score.
- **DepressionClassifier (PHQ-9)** — 9 item scores se severity level nikalta hai (Minimal se Severe).
- **BioAgeEngine + LongevityScoreEngine** — Formula-based biological age aur 0-100 longevity score deta hai.
- **FutureSimulator** — Lifestyle changes ka future disease-risk projection simulate karta hai.

### 16 Registry Diseases (engine-wise)
- **Phase 1 (ML):** diabetes, heart, hypertension, obesity
- **Phase 2-5 (ML):** stroke, ckd, liver, thyroid, pcos, anemia, lung_cancer, colorectal
- **Rule-based:** gad7, sleep_apnea, metabolic_syndrome, burnout
- **Depression:** alag PHQ-9 engine

### Training Tech & Data
- **scikit-learn 1.4 / XGBoost 2.0** — Model training, CV va metrics (AUC, F1, Brier).
- **pandas + numpy** — Data loading, cleaning, feature engineering.
- **matplotlib + Optuna + joblib** — SHAP PNG plots, tuning, aur artifact serialization.
- **Real public datasets** — NHANES, UCI, Kaggle (diabetes, heart, stroke, ckd, etc.).
- **Synthetic data flags** — Kuch datasets generated hain; `SYNTHETIC_DATA` flag har jagah report hota.
- **ml/predict.py** — Served artifacts ka single entry point: `predict_risk` + `explain` (SHAP).

## 3. Backend (FastAPI)

- **FastAPI 0.110** — Async Python web framework, saare REST endpoints aur auto Swagger docs deta hai.
- **Uvicorn** — ASGI server jo FastAPI app ko serve karta hai.
- **SQLAlchemy 2.0** — ORM; DB models (User, Profile, Prediction, SHAP) handle karta hai.
- **Pydantic 2.6** — Request/response validation aur schemas (HealthProfileInput, ChatMessage, etc.).
- **Alembic** — Database migration tool, schema versioning ke liye.
- **python-jose + passlib[bcrypt]** — JWT tokens banana aur passwords hashing (bcrypt pinned 4.0.1).
- **Redis** — Caching aur fast key-value store ke liye client integrate hai.
- **ReportLab 4.1** — User health report PDF generate karta hai (background task).
- **httpx** — Groq/Claude aur API Ninjas ko async HTTP calls karta hai.
- **MLPipelineOrchestrator** — Facade jo saare ML engines ko ek `run_pipeline()` se chalata hai.
- **JWT Auth Middleware** — Protected routes pe token verify, `get_current_user` dependency deta hai.
- **CORS Middleware** — Frontend origins (3000/5173) ko cross-origin access allow karta hai.
- **lifespan hook** — Startup pe saare ML models ek baar memory mein load karta hai.

## 4. Database (PostgreSQL 16)

- **PostgreSQL 16** — Primary relational DB, Docker container mein chalti hai (port 5432).
- **users** — Login accounts: name, email, password_hash, role, created_at store karta hai.
- **user_profiles** — Health intake: age, gender, BMI (generated), sleep, BP, waist, PHQ-9.
- **screening_responses** — Extra Phase 2-5 questionnaire answers JSONB blob mein.
- **prediction_results** — Phase-1 flat risks, biological age, longevity, depression level.
- **disease_risk_results** — Normalized per-disease risk % (16 diseases), category + label.
- **shap_explanations** — Per-disease SHAP feature values (-1 se 1), rank ke sath stored.
- **chat_sessions** — Diet chatbot messages JSONB array mein, prediction se linked.
- **report_log** — Generated PDF reports ka path, size, status track karta hai.
- **pgcrypto extension + seed.py** — UUID/crypto support aur initial demo data seed karta hai.
- **indexes + FK cascade** — Foreign keys pe indexes, parent delete pe child rows cascade delete.

## 5. APIs — Internal (Backend REST)

Base prefix: `/api/v1` (Swagger: `/docs`)

- **Auth** (`/auth`) — register, login, refresh, me, logout; JWT access + refresh tokens.
- **Predict** (`/predict`) — POST profile → full ML pipeline; GET latest aur history.
- **Diseases** (`/diseases`) — Active disease catalog, frontend cards isse feed hote hain.
- **Screenings** (`/screenings/{key}/questions`) — Per-screener dynamic question sets deta hai.
- **SHAP** (`/shap/{prediction_id}`) — Stored per-disease SHAP explanations return karta hai.
- **Simulate** (`/simulate`) — Lifestyle change ka future disease-risk projection bhejta hai.
- **Chat** (`/chat/{user_id}/message|history`) — Diet chatbot reply + session history deta hai.
- **Reports** (`/reports`) — generate (202), list, status, download (PDF blob) endpoints.
- **Admin** (`/admin`) — users CRUD, stats, actions log, model retrain trigger (admin only).
- **Health** (`/` and `/health`) — Root info aur models_loaded status check endpoint.

## 6. APIs — External (Third-party integrations)

- **Groq API** — `api.groq.com` chat completions; diet chatbot ka primary LLM (gpt-oss-120b).
- **Anthropic Claude API** — `api.anthropic.com` messages; Groq fail hone pe fallback LLM.
- **API Ninjas — Nutrition** — Food ka calories/macros lookup, chatbot nuCtrition queries ke liye.
- **API Ninjas — Exercises** — Muscle/type/name se exercises fetch, workout plans ke liye.
- **Macro Calculator (local)** — Mifflin-St Jeor BMR + TDEE formula, koi external API nahi.
- **Env keys** — `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `APININJAS_KEY`; missing ho to fallback chalta hai.

## 7. Infra & Deployment

- **docker-compose.yml** — db + redis + backend + frontend, chaar services ek sath orchestrate karta hai.
- **postgres:16 + redis:7-alpine** — Official images, healthchecks ke sath.
- **backend/Dockerfile + frontend/Dockerfile** — Dono services ke alag production images banate hain.
- **start_backend.bat** — Windows ke liye quick local backend start script.
- **pytest + pytest-cov** — Unit aur integration tests (backend/tests), coverage report ke liye.
- **.env / .env.example** — Local secrets aur config (DB URL, JWT, API keys) manage karta hai.
- **ml/data, ml/models, ml/reports** — Datasets, trained artifacts, aur metrics/SHAP reports.
- **docx.md** — Detailed spec docs (PRD, architecture, API, ML training, deployment, debugging).

---

*Note: Ye platform screening aur awareness tool hai — medical diagnosis nahi. Saare risk
outputs ke sath disclaimer attach hota hai: "Screening estimate only, not a medical diagnosis."*
