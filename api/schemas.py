from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    LIMIT_BAL: float = Field(..., ge=0, description="Credit limit (NT$)")
    SEX: int = Field(..., ge=1, le=2, description="1=male, 2=female")
    EDUCATION: int = Field(..., ge=1, le=4)
    MARRIAGE: int = Field(..., ge=1, le=3)
    AGE: float = Field(..., ge=18, le=100)
    PAY_0: int = Field(..., ge=-2, le=9)
    PAY_2: int = Field(..., ge=-2, le=9)
    PAY_3: int = Field(..., ge=-2, le=9)
    PAY_4: int = Field(..., ge=-2, le=9)
    PAY_5: int = Field(..., ge=-2, le=9)
    PAY_6: int = Field(..., ge=-2, le=9)
    BILL_AMT1: float = 0
    BILL_AMT2: float = 0
    BILL_AMT3: float = 0
    BILL_AMT4: float = 0
    BILL_AMT5: float = 0
    BILL_AMT6: float = 0
    PAY_AMT1: float = 0
    PAY_AMT2: float = 0
    PAY_AMT3: float = 0
    PAY_AMT4: float = 0
    PAY_AMT5: float = 0
    PAY_AMT6: float = 0
    RISK_RATING: int = Field(1, ge=1, le=3)
    CITY: str = "City_1"


class DriverItem(BaseModel):
    feature: str
    score: float


class PredictResponse(BaseModel):
    default_probability: float
    risk_label: str
    risk_level: str
    model_name: str
    top_drivers: list[DriverItem]
    threshold: float
    recommendations: list[str]
    payment_summary: dict[str, int | str]


class WhatIfScenario(BaseModel):
    label: str
    changes: dict[str, float | int | str]


class WhatIfRequest(BaseModel):
    profile: PredictRequest
    scenarios: list[WhatIfScenario]


class WhatIfResult(BaseModel):
    label: str
    default_probability: float
    risk_label: str
    risk_level: str
    delta_vs_baseline: float


class WhatIfResponse(BaseModel):
    baseline: PredictResponse
    scenarios: list[WhatIfResult]
