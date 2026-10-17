"""pytest fixtures — isolated test DB + TestClient (07-DEV-WORKFLOW §4).

IMPORTANT: ye env vars `backend.app` import hone se PEHLE set hone chahiye, warna
`database.py` (module-level engine) production DB pe bind ho jata hai. `main.py` ka
load_dotenv existing env ko override nahi karta (python-dotenv default), isliye yahan
set kiya hua DATABASE_URL jeet jata hai.
"""
import os
import sys
import pathlib

# Repo root sys.path pe (backend.app / ml imports ke liye)
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Test DB (asli dev data chhedne se bacho) — pehle env set karo
_TEST_DB = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/longevity_platform_test",
)
os.environ["DATABASE_URL"] = _TEST_DB
os.environ.setdefault("JWT_SECRET", "test-secret")
# External LLM calls tests mein band — rule-based fallback exercise hota hai (deterministic)
os.environ["GROQ_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""

import uuid
import pytest


def _ensure_test_database():
    """Admin `postgres` DB se test DB create karo agar na ho (DROP/CREATE ke liye)."""
    import psycopg2
    from psycopg2 import sql

    base, dbname = _TEST_DB.rsplit("/", 1)
    conn = psycopg2.connect(base + "/postgres")
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _database():
    """Session start pe clean test schema (drop + create all tables)."""
    _ensure_test_database()
    from backend.app.models.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — startup pe ML models load hote hain (~20s)."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def pipeline():
    """ML orchestrator (models loaded) — unit tests ke liye."""
    from ml.models.orchestrator import MLPipelineOrchestrator

    orch = MLPipelineOrchestrator()
    orch.load_models()
    return orch


@pytest.fixture
def db_session():
    from backend.app.models.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def make_user(client, db_session):
    """Naya user register karo (optional role). Returns {email, token, id, role}."""

    def _make(role="user", age=45, gender=0):
        email = f"{uuid.uuid4().hex[:10]}@test.local"
        r = client.post(
            "/api/v1/auth/register",
            json={"name": "Test User", "email": email,
                  "password": "testpass123", "age": age, "gender": gender},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        user_id = data["user"]["id"]
        if role != "user":
            from backend.app.models.database import User

            u = db_session.query(User).filter(User.id == user_id).first()
            u.role = role
            db_session.commit()
        return {"email": email, "token": data["access_token"],
                "id": user_id, "role": role}

    return _make


def auth_headers(user):
    return {"Authorization": f"Bearer {user['token']}"}


def _yn(*keys):
    return {k: "yes" for k in keys}


# Poore 16 screeners ke valid payloads — 16 disease rows trigger karne ke liye.
SCREENING_ALL = {
    "diabetes": _yn("freq_urination", "excess_thirst", "weight_loss"),
    "heart": _yn("chest_pain", "short_breath", "palpitations"),
    "hypertension": _yn("headaches", "dizziness", "blurred_vision"),
    "obesity": _yn("sugary_diet", "freq_hunger", "hard_lose_weight"),
    "stroke": _yn("tia_symptoms", "speech_difficulty", "irregular_heartbeat"),
    "sleep_apnea": _yn("snoring", "wake_tired", "witnessed_apnea", "daytime_sleepy"),
    "gad7": {"answers": [2, 2, 2, 2, 2, 2, 2]},
    "ckd": _yn("ankle_swelling", "urination_changes", "ckd_fatigue"),
    "liver": _yn("jaundice", "abdominal_pain", "liver_fatigue"),
    "metabolic_syndrome": _yn("doctor_high_bp", "doctor_high_sugar",
                              "frequent_thirst_urination"),
    "thyroid": _yn("fatigue", "weight_change", "temperature_issues", "hair_skin"),
    "pcos": _yn("irregular_periods", "weight_gain", "excess_hair", "acne"),
    "anemia": _yn("frequent_fatigue", "pale_cold", "lightheadedness", "brittle_nails"),
    "burnout": {"work_hours": 55, "job_satisfaction": 2, "exhaustion": [2, 2, 2]},
    "colorectal": _yn("blood_in_stool", "bowel_change", "colorectal_weight_loss"),
    "lung_cancer_exposure": _yn("passive_smoke", "persistent_cough",
                                "coughing_blood", "breath_shortness"),
}


def sample_profile(**overrides):
    """High-risk female-45 profile (16 diseases eligible) — sab active gates pass."""
    payload = {
        "name": "Test User", "age": 45, "gender": 0,
        "height": 160, "weight": 82, "sleep_hours": 5,
        "exercise_level": 0, "smoking": True, "alcohol": 5,
        "family_history": [1, 1, 1, 1], "phq9": [3] * 9,
        "bp_systolic": 145, "bp_diastolic": 92, "waist_circumference": 95,
        "diet_quality": "poor",
        "screening_responses": SCREENING_ALL,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def profile_payload():
    return sample_profile()


@pytest.fixture
def assessment(client, make_user):
    """Register + full assessment submit → {user, body}. Multiple tests ise reuse karte hain."""
    user = make_user(age=45, gender=0)
    r = client.post("/api/v1/predict", json=sample_profile(), headers=auth_headers(user))
    assert r.status_code == 200, r.text
    return {"user": user, "body": r.json()}
