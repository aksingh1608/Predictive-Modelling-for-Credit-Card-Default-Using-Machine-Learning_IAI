"""FastAPI service for credit-card default risk prediction."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.preprocess import MODELS_DIR, transform_input
from api.schemas import (
    DriverItem,
    PredictRequest,
    PredictResponse,
    WhatIfRequest,
    WhatIfResponse,
    WhatIfResult,
)

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

_model = None
_scaler = None
_metadata: dict = {}
_feature_columns: list[str] = []


def _load_models():
    global _model, _scaler, _metadata, _feature_columns
    model_path = MODELS_DIR / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. "
            "Run Section 7 in Credit_Card_Default_Prediction.ipynb to export your tuned model."
        )
    _model = joblib.load(model_path)
    _scaler = joblib.load(MODELS_DIR / "scaler.joblib")
    _metadata = json.loads((MODELS_DIR / "metadata.json").read_text())
    _feature_columns = json.loads((MODELS_DIR / "feature_columns.json").read_text())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_models()
    yield


app = FastAPI(
    title="Credit Default Risk API",
    description="Predict next-month credit card default from client features.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _risk_label(prob: float, threshold: float) -> tuple[str, str]:
    if prob >= threshold:
        return "Likely default", "high"
    if prob >= threshold * 0.6:
        return "Elevated risk", "medium"
    return "Low risk", "low"


def _payment_summary(row: dict) -> dict[str, int | str]:
    pay_cols = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    values = [int(row[c]) for c in pay_cols]
    late = sum(1 for v in values if v > 0)
    on_time = sum(1 for v in values if v <= 0)
    worst = max(values)
    trend = "improving" if values[0] <= values[-1] else "worsening" if values[0] > values[-1] else "stable"
    return {
        "months_late": late,
        "months_on_time": on_time,
        "worst_delay": worst,
        "trend": trend,
        "pay_0": values[0],
    }


def _recommendations(row: dict, prob: float, threshold: float, drivers: list[DriverItem]) -> list[str]:
    tips: list[str] = []
    pay = _payment_summary(row)

    if int(row.get("PAY_0", 0)) > 0:
        tips.append(
            f"PAY_0 shows {pay['pay_0']} month(s) late — bringing the latest payment current "
            "is the single strongest lever (see notebook SHAP: PAY_0 dominates)."
        )
    elif int(row.get("PAY_0", 0)) == 0:
        tips.append("Latest payment is neutral (PAY_0 = 0). Paying ahead of schedule (PAY_0 = -1) may further reduce risk.")

    if pay["months_late"] >= 3:
        tips.append(
            f"{pay['months_late']} of 6 months show late status. A sustained on-time streak over 3+ months "
            "typically lowers default probability in tree models."
        )

    if pay["trend"] == "worsening":
        tips.append("Payment delay is worsening over time — early intervention (payment plan, limit review) is advised.")
    elif pay["trend"] == "improving":
        tips.append("Payment behaviour is improving — maintain current trajectory to keep risk down.")

    bill_cols = [f"BILL_AMT{i}" for i in range(1, 7)]
    bills = [float(row.get(c, 0) or 0) for c in bill_cols]
    limit = float(row.get("LIMIT_BAL", 1) or 1)
    util = max(bills) / limit if limit > 0 else 0
    if util > 0.8:
        tips.append(
            f"Latest bill is ~{util:.0%} of credit limit — high utilisation increases default risk. "
            "Consider paying down balance or requesting a limit review."
        )

    if int(row.get("RISK_RATING", 1)) >= 3:
        tips.append("Internal risk rating is High (3). Manual review recommended regardless of model score.")
    elif int(row.get("RISK_RATING", 1)) == 2 and prob >= threshold * 0.6:
        tips.append("Medium risk rating combined with elevated model score — monitor closely next billing cycle.")

    if prob >= threshold:
        tips.append(
            f"Probability exceeds decision threshold ({threshold:.2f}). "
            "Flag for collections review or offer structured repayment."
        )
    elif prob >= threshold * 0.6:
        tips.append("Elevated but below default threshold — proactive reminder before next due date.")
    else:
        tips.append("Below default threshold — standard servicing; re-score after next statement.")

    driver_names = {d.feature.upper().replace(" ", "_") for d in drivers}
    if any("PAY_0" in n for n in driver_names):
        tips.insert(0, "Top driver: latest repayment status — prioritise fixing PAY_0 before other fields.")

    return tips[:5]


def _score_profile(row: dict) -> PredictResponse:
    if _model is None:
        raise HTTPException(503, "Model not loaded")

    try:
        X = transform_input(row)
        X_scaled = _scaler.transform(X.values)
        prob = float(_model.predict_proba(X_scaled)[0, 1])
    except Exception as exc:
        raise HTTPException(400, f"Preprocessing failed: {exc}") from exc

    threshold = float(_metadata.get("risk_threshold", 0.5))
    label, level = _risk_label(prob, threshold)

    importances = _model.feature_importances_
    row_imp = sorted(
        zip(_feature_columns, (importances * X_scaled[0]).tolist()),
        key=lambda x: -abs(x[1]),
    )[:5]
    drivers = [
        DriverItem(feature=name.replace("CITY_", "City "), score=round(abs(v), 4))
        for name, v in row_imp
    ]

    return PredictResponse(
        default_probability=round(prob, 4),
        risk_label=label,
        risk_level=level,
        model_name=_metadata.get("model_name", "Random Forest"),
        top_drivers=drivers,
        threshold=threshold,
        recommendations=_recommendations(row, prob, threshold, drivers),
        payment_summary=_payment_summary(row),
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "model": _metadata.get("model_name"),
    }


@app.get("/api/metadata")
def metadata():
    cities = json.loads((MODELS_DIR / "cities.json").read_text())
    return {**_metadata, "cities": cities}


@app.post("/api/predict", response_model=PredictResponse)
def predict(body: PredictRequest):
    return _score_profile(body.model_dump())


@app.post("/api/whatif", response_model=WhatIfResponse)
def whatif(body: WhatIfRequest):
    baseline_row = body.profile.model_dump()
    baseline = _score_profile(baseline_row)

    results: list[WhatIfResult] = []
    for scenario in body.scenarios:
        modified = {**baseline_row, **scenario.changes}
        scored = _score_profile(modified)
        results.append(
            WhatIfResult(
                label=scenario.label,
                default_probability=scored.default_probability,
                risk_label=scored.risk_label,
                risk_level=scored.risk_level,
                delta_vs_baseline=round(scored.default_probability - baseline.default_probability, 4),
            )
        )

    return WhatIfResponse(baseline=baseline, scenarios=results)


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
