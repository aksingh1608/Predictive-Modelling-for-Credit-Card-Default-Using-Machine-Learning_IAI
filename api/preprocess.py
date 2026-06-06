"""Single-row preprocessing matching the notebook pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

_caps: dict | None = None
_impute: dict | None = None
_feature_columns: list[str] | None = None


def _load_artifacts():
    global _caps, _impute, _feature_columns
    if _caps is None:
        _caps = json.loads((MODELS_DIR / "iqr_caps.json").read_text())
        _impute = json.loads((MODELS_DIR / "impute.json").read_text())
        _feature_columns = json.loads((MODELS_DIR / "feature_columns.json").read_text())
    return _caps, _impute, _feature_columns


def _apply_caps(row: dict[str, Any], caps: dict) -> dict[str, Any]:
    out = dict(row)
    for col, bounds in caps.items():
        if col in out and out[col] is not None:
            lo, hi = bounds["low"], bounds["high"]
            out[col] = float(np.clip(float(out[col]), lo, hi))
    return out


def _apply_impute(row: dict[str, Any], impute: dict) -> dict[str, Any]:
    out = dict(row)
    for col, val in impute["numeric"].items():
        if out.get(col) is None or (isinstance(out[col], float) and np.isnan(out[col])):
            out[col] = val
    for col, val in impute["categorical"].items():
        if out.get(col) is None or (isinstance(out[col], float) and np.isnan(out[col])):
            out[col] = val
    return out


def transform_input(data: dict[str, Any]) -> np.ndarray:
    """Return 1 x n_features scaled array ready for predict_proba."""
    caps, impute, feature_columns = _load_artifacts()

    row = dict(data)
    row = _apply_caps(row, caps)
    row = _apply_impute(row, impute)

    edu = float(row["EDUCATION"])
    if edu in (0, 5, 6):
        row["EDUCATION"] = 4.0
    if float(row["MARRIAGE"]) == 0:
        row["MARRIAGE"] = 3.0

    base_cols = [
        "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
        "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
        "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
        "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
        "RISK_RATING",
    ]
    frame = {c: [float(row[c])] for c in base_cols}

    city = row.get("CITY", "City_1")
    city_col = f"CITY_{city}" if not str(city).startswith("CITY_") else str(city)
    for col in feature_columns:
        if col.startswith("CITY_"):
            frame[col] = [1 if col == city_col else 0]

    df = pd.DataFrame(frame)
    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_columns]

    return df
