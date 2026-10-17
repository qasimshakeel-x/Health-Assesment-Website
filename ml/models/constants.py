"""Feature names used across the ML pipeline."""
# Input features for disease risk prediction
DISEASE_RISK_FEATURES = [
    "age", "gender", "bmi", "sleep_hours", "exercise_level",
    "smoking", "alcohol", "family_diabetes", "family_heart",
    "family_hypertension", "family_cancer"
]

# Phase-1 per-disease feature schema: base 11 features + 3 disease-specific screening
# symptoms. Moved here from ml/data/generate_datasets.py (removed — synthetic generator was
# replaced by ml/data/prepare_real.py). This list IS the column order used by
# DiseaseRiskEngine._build_vector and by ml/train_config.py (BUG-5: training == inference).
PHASE1_SCHEMAS = {
    "diabetes": DISEASE_RISK_FEATURES + ["freq_urination", "excess_thirst", "weight_loss"],
    "heart": DISEASE_RISK_FEATURES + ["chest_pain", "short_breath", "palpitations"],
    "hypertension": DISEASE_RISK_FEATURES + ["headaches", "dizziness", "blurred_vision"],
    "obesity": DISEASE_RISK_FEATURES + ["sugary_diet", "freq_hunger", "hard_lose_weight"],
}

PHQ9_FEATURES = [
    "phq1", "phq2", "phq3", "phq4", "phq5",
    "phq6", "phq7", "phq8", "phq9"
]

# Depression severity tiers (SDD 5-tier version)
DEPRESSION_LEVELS = {
    (0, 4): "No Depression",
    (5, 9): "Mild",
    (10, 14): "Moderate",
    (15, 19): "Moderately Severe",
    (20, 27): "Severe"
}

# Risk category thresholds
RISK_CATEGORIES = [
    (0, 25, "Low Risk"),
    (25, 50, "Moderate Risk"),
    (50, 75, "High Risk"),
    (75, 100, "Very High Risk")
]

# Longevity score weights
LONGEVITY_WEIGHTS = {
    "bmi": 0.20,
    "sleep": 0.15,
    "exercise": 0.20,
    "disease_risk": 0.25,
    "depression": 0.20
}

# Ensemble weights for disease risk
ENSEMBLE_WEIGHTS = {
    "random_forest": 0.40,
    "xgboost": 0.40,
    "logistic_regression": 0.20
}
