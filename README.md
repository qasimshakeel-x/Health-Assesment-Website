# AI Longevity Intelligence Platform

An AI-powered health intelligence platform that assesses disease risk from a health
profile, explains it with SHAP, simulates future outcomes, and gives personalised diet
advice through a chatbot.

> ⚠️ **Disclaimer:** This is an AI-estimated health risk assessment, **not a medical
> diagnosis**. Always consult a qualified doctor.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧬 **Disease Risk Prediction** | ML pipeline predicts risk across 17 conditions (diabetes, heart, hypertension, CKD, stroke, depression, …) |
| 📊 **SHAP Explanations** | Per-disease feature contributions in plain language |
| 🔮 **Health Simulator** | Projects future biological age / risk under lifestyle changes |
| 🥗 **Diet Chatbot** | Risk-aware diet advice + exact one-day plans (Groq/OpenAI LLM, DB health context) |
| 📄 **Reports** | Generate and download assessment reports |
| 🛡️ **Auth + Roles** | JWT auth (user / admin), admin dashboard |
| 🌐 **Screening Modules** | Rule-based screeners (PHQ-9, GAD-7, and more) |

---

## 🏗️ Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Redis |
| ML | scikit-learn, SHAP, pandas, joblib |
| Frontend | React 18, Vite, Tailwind CSS, React Router, Axios |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| LLM | Groq (`gpt-oss-120b`), optional OpenAI, optional Anthropic |
| Container | Docker, docker-compose |

---

## 🚀 Getting Started

### Prerequisites
- Python **3.12+**
- Node.js **18+**
- PostgreSQL **16** and Redis **7** (or Docker)

### 1. Clone & configure
```bash
git clone https://github.com/qasimshakeel-x/Health-Assesment-Website.git
cd Health-Assesment-Website
cp .env.example .env      # then fill in your keys
```

### 2. Run with Docker (easiest)
```bash
docker compose up --build
```
- Backend → http://localhost:8000
- Frontend → http://localhost:3000

### 3. Run manually (dev)

**Backend**
```bash
pip install -r backend/requirements.txt
python -m backend.run            # http://localhost:8000  (loads ML models on startup)
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

**Database**
```bash
# fresh DB via docker
docker compose up -d db redis
# or apply schema
psql "$DATABASE_URL" -f db/schema.sql
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_HOST` / `REDIS_PORT` | ✅ | Redis connection |
| `JWT_SECRET` | ✅ | **Change in production** — token signing secret |
| `GROQ_API_KEY` | ⬜ | Groq LLM key for the diet chatbot (recommended, free) |
| `GROQ_MODEL` | ⬜ | Default `openai/gpt-oss-120b` |
| `APININJAS_KEY` | ⬜ | Nutrition/exercise lookup (free tier is limited) |
| `OPEN-AI` | ⬜ | OpenAI key — used first **if** credits are available |
| `ANTHROPIC_API_KEY` | ⬜ | Claude fallback (optional) |
| `FRONTEND_URL` | ⬜ | CORS allow-list origin (default `http://localhost:3000`) |

> The chatbot tries **OpenAI → Groq → Claude**, then a rule-based fallback. Missing keys
> are skipped automatically.

---

## 🤖 ML Pipeline

- **Training entry:** `ml/train.py` (config: `ml/train_config.py`)
- **Model registry:** `ml/models/registry.py`
- **Model cards:** `ml/models/model_cards/*.json`
- **Metrics:** `ml/reports/SUMMARY.md`, `ml/reports/*_metrics.json`

```bash
pip install -r ml/requirements.txt
python -m ml.train             # trains + writes metrics to ml/reports/
```

> Trained artifacts (`*.joblib`, `ml/models/pkl/`) and raw datasets are **gitignored** —
> regenerate them locally.

---

## 🔌 API (prefix `/api/v1`)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Login (JWT) |
| POST | `/predict` | Submit health profile → full ML pipeline |
| GET | `/predict/{user_id}/latest` | Latest prediction |
| GET | `/shap/{prediction_id}` | SHAP explanation |
| POST | `/simulate` | Future health simulation |
| POST | `/chat/{user_id}/message` | Diet chatbot |
| POST | `/reports/{user_id}/generate` | Generate report |
| GET | `/diseases` | Disease registry |

Interactive docs: **http://localhost:8000/docs**

---

## 📁 Project Structure

```
├── backend/          # FastAPI app (routes, models, schemas, services)
├── frontend/         # React + Vite app
├── ml/               # Training, models, registry, reports, model cards
├── db/               # schema.sql + alembic migrations
├── docx.md/          # Full design docs (01-PRD … 13-DEBUGGING)
├── docker-compose.yml
└── .env.example
```

---

## 🧪 Testing

```bash
pytest                       # backend tests (backend/tests/)
```

Frontend e2e (headless CDP, no deps): `frontend/e2e_*.mjs`.

---

## 📚 Documentation

Full specifications live in [`docx.md/`](./docx.md) (PRD, architecture, data model,
API spec, ML training, deployment, debugging).

---

## 📝 License

For academic / educational use.
