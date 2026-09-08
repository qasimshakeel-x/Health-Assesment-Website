"""Feature names used across the ML pipeline."""
# Input features for disease risk prediction
DISEASE_RISK_FEATURES = [
    "age", "gender", "bmi", "sleep_hours", "exercise_level",
    "smoking", "alcohol", "family_diabetes", "family_heart",
    "family_hypertension", "family_cancer"
]

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
