"""Future health simulation route."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.middleware.auth import get_current_user
from backend.app.models.database import get_db, UserProfile, PredictionResult, User
from backend.app.schemas.user import SimulationInput, DISCLAIMER
from ml.models.future_simulator import FutureSimulator

router = APIRouter()
simulator = FutureSimulator()


@router.post("")
def simulate_future(
    data: SimulationInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run future health simulation with lifestyle changes.

    Baseline user ki latest profile + prediction se aata hai (WS-3 — pehle hardcoded fake
    profile tha: bmi 28 / risks 35-28 hamesha, asli data se kabhi nahi badalta tha).
    """
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .order_by(UserProfile.created_at.desc())
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No health profile found — submit the assessment first")

    prediction = (
        db.query(PredictionResult)
        .filter(PredictionResult.user_profile_id == profile.id)
        .order_by(PredictionResult.created_at.desc())
        .first()
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="No prediction found — submit the assessment first")

    # Simulator ko pura context chahiye (WS-5): flat keys purane clients ke liye +
    # `disease_risks` list taake 16 diseases project hon (05-API-SPEC §2 /simulate).
    rows = list(prediction.disease_risk_results or [])
    # registry order (dashboard/jaisa hi order chahiye frontend ko)
    from ml.models.registry import DISEASE_REGISTRY
    order = {k: i for i, k in enumerate(DISEASE_REGISTRY.keys())}
    rows.sort(key=lambda r: order.get(r.disease_key, 999))
    disease_risks = [
        {
            "disease_key": r.disease_key,
            "label": (DISEASE_REGISTRY.get(r.disease_key).label
                      if r.disease_key in DISEASE_REGISTRY else r.disease_key),
            "category": r.category,
            "risk_percent": r.risk_percent,
        }
        for r in rows
    ]
    avg_risk = (sum(d["risk_percent"] or 0 for d in disease_risks) / len(disease_risks)
                if disease_risks else 0.0)

    current_profile = {
        "age": profile.age,
        "bmi": profile.computed_bmi,
        "biological_age": prediction.biological_age,
        "diabetes_risk": prediction.diabetes_risk,
        "heart_risk": prediction.heart_risk,
        # longevity + bio inputs (FutureSimulator dono scenarios ko engine se score kare)
        "sleep_hours": profile.sleep_hours,
        "exercise_level": profile.exercise_level,
        "longevity_score": prediction.longevity_score,
        "phq9_total": sum(profile.phq9 or []),
        "disease_risks": disease_risks,
        "avg_disease_risk": avg_risk,
    }

    changes = {
        "sleep_hours": data.sleep_hours_delta,
        "exercise_level": data.exercise_level_delta,
        "smoking_quit": data.smoking_quit,
        "bmi_improvement": data.bmi_improvement,
        "diet_improvement": data.diet_improvement
    }

    result = simulator.simulate(current_profile, data.years, changes)
    if isinstance(result, dict):
        result["disclaimer"] = DISCLAIMER
    return result
