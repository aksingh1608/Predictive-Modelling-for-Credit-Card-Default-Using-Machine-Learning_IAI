"""Save notebook-trained model + preprocessing for the web app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
TARGET = "default.payment.next.month"


def _caps_to_json(caps: dict) -> dict:
    out = {}
    for col, bounds in caps.items():
        if isinstance(bounds, dict):
            out[col] = bounds
        else:
            lo, hi = bounds
            out[col] = {"low": float(lo), "high": float(hi)}
    return out


def export_artifacts(
    model,
    scaler,
    caps: dict,
    feature_columns: list[str],
    *,
    model_name: str,
    X_test_scaled=None,
    y_test=None,
    source: str = "Credit_Card_Default_Prediction.ipynb",
    use_tuned: bool = True,
    impute: dict | None = None,
) -> Path:
    """
    Call this from the last cell of the notebook after training/tuning.

    Parameters match notebook variables: tuned, scaler, caps, X, X_test_scaled, y_test.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if impute is None:
        impute = {
            "numeric": {
                "LIMIT_BAL": 140000.0,
                "AGE": 34.0,
                "PAY_AMT1": 2160.0,
                "PAY_AMT2": 2019.0,
            },
            "categorical": {"SEX": 2.0, "EDUCATION": 2.0, "MARRIAGE": 2.0},
        }

    metadata: dict[str, Any] = {
        "model_name": model_name,
        "target": TARGET,
        "source": source,
        "use_tuned": use_tuned,
        "n_features": len(feature_columns),
        "risk_threshold": 0.5,
    }

    if X_test_scaled is not None and y_test is not None:
        if hasattr(X_test_scaled, "values"):
            X_arr = X_test_scaled.values
        else:
            X_arr = X_test_scaled
        proba = model.predict_proba(X_arr)[:, 1]
        pred = model.predict(X_arr)
        metadata["test_auc_roc"] = round(float(roc_auc_score(y_test, proba)), 4)
        metadata["test_f1"] = round(float(f1_score(y_test, pred)), 4)

    if hasattr(model, "feature_importances_"):
        top = sorted(
            zip(feature_columns, model.feature_importances_.tolist()),
            key=lambda x: -x[1],
        )[:15]
        metadata["top_features"] = [
            {"name": n, "importance": round(v, 4)} for n, v in top
        ]

    city_cols = [c for c in feature_columns if c.startswith("CITY_")]
    cities = ["City_1"] + sorted(c.replace("CITY_", "") for c in city_cols)

    joblib.dump(model, MODELS_DIR / "model.joblib")
    joblib.dump(scaler, MODELS_DIR / "scaler.joblib")
    (MODELS_DIR / "feature_columns.json").write_text(
        json.dumps(list(feature_columns), indent=2)
    )
    (MODELS_DIR / "iqr_caps.json").write_text(json.dumps(_caps_to_json(caps), indent=2))
    (MODELS_DIR / "impute.json").write_text(json.dumps(impute, indent=2))
    (MODELS_DIR / "cities.json").write_text(json.dumps(cities, indent=2))
    (MODELS_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"Exported notebook model → {MODELS_DIR}/")
    print(f"  model: {model_name}")
    if "test_auc_roc" in metadata:
        print(f"  test AUC: {metadata['test_auc_roc']}  F1: {metadata['test_f1']}")
    return MODELS_DIR
