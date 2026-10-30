"""Local API and dashboard for exploring the two trained models."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 2))

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core import FEATURES, salt_rejection

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"

if not MODEL_PATH.exists() or not METRICS_PATH.exists():
    raise RuntimeError("Model missing. Run `python3 download_data.py` and `python3 train.py` first.")

bundle = joblib.load(MODEL_PATH)
metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
app = FastAPI(title="RO Monitor Lab", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class SensorInput(BaseModel):
    current_a: float = Field(ge=0, le=15)
    flow_l_min: float = Field(ge=0, le=10)
    pressure_bar: float = Field(ge=0, le=20)
    raw_tds_ppm: float = Field(gt=0, le=5000)
    output_tds_ppm: float = Field(ge=0, le=5000)
    cumulative_litres: float = Field(ge=0, le=1_000_000)
    filter_age_days: float = Field(ge=0, le=3000)
    runtime_hours: float = Field(ge=0, le=50_000)
    flow_trend_pct_week: float = Field(ge=-100, le=100)
    current_trend_pct_week: float = Field(ge=-100, le=100)
    pressure_trend_pct_week: float = Field(ge=-100, le=100)


class NrelInput(BaseModel):
    pressure_bar: float = Field(ge=34, le=63)
    feed_flow_l_min: float = Field(ge=14, le=27)
    feed_conductivity_ms_cm: float = Field(ge=50, le=62)
    temperature_c: float = Field(ge=19, le=21)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/model-info")
def model_info() -> dict:
    return metrics


@app.post("/api/predict")
def predict(sensor: SensorInput) -> dict:
    reading = sensor.model_dump() if hasattr(sensor, "model_dump") else sensor.dict()
    rejection = salt_rejection(reading["raw_tds_ppm"], reading["output_tds_ppm"])
    reading["salt_rejection_pct"] = rejection
    if reading["current_a"] <= 0.1 and reading["flow_l_min"] <= 0.05:
        return {
            "status": "off",
            "model_status": "not_evaluated",
            "model_confidence": 0,
            "probabilities": {"normal": 0, "warning": 0, "critical": 0},
            "salt_rejection_pct": round(rejection, 2),
            "outside_training_range": True,
            "notes": ["The pump appears off. Start it and collect flowing-water readings before assessing filter health."],
            "model_source": "simulated household RO scenarios",
            "remaining_life_days": None,
        }
    frame = pd.DataFrame([{key: reading[key] for key in FEATURES}])
    model = bundle["status_model"]
    probabilities = model.predict_proba(frame)[0]
    scores = {label: float(probability) for label, probability in zip(model.classes_, probabilities)}
    model_status = max(scores, key=scores.get)
    status = model_status
    notes = []

    # These basic checks prevent physically contradictory or clearly stalled
    # readings from being presented as a healthy prediction.
    if reading["output_tds_ppm"] > reading["raw_tds_ppm"]:
        status = "critical"
        notes.append("Output TDS is higher than raw-water TDS. Check the sensor calibration and the RO system.")
    if reading["flow_l_min"] == 0 and reading["current_a"] > 0.5:
        status = "critical"
        notes.append("The pump appears active but no permeate flow is measured.")
    if reading["current_a"] <= 0.1 and reading["flow_l_min"] > 0.05:
        status = "critical"
        notes.append("Flow is measured while pump current is near zero. Check the current sensor and plumbing.")

    outside_scope = any(
        [
            reading["current_a"] > 4,
            reading["flow_l_min"] > 3.5,
            reading["pressure_bar"] < 2,
            reading["pressure_bar"] > 12,
            reading["raw_tds_ppm"] < 100,
            reading["raw_tds_ppm"] > 1100,
        ]
    )
    if outside_scope:
        notes.append("One or more inputs fall outside the simulated household training range; treat this result as exploratory.")
    if not notes:
        notes.append(
            {
                "normal": "These readings resemble the simulated healthy examples.",
                "warning": "These readings resemble simulated early degradation. Check the trends and repeat the measurement.",
                "critical": "These readings resemble simulated severe degradation. Inspect the device and confirm with real measurements.",
            }[status]
        )

    return {
        "status": status,
        "model_status": model_status,
        "model_confidence": round(scores[model_status], 4),
        "probabilities": {key: round(value, 4) for key, value in scores.items()},
        "salt_rejection_pct": round(rejection, 2),
        "outside_training_range": outside_scope,
        "notes": notes,
        "model_source": "simulated household RO scenarios",
        "remaining_life_days": None,
    }


@app.post("/api/nrel-flow")
def nrel_flow(values: NrelInput) -> dict:
    reading = values.model_dump() if hasattr(values, "model_dump") else values.dict()
    frame = pd.DataFrame([reading], columns=bundle["nrel_features"])
    predicted_flow = float(bundle["nrel_flow_model"].predict(frame)[0])
    if predicted_flow < 0:
        raise HTTPException(status_code=422, detail="Input produced an invalid flow prediction")
    return {
        "predicted_permeate_flow_l_min": round(predicted_flow, 3),
        "source": "NREL experimental seawater RO data",
        "scope": "Experimental range only; not calibrated for household purifiers",
    }
