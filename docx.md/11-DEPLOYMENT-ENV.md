# Deployment & Environment Config — AI Longevity Intelligence Platform

## 1. Environment Variables

### Backend (`backend/.env`)
| Variable | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/longevity` | PostgreSQL 16 |
| `REDIS_URL` | `redis://localhost:6379/0` | prediction cache |
| `JWT_SECRET` | `<random 64-char string>` | never commit; rotate on compromise |
| `JWT_ALGORITHM` | `HS256` | fixed per `03-AUTH.md` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 24h |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | never in frontend code or repo |
| `ANTHROPIC_MODEL` | confirm current model string at build time | used by `DietChatEngine` |
| `CORS_ALLOWED_ORIGIN` | `https://app.yourdomain.com` | single registered frontend origin only |
| `ENVIRONMENT` | `development` / `staging` / `production` | gates debug logging, docs exposure |
| `LOG_LEVEL` | `INFO` | `DEBUG` only in development |

### Frontend (`frontend/.env.local`)
| Variable | Example | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | points at the FastAPI gateway |

**Rule:** no secret ever ships in the frontend bundle. The frontend never talks to Anthropic, Redis,
or PostgreSQL directly — only to the FastAPI gateway.

## 2. Docker Compose (local / single-server)
Services: `backend` (FastAPI, `python:3.11-slim`), `frontend` (React build served via Nginx,
`node:20` build stage), `db` (`postgres:16`), `redis` (`redis:7`).

Key behaviors:
- `backend` depends_on `db`, `redis` with healthchecks — don't start serving until both are ready.
- Alembic migrations run automatically via the backend container's entrypoint script on startup.
- Each service exposes a `/health` endpoint (backend) or Docker's built-in healthcheck (db/redis);
  unhealthy containers auto-restart per `02-ARCHITECTURE.md` §9.
- Volumes: persist `db` data; persist `backend/app/ml/models/` if `.pkl` files are generated at
  build time rather than baked into the image.

## 3. Hosting Targets
| Component | Target | Notes |
|---|---|---|
| Frontend | Vercel | static build output from `frontend/dist` |
| Backend | Render.com | FastAPI + Uvicorn, auto-deploy from `main` |
| Database | Railway.app | PostgreSQL 16 managed instance |
| Redis | Railway.app or Render add-on | |

Local/offline demo (e.g. for a committee viva where internet may not be reliable) should run
entirely via `docker compose up`, with the diet-chat module clearly showing its graceful fallback
UI if `ANTHROPIC_API_KEY` is unset or unreachable — everything else must still function fully
offline per the original OE-5 constraint.

## 4. CI/CD Checklist (suggested, adapt to whatever CI the team picks — GitHub Actions assumed)
```
on: pull_request → dev, push → main
jobs:
  backend-test:
    - pip install -r requirements.txt
    - pytest --cov=app --cov-fail-under=85
    - alembic upgrade head --sql   # verify migrations apply cleanly
  frontend-test:
    - npm ci
    - npm run lint
    - npm run build
  ml-validation (manual trigger or on training/ changes only):
    - run each train_*.py script's evaluation step
    - fail if any model misses its threshold from 09-ML-TRAINING-SPEC.md §4
  deploy (on push to main only, after tests pass):
    - build + push backend Docker image
    - trigger Render deploy hook
    - trigger Vercel deploy (or auto via Vercel's git integration)
```

## 5. Secrets Management
- Local dev: `.env` files, gitignored, `.env.example` committed with placeholder values.
- Render/Vercel/Railway: set secrets via each platform's dashboard/env-var UI, never in
  `docker-compose.yml` or any committed file.
- Rotate `JWT_SECRET` and `ANTHROPIC_API_KEY` if ever exposed (e.g. accidental commit) — this
  invalidates all existing sessions, document that tradeoff for the team.

## 6. Pre-deployment Checklist
- [ ] All env vars set on the target platform (§1)
- [ ] `ENVIRONMENT=production` → Swagger `/docs` either disabled or protected (don't expose
      full API schema publicly without deciding that's intentional)
- [ ] `CORS_ALLOWED_ORIGIN` matches the actual deployed frontend URL exactly
- [ ] TLS/HTTPS enforced on all public endpoints
- [ ] Alembic migrations applied on the production DB before the new backend version goes live
- [ ] `.pkl` model files present in the deployed backend image/volume — a missing model file is
      the `503 Service Unavailable` case from `02-ARCHITECTURE.md`/`07-DEV-WORKFLOW.md`
- [ ] Smoke test: register → login → submit assessment → view dashboard → download PDF, on
      the actual deployed URLs, not just localhost
