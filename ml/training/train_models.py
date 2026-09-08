"""Model training script — trains all ML models and saves them as .pkl files."""
import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml.models.disease_risk import DiseaseRiskEngine
from ml.models.depression import DepressionClassifier
from ml.models.constants import DISEASE_RISK_FEATURES, PHQ9_FEATURES


def load_pima_diabetes(path: str) -> tuple:
    """Load PIMA Indians Diabetes dataset from CSV."""
    df = pd.read_csv(path)
    X = df[["Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
             "Insulin", "BMI", "DiabetesPedigreeFunction", "Age"]].values
    y = df["Outcome"].values
    return X, y


def load_heart_disease(path: str) -> tuple:
    """Load UCI Heart Disease dataset."""
    df = pd.read_csv(path)
    X = df.drop("target", axis=1).values
    y = df["target"].values
    return X, y


def generate_synthetic_phq9(n_samples: int = 2000) -> tuple:
    """Generate synthetic PHQ-9 dataset for depression classification."""
    np.random.seed(42)
    X = np.random.randint(0, 4, size=(n_samples, 9))
    # Create realistic correlations: total score determines class
    totals = X.sum(axis=1)
    y = np.zeros(n_samples, dtype=int)
    y[totals >= 5] = 1   # Mild
    y[totals >= 10] = 2   # Moderate
    y[totals >= 15] = 3   # Moderately Severe
    y[totals >= 20] = 4   # Severe
    return X, y


def train_all(data_dir: str = "ml/data"):
    """Train all models and save to ml/models/pkl/."""
    print("Training Disease Risk Ensemble...")
    disease_engine = DiseaseRiskEngine()

    # Train on available datasets
    datasets = {}
    diabetes_path = os.path.join(data_dir, "pima_diabetes.csv")
    heart_path = os.path.join(data_dir, "heart_disease.csv")

    if os.path.exists(diabetes_path):
        X_diab, y_diab = load_pima_diabetes(diabetes_path)
        # Pad features to match expected input (11 features)
        X_padded = np.zeros((X_diab.shape[0], 11))
        X_padded[:, :X_diab.shape[1]] = X_diab
        datasets["diabetes"] = (X_padded, y_diab)
        print(f"  Loaded PIMA Diabetes: {X_diab.shape[0]} samples")

    if os.path.exists(heart_path):
        X_heart, y_heart = load_heart_disease(heart_path)
        n_cols = min(X_heart.shape[1], 11)
        X_padded = np.zeros((X_heart.shape[0], 11))
        X_padded[:, :n_cols] = X_heart[:, :n_cols]
        datasets["heart"] = (X_padded, y_heart)
        print(f"  Loaded Heart Disease: {X_heart.shape[0]} samples")

    if datasets:
        disease_engine.train_all_diseases(datasets)
        disease_engine.save()
        print("  Disease models saved.")
    else:
        print("  WARNING: No training data found. Skipping disease model training.")

    print("\nTraining Depression Classifier...")
    X_phq9, y_phq9 = generate_synthetic_phq9()
    dep_classifier = DepressionClassifier()
    metrics = dep_classifier.train(X_phq9, y_phq9)
    dep_classifier.save()
    print(f"  Depression classifier saved. F1: {metrics['weighted_f1']:.3f}")

    print("\nAll models trained and saved successfully!")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "ml/data"
    train_all(data_dir)
