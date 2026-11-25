"""Carregamento dos artefatos do modelo, usado pelo scoring batch e pela API online."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS
from pipeline import config

MODEL_FILE = "model.joblib"
METADATA_FILE = "metadata.json"


class ModelNotTrainedError(FileNotFoundError):
    pass


@dataclass
class FraudModel:
    pipeline: Any
    threshold: float
    version: str
    metadata: dict

    def score(self, features: pd.DataFrame) -> np.ndarray:
        return self.pipeline.predict_proba(features[FEATURE_COLUMNS])[:, 1]


def load_model(artifacts_dir: Path | None = None) -> FraudModel:
    directory = artifacts_dir or config.ARTIFACTS_DIR
    model_path, metadata_path = directory / MODEL_FILE, directory / METADATA_FILE
    if not model_path.exists() or not metadata_path.exists():
        raise ModelNotTrainedError(f"Modelo nao encontrado em {directory}. Rode o treino primeiro.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return FraudModel(
        pipeline=joblib.load(model_path),
        threshold=float(metadata["threshold"]),
        version=metadata["model_version"],
        metadata=metadata,
    )
