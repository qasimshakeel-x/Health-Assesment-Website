@echo off
cd /d D:\Uni-Project
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/longevity_platform
set REDIS_HOST=localhost
set REDIS_PORT=6379
set JWT_SECRET=change-me-in-production
set ANTHROPIC_API_KEY=your-api-key-here
set FRONTEND_URL=http://localhost:3000
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
