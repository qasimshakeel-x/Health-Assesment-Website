"""AI Longevity Platform — FastAPI Backend."""
from pathlib import Path
import sys

# Ensure project root is on sys.path so relative "ml.*" imports resolve.
# NOTE: parents[2] = project root (D:\Uni-Project); parents[1] sirf backend/ tha —
# wahin se "import ml..." fail hota tha (BUG-3 fix).
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Repo-root .env load karo (uvicorn se boot hone par bhi GROQ_API_KEY
# mile — diet chat ka LLM isi se chalta hai). Missing python-dotenv pe silently skip.
try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except ImportError:
    pass

import os
import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from ml.models.orchestrator import MLPipelineOrchestrator
from backend.app.limiter import limiter

# Global ML pipeline
ml_pipeline = MLPipelineOrchestrator()

# Redis connection for caching
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models once at startup."""
    ml_pipeline.load_models()
    yield


app = FastAPI(
    title="AI & ML Longevity Intelligence Platform",
    description="AI & ML powered health intelligence platform",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting (slowapi) — per-IP limits endpoints pe @limiter.limit(...) se lagte hain
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
            os.getenv("FRONTEND_URL", "http://localhost:3000"),
            "http://localhost:3000",
            "http://localhost:5173",
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Basic security headers — clickjacking / MIME-sniffing / referrer leaks rokta hai."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    return response

# Import and register routers
from backend.app.routes import auth, predict, shap, simulate, chat, reports, admin, diseases, intake

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(predict.router, prefix="/api/v1/predict", tags=["Predict"])
app.include_router(shap.router, prefix="/api/v1/shap", tags=["SHAP"])
app.include_router(simulate.router, prefix="/api/v1/simulate", tags=["Simulate"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(diseases.router, prefix="/api/v1/diseases", tags=["Diseases"])
# Assessment Form Helper — LLM proxy (keys server-side, /intake/chat)
app.include_router(intake.router, prefix="/api/v1/intake", tags=["Intake Assistant"])
# 05-API-SPEC §3 — screening metadata ka path `/screenings/...` hai (diseases prefix ke bahar)
app.include_router(diseases.screenings_router, prefix="/api/v1/screenings", tags=["Screenings"])


@app.get("/")
def root():
    return {"message": "AI & ML Longevity Intelligence Platform API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy", "models_loaded": ml_pipeline.models_loaded}
