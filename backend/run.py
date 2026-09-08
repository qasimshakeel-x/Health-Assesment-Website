"""AI Longevity Platform — run script."""
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path so "backend.app.main" imports cleanly.
project_root = Path(__file__).resolve().parent.parent
for base in (str(project_root), str(Path(__file__).resolve().parent)):
    if base not in sys.path:
        sys.path.insert(0, base)

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/longevity_platform")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("JWT_SECRET", "change-me-in-production")
os.environ.setdefault("ANTHROPIC_API_KEY", "your-api-key-here")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from uvicorn import run
import importlib
main_module = importlib.import_module("app.main")
app = main_module.app

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000, log_level="info")
