"""Prediction routes — submit health profile, get latest results."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from backend.app.models.database import (
    get_db, UserProfile, PredictionResult, SHAPExplanation,
    ScreeningResponse, DiseaseRiskResult,
)
from backend.app.schemas.user import HealthProfileInput, DISCLAIMER
from backend.app.middleware.auth import get_current_user
from ml.models.registry import DISEASE_REGISTRY
from ml.predict import band_for, DISCLAIMER as ML_DISCLAIMER

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


def _registry_order(disease_key: str) -> int:
    """Disease_risk_results ko registry order mein sort (dashboard cards ka order)."""
    for i, key in enumerate(DISEASE_REGISTRY.keys()):
        if key == disease_key:
            return i
    return 999


def _model_meta(key: str, risk_percent) -> dict:
    """Per-row `band`/`see_doctor`/`disclaimer` (ML_TRAINING.md §7: every risk carries these).

    Only ML-scored diseases (`scoring=="ml"`) get a model-derived band, and only when a
    `ml/train.py` artifact exists (colorectal is NO_REAL_DATA → no band). Rule-based screeners
    (gad7/sleep_apnea/metabolic_syndrome/burnout) stay band-less."""
    cfg = DISEASE_REGISTRY.get(key)
    if cfg is None or cfg.scoring != "ml":
        return {"band": None, "see_doctor": None, "disclaimer": None}
    band = band_for(key, (to_float(risk_percent) or 0.0) / 100.0)
    if band is None:
        return {"band": None, "see_doctor": None, "disclaimer": None}
    return {"band": band, "see_doctor": band == "high", "disclaimer": ML_DISCLAIMER}


def risk_rows_from_results(results: dict) -> list:
    """Pipeline output → 05-API-SPEC §9 `disease_risk_results` array shape."""
    rows = []
    for key, item in (results.get("disease_risks") or {}).items():
        # Engine already returns band/see_doctor for artifact diseases — prefer it, else derive.
        meta = _model_meta(key, item.get("risk_percent"))
        rows.append({
            "disease_key": key,
            "label": item.get("label") or (DISEASE_REGISTRY[key].label if key in DISEASE_REGISTRY else key),
            "category": item.get("category"),
            "risk_percent": to_float(item.get("risk_percent")),
            "risk_label": item.get("risk_label"),
            "confidence": to_float(item.get("confidence")),
            "band": item.get("band") or meta["band"],
            "see_doctor": item.get("see_doctor") if item.get("see_doctor") is not None else meta["see_doctor"],
            "disclaimer": item.get("disclaimer") or meta["disclaimer"],
        })
    rows.sort(key=lambda r: _registry_order(r["disease_key"]))
    return rows


def risk_rows_from_db(rows) -> list:
    """DiseaseRiskResult ORM rows → same array shape (label registry se).

    `band`/`see_doctor` stored nahi hote (04-DATA-MODEL), isliye yahan artifact threshold se
    dobara derive karte hain taake reload pe bhi wahi model flags dikhein."""
    out = []
    for r in rows:
        cfg = DISEASE_REGISTRY.get(r.disease_key)
        meta = _model_meta(r.disease_key, r.risk_percent)
        out.append({
            "disease_key": r.disease_key,
            "label": cfg.label if cfg else r.disease_key.replace("_", " ").title(),
            "category": r.category,
            "risk_percent": to_float(r.risk_percent),
            "risk_label": r.risk_label,
            "confidence": to_float(r.confidence),
            "band": meta["band"],
            "see_doctor": meta["see_doctor"],
            "disclaimer": meta["disclaimer"],
        })
    out.sort(key=lambda r: _registry_order(r["disease_key"]))
    return out


@router.post("", response_model=dict)
def submit_prediction(
    data: HealthProfileInput,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit health profile and run full ML pipeline."""
    from backend.app.main import ml_pipeline

    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    profile = UserProfile(
        user_id=user_id,
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
        phq9=data.phq9,
        # Phase 2-5 inputs (06-DISEASE-MODULES) — engines inhein norm_profile se padhte hain
        bp_systolic=data.bp_systolic,
        bp_diastolic=data.bp_diastolic,
        waist_circumference=data.waist_circumference,
        diet_quality=data.diet_quality,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Screening rows (04-DATA-MODEL §2): har screener ek row, JSONB blob = wahi payload
    # jo pipeline `extras["screening"][key]` se padhta hai (read-back mein wapas wrap karna).
    for key, payload in (data.screening_responses or {}).items():
        db.add(ScreeningResponse(
            user_profile_id=profile.id,
            screening_key=key,
            responses=payload,
        ))
    db.commit()

    # Run ML pipeline (model_dump = naye columns + screening_responses bhi andar)
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

    # Normalized per-disease rows (04-DATA-MODEL §2, 05-API-SPEC §9) — 16 diseases tak scale.
    # Flat columns (diabetes_risk etc.) upar isi liye rakhay hain: chat.py/reports.py wahi
    # padhte hain (back-compat) — WS-6 mein wo disease_risk_results pe move honge.
    disease_rows = risk_rows_from_results(results)
    for row in disease_rows:
        db.add(DiseaseRiskResult(
            prediction_id=prediction.id,
            disease_key=row["disease_key"],
            category=row["category"],
            risk_percent=max(0.0, min(100.0, float(row["risk_percent"] or 0.0))),
            risk_label=str(row["risk_label"] or "Low Risk"),
            confidence=row["confidence"],
        ))
    db.commit()

    # Save SHAP — per disease rows (Per-disease SHAP: har ML disease ka apna SHAP model se),
    # `disease` key registry vocabulary (12-INTEGRATION §5) use karta hai. Rule-based screeners
    # ka model nahi → unke liye koi row nahi.
    shap_all = results.get("shap_explanations") or {}
    if isinstance(shap_all, dict):
        shap_items = [(d, items) for d, items in shap_all.items()]
    else:  # legacy single-list protection
        shap_items = [("diabetes", shap_all)]
    for disease_key, items in shap_items:
        for i, item in enumerate(items):
            shap = SHAPExplanation(
                prediction_id=prediction.id,
                disease=disease_key,
                feature_name=item["feature"],
                shap_value=to_float(item["shap_value"]),
                rank=i + 1
            )
            db.add(shap)
    db.commit()

    # age bhi bhejo — Dashboard bio-age delta chronological age ke bina 30 fallback se bana raha tha (BUG-6)
    return {
        "profile_id": profile.id,
        "prediction_id": prediction.id,
        "age": data.age,
        "disclaimer": DISCLAIMER,
        "disease_risk_results": disease_rows,
        **results,
    }


@router.get("/{user_id}/latest")
def get_latest_prediction(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest prediction for a user."""
    prediction = (
        db.query(PredictionResult)
        .options(joinedload(PredictionResult.disease_risk_results))
        .join(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .order_by(PredictionResult.created_at.desc())
        .first()
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="No predictions found")

    # profile relationship se age — Dashboard isse bio-age delta ke liye use karta hai (BUG-6)
    age = prediction.profile.age if prediction.profile is not None else None

    return {
        "id": prediction.id,
        "age": age,
        "diabetes_risk": to_float(prediction.diabetes_risk),
        "heart_risk": to_float(prediction.heart_risk),
        "hypertension_risk": to_float(prediction.hypertension_risk),
        "obesity_risk": to_float(prediction.obesity_risk),
        "biological_age": to_float(prediction.biological_age),
        "longevity_score": to_float(prediction.longevity_score),
        "depression_level": prediction.depression_level,
        "depression_confidence": to_float(prediction.depression_confidence),
        "disease_risk_results": risk_rows_from_db(prediction.disease_risk_results),
        "created_at": str(prediction.created_at),
        "disclaimer": DISCLAIMER
    }


@router.get("/{user_id}/history")
def get_prediction_history(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return user's prediction history (05-API-SPEC §4.4, latest first)."""
    predictions = (
        db.query(PredictionResult)
        .options(joinedload(PredictionResult.disease_risk_results))
        .join(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .order_by(PredictionResult.created_at.desc())
        .limit(30)
        .all()
    )
    if not predictions:
        raise HTTPException(status_code=404, detail="No predictions found")

    items = []
    for p in predictions:
        items.append({
            "id": p.id,
            "age": p.profile.age if p.profile is not None else None,
            "diabetes_risk": to_float(p.diabetes_risk),
            "heart_risk": to_float(p.heart_risk),
            "hypertension_risk": to_float(p.hypertension_risk),
            "obesity_risk": to_float(p.obesity_risk),
            "biological_age": to_float(p.biological_age),
            "longevity_score": to_float(p.longevity_score),
            "depression_level": p.depression_level,
            "disease_risk_results": risk_rows_from_db(p.disease_risk_results),
            "created_at": str(p.created_at),
        })
    return {"predictions": items, "disclaimer": DISCLAIMER}
