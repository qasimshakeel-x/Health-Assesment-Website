"""Base class for all ML models — Strategy pattern."""
from abc import ABC, abstractmethod
import numpy as np
from typing import Dict


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
