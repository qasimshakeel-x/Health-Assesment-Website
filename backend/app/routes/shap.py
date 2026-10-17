"""SHAP explanation routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.models.database import get_db, User, PredictionResult, SHAPExplanation
from backend.app.middleware.auth import get_current_user

router = APIRouter()


@router.get("/{prediction_id}")
def get_shap_explanations(
    prediction_id: int,
    disease: str | None = Query(None, description="Optional disease key filter (e.g. diabetes, heart_disease)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get SHAP explanations for a prediction (optionally filtered by disease)."""
    prediction = db.query(PredictionResult).filter(PredictionResult.id == prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    query = (
        db.query(SHAPExplanation)
        .filter(SHAPExplanation.prediction_id == prediction_id)
        .order_by(SHAPExplanation.rank)
    )
    if disease:
        query = query.filter(SHAPExplanation.disease == disease)
    explanations = query.all()

    return {
        "prediction_id": prediction_id,
        "explanations": [
            {
                "feature": exp.feature_name,
                "shap_value": exp.shap_value,
                "direction": "increases_risk" if exp.shap_value > 0 else "decreases_risk",
                "disease": exp.disease
            }
            for exp in explanations
        ]
    }
