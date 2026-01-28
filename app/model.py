import logging
import pickle
from typing import Optional

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from app.errors import ModelIsNotAvailable


class ModelSingleton:
    """
    Singleton class для работы с ML-моделью.
    Просто с DI fastapi сложно сделать нормальное использование модели
    в разных местах.
    """

    _instance = None
    _model = None

    def __init__(self, model_path: str = "model.pkl"):
        self.model_path = model_path

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def train_model(self) -> LogisticRegression:
        """Обучает простую модель на синтетических данных."""
        np.random.seed(42)
        # Признаки: [is_verified_seller, images_qty, description_length, category]
        X = np.random.rand(1000, 4)
        # Целевая переменная: 1 = нарушение, 0 = нет нарушения
        y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
        y = y.astype(int)

        model = LogisticRegression()
        model.fit(X, y)
        return model

    def save_model(self, model: LogisticRegression) -> None:
        with open(self.model_path, "wb") as f:
            pickle.dump(model, f)

    def load_model(self) -> Optional[LogisticRegression]:
        try:
            with open(self.model_path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    def initialize_model(self) -> LogisticRegression:
        model = self.load_model()
        if model is None:
            model = self.train_model()
            self.save_model(model)

        self._model = model
        return model

    def get_model(self) -> LogisticRegression:
        return self._model

    def predict(self, features: np.ndarray) -> tuple[bool, float]:
        try:
            proba = self._model.predict_proba(features)[0]
            prediction = self._model.predict(features)[0]
            return bool(prediction), float(proba[1])
        except AttributeError as e:
            raise ModelIsNotAvailable("Model is not available in ModelSingleton.")


model_client = ModelSingleton()


def get_model():
    return model_client.get_model()
