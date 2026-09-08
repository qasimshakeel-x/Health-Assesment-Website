"""Prediction routes — submit health profile, get latest results."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.models.database import get_db, User, UserProfile, PredictionResult, SHAPExplanation
from backend.app.schemas.user import HealthProfileInput
from backend.app.middleware.auth import get_current_user
from backend.app.main import ml_pipeline, redis_client
import json
import numpy as np

router = APIRouter()


def to_float(val):
    """Convert numpy/pandas types to native Python float."""
    if val is None:
        return None
    if isinstance(val, (np.floating, np.integer)):
        return float(val)
    return float(val)


@router.post("", response_model=dict)
def submit_prediction(
    data: HealthProfileInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit health profile and run full ML pipeline."""
    # Save profile
    profile = UserProfile(
        user_id=current_user.id,
        name=data.name,
        age=data.age,
        gender=data.gender,
        height=data.height,
        weight=data.weight,
        sleep_hours=data.sleep_hours,
        exercise_level=data.exercise_level,
        smoking=data.smoking,
        alcohol=data.alcohol,
        family_history=data.family_history,
        phq9=data.phq9
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Run ML pipeline
    results = ml_pipeline.run_pipeline(data.model_dump())

    # Save prediction (convert numpy types to native Python)
    prediction = PredictionResult(
        user_profile_id=profile.id,
        diabetes_risk=to_float(results["disease_risks"].get("diabetes", {}).get("risk_percent")),
        heart_risk=to_float(results["disease_risks"].get("heart", {}).get("risk_percent")),
        hypertension_risk=to_float(results["disease_risks"].get("hypertension", {}).get("risk_percent")),
        obesity_risk=to_float(results["disease_risks"].get("obesity", {}).get("risk_percent")),
        biological_age=to_float(results["biological_age"]["biological_age"]),
        longevity_score=to_float(results["longevity_score"]["score"]),
        depression_level=str(results["depression"]["severity"]),
        depression_confidence=to_float(results["depression"]["confidence"])
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    # Save SHAP
    for i, item in enumerate(results.get("shap_explanations", [])):
        shap = SHAPExplanation(
            prediction_id=prediction.id,
            disease="ensemble",
            feature_name=item["feature"],
            shap_value=to_float(item["shap_value"]),
            rank=i + 1
        )
        db.add(shap)
    db.commit()

    return {"profile_id": profile.id, "prediction_id": prediction.id, **results}


@router.get("/{user_id}/latest")
def get_latest_prediction(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest prediction for a user."""
    prediction = (
        db.query(PredictionResult)
        .join(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .order_by(PredictionResult.created_at.desc())
        .first()
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="No predictions found")

    return {
        "id": prediction.id,
        "diabetes_risk": to_float(prediction.diabetes_risk),
        "heart_risk": to_float(prediction.heart_risk),
        "hypertension_risk": to_float(prediction.hypertension_risk),
        "obesity_risk": to_float(prediction.obesity_risk),
        "biological_age": to_float(prediction.biological_age),
        "longevity_score": to_float(prediction.longevity_score),
        "depression_level": prediction.depression_level,
        "depression_confidence": to_float(prediction.depression_confidence),
        "created_at": str(prediction.created_at)
    }
