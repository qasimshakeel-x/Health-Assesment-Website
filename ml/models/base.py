"""Base class for all ML models — Strategy pattern."""
from abc import ABC, abstractmethod
import numpy as np
import pickle
import os
from typing import Dict, Any


class MLModel(ABC):
    """Abstract base class for ML models. All models must implement train and evaluate."""

    def __init__(self, name: str):
        self.name = name
        self.model = None
        self.is_loaded = False

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train the model and return metrics."""
        pass

    @abstractmethod
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Evaluate the model on test data."""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return class probabilities."""
        pass

    def save(self, path: str):
        """Save the trained model to a pickle file."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        self.is_loaded = True

    def load(self, path: str):
        """Load a trained model from a pickle file."""
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        self.is_loaded = True

    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importances if available."""
        if hasattr(self.model, "feature_importances_"):
            return dict(enumerate(self.model.feature_importances_))
        elif hasattr(self.model, "coef_"):
            return dict(enumerate(np.abs(self.model.coef_[0])))
        return {}
