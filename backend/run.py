"""AI Longevity Platform — run script."""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
for base in (str(project_root), str(Path(__file__).resolve().parent)):
    if base not in sys.path:
        sys.path.insert(0, base)

# Repo-root .env load karo — warna GROQ_API_KEY/ANTHROPIC_API_KEY os.getenv se kabhi
# nahi milte (diet chat silent fallback pe chala jaata tha). setdefault se PEHLE load
# karo taake .env wali values priority lein.
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
if load_dotenv:
    load_dotenv(project_root / ".env")

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/longevity_platform")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
# NOTE: JWT_SECRET ka setdefault JAAN-BOOJH kar nahi rakha — weak default se koi bhi
# token forge kar sakta tha. Secret .env se aana chahiye; auth.py production mein
# missing/weak secret pe fail-fast karta hai aur dev mein sirf warning deta hai.
os.environ.setdefault("ANTHROPIC_API_KEY", "your-api-key-here")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from uvicorn import run
import importlib

# "backend.app.main" hi import karo — routes (predict.py) bhi "backend.app.main" se
# ml_pipeline import karte hain. "app.main" se import karne par 2 alag module instances
# bante the → doosra ml_pipeline loaded nahi rehta tha → "Models not loaded" (BUG-3 fix).
main_module = importlib.import_module("backend.app.main")
app = main_module.app

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000, log_level="info")
