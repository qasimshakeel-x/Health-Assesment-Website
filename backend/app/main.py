"""AI Longevity Platform — FastAPI Backend."""
from pathlib import Path
import sys

# Ensure project root is on sys.path so relative "ml.*" imports resolve.
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import os
import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ml.models.orchestrator import MLPipelineOrchestrator

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
    title="AI Longevity Intelligence Platform",
    description="Full-stack AI-powered health intelligence platform",
    version="1.0.0",
    lifespan=lifespan
)

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

# Import and register routers
from backend.app.routes import auth, predict, shap, simulate, chat, reports, admin

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(predict.router, prefix="/api/v1/predict", tags=["Predict"])
app.include_router(shap.router, prefix="/api/v1/shap", tags=["SHAP"])
app.include_router(simulate.router, prefix="/api/v1/simulate", tags=["Simulate"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


@app.get("/")
def root():
    return {"message": "AI Longevity Intelligence Platform API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy", "models_loaded": ml_pipeline.models_loaded}
