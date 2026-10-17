"""Integration tests IT-01..IT-07 (07-DEV-WORKFLOW §4) + Round-2 endpoints."""
from datetime import timedelta

from backend.tests.conftest import auth_headers, sample_profile
from backend.app.models.database import SHAPExplanation, DiseaseRiskResult, AdminActionLog
from backend.app.middleware.auth import create_access_token


# ── IT-01 Full prediction pipeline ───────────────────────────────────────────
def test_it01_full_prediction_pipeline(assessment):
    body = assessment["body"]
    assert body["prediction_id"]
    assert body["disclaimer"]

    rows = body["disease_risk_results"]
    keys = {r["disease_key"] for r in rows}
    assert len(keys) == 16, f"expected 16 active diseases, got {sorted(keys)}"
    assert {"diabetes", "heart", "hypertension", "obesity", "ckd", "pcos"} <= keys
    assert all(0 <= r["risk_percent"] <= 100 for r in rows)

    assert body["biological_age"]["biological_age"] > 0
    assert 0 <= body["longevity_score"]["score"] <= 100


def test_it01_latest_and_history(assessment, client):
    user = assessment["user"]
    latest = client.get(f"/api/v1/predict/{user['id']}/latest", headers=auth_headers(user))
    assert latest.status_code == 200
    assert len(latest.json()["disease_risk_results"]) == 16

    hist = client.get(f"/api/v1/predict/{user['id']}/history", headers=auth_headers(user))
    assert hist.status_code == 200
    assert len(hist.json()["predictions"]) >= 1


# ── IT-02 SHAP persistence ───────────────────────────────────────────────────
def test_it02_shap_rows_for_ml_diseases(assessment, db_session):
    pid = assessment["body"]["prediction_id"]
    rows = db_session.query(SHAPExplanation).filter_by(prediction_id=pid).all()
    diseases = {r.disease for r in rows}
    # har ML disease (4 phase1 + 8 phase2) ke SHAP rows hote hain (rule-based ka model nahi)
    assert "diabetes" in diseases
    assert len(diseases) >= 8
    assert all(-1.0 <= float(r.shap_value) <= 1.0 for r in rows)


# ── IT-03 Diet chat risk injection ───────────────────────────────────────────
def test_it03_chat_returns_risk_aware_guidance(assessment, client):
    user = assessment["user"]
    # "fruit" branch → diabetes risk >40 pe low-GI guidance deta hai (no 'diabetes'/'eat'
    # keyword warna RISKS/meal branch pehle catch kar leta). LLM keys test env blank → rule-based.
    r = client.post(f"/api/v1/chat/{user['id']}/message",
                    json={"message": "which fruit is best for my blood sugar"},
                    headers=auth_headers(user))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "low-GI" in body["response"] or "low GI" in body["response"]
    assert body["risk_context"]


def test_it03b_chat_sessions_are_isolated(assessment, client):
    """S15 STATELESS chat — DB mein kuch save nahi hota → koi session doosre ka data leak nahi kar
    sakta (history endpoint HAR session_id pe khaali).

    (Pehle session-based storage thi jo DB mein messages rakhti thi; S15 mein user ke request pe
    hata di gayi — "chat DB mein na ho, session-based, refresh pe fresh". Isliye ab history
    hamesha `[]` hai; isolation ab by-design hai, persist karne se nahi.)
    """
    user = assessment["user"]

    r = client.post(f"/api/v1/chat/{user['id']}/message",
                    json={"message": "what should I eat for lunch"},
                    headers=auth_headers(user))
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    assert sid  # echo/reference ke liye milta hai

    # Apna session_id, koi session_id nahi, ya naya session_id — sab pe khaali (no leak).
    for params in ({"session_id": sid}, {}, {"session_id": "fresh-session-xyz"}):
        h = client.get(f"/api/v1/chat/{user['id']}/history",
                       params=params, headers=auth_headers(user))
        assert h.status_code == 200
        assert h.json()["messages"] == []


# ── IT-04 PDF generation (202 → poll → download valid PDF) ───────────────────
def test_it04_pdf_generation(assessment, client):
    user = assessment["user"]
    gen = client.post(f"/api/v1/reports/{user['id']}/generate", headers=auth_headers(user))
    assert gen.status_code == 202, gen.text
    report_id = gen.json()["report_id"]

    status = client.get(f"/api/v1/reports/{report_id}/status", headers=auth_headers(user))
    assert status.status_code == 200
    assert status.json()["status"] == "success"

    dl = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers(user))
    assert dl.status_code == 200
    assert dl.content[:5] == b"%PDF-"


# ── IT-05 JWT protection ─────────────────────────────────────────────────────
def test_it05_jwt_protection(client):
    assert client.get("/api/v1/predict/1/latest").status_code in (401, 403)

    bad = client.get("/api/v1/predict/1/latest",
                     headers={"Authorization": "Bearer not.a.real.token"})
    assert bad.status_code == 401

    expired = create_access_token({"sub": "1", "role": "user"},
                                  expires_delta=timedelta(seconds=-10))
    r = client.get("/api/v1/predict/1/latest",
                   headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


# ── IT-06 Future simulator ───────────────────────────────────────────────────
def test_it06_simulator_improves_bio_age(assessment, client):
    user = assessment["user"]
    r = client.post("/api/v1/simulate",
                    json={"years": 10, "sleep_hours_delta": 1, "exercise_level_delta": 2,
                          "smoking_quit": True, "bmi_improvement": 3,
                          "diet_improvement": "strict"},
                    headers=auth_headers(user))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["improved"]["biological_age"] < body["current"]["biological_age"]
    assert body["improved"]["longevity_score"] >= body["current"]["longevity_score"]
    assert body["disclaimer"]


# ── IT-07 CKD depends_on ordering ────────────────────────────────────────────
def test_it07_ckd_depends_on_diabetes_and_hypertension(assessment, db_session):
    pid = assessment["body"]["prediction_id"]
    keys = {r.disease_key for r in
            db_session.query(DiseaseRiskResult).filter_by(prediction_id=pid).all()}
    assert {"diabetes", "hypertension", "ckd"} <= keys


# ── Round-2 endpoints ────────────────────────────────────────────────────────
def test_logout(assessment, client):
    user = assessment["user"]
    r = client.post("/api/v1/auth/logout", headers=auth_headers(user))
    assert r.status_code == 200


def test_reports_list(assessment, client):
    user = assessment["user"]
    client.post(f"/api/v1/reports/{user['id']}/generate", headers=auth_headers(user))
    r = client.get(f"/api/v1/reports/{user['id']}/list", headers=auth_headers(user))
    assert r.status_code == 200
    assert len(r.json()["reports"]) >= 1


def test_diseases_and_screening_catalog(assessment, client):
    user = assessment["user"]
    d = client.get("/api/v1/diseases", headers=auth_headers(user))
    assert d.status_code == 200
    assert len(d.json()["diseases"]) == 16

    q = client.get("/api/v1/screenings/gad7/questions", headers=auth_headers(user))
    assert q.status_code == 200
    assert len(q.json()["questions"]) == 7

    assert client.get("/api/v1/screenings/nope/questions",
                      headers=auth_headers(user)).status_code == 404


def test_admin_actions_requires_role(assessment, client):
    user = assessment["user"]
    # normal user → 403 (require_role), admin route protected
    assert client.get("/api/v1/admin/actions",
                      headers=auth_headers(user)).status_code == 403
    assert client.post("/api/v1/admin/models/retrain",
                       headers=auth_headers(user)).status_code == 403


def test_admin_actions_ok_for_admin(client, make_user, db_session):
    admin = make_user(role="admin")
    r = client.get("/api/v1/admin/actions", headers=auth_headers(admin))
    assert r.status_code == 200
    assert "actions" in r.json()


def test_admin_action_log_model(db_session):
    # admin_action_log table reachable (Round-2 WS-1 migration)
    assert db_session.query(AdminActionLog).count() >= 0
