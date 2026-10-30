"""Train the demo status model and a separate NREL experimental model."""

from __future__ import annotations

import json
import hashlib
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(max(1, (os.cpu_count() or 2) - 1)))

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import GroupShuffleSplit

from core import FEATURES, LABELS
from simulation import make_simulated_lifecycles


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
MODEL_PATH = ROOT / "models" / "model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"

NREL_FEATURES = [
    "pressure_bar",
    "feed_flow_l_min",
    "feed_conductivity_ms_cm",
    "temperature_c",
]

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_nrel_frame(archive: Path, member: str) -> pd.DataFrame:
    if not archive.exists():
        raise FileNotFoundError(
            f"Missing {archive}. Run `python3 download_data.py` first."
        )
    with zipfile.ZipFile(archive) as source:
        frame = pd.read_csv(source.open(member))

    result = pd.DataFrame(
        {
            "pressure_bar": frame["Feed Pressure (psi)"] * 0.0689475729,
            "feed_flow_l_min": frame["Feed Flowrate (L/min)"],
            "feed_conductivity_ms_cm": frame["Feed Conductivity (mS/cm)"],
            "temperature_c": frame["Feed Temperature (C)"],
            "permeate_flow_l_min": frame["Permeate 1 Flowrate (L/min)"],
        }
    )
    result = result.replace([np.inf, -np.inf], np.nan).dropna()
    return result[(result > 0).all(axis=1)]


def train() -> dict:
    # Simulated household conditions: group by entire simulated filter lifecycle.
    simulated = make_simulated_lifecycles()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.24, random_state=2311)
    train_idx, test_idx = next(
        splitter.split(simulated[FEATURES], simulated["label"], simulated["lifecycle_id"])
    )
    train_rows = simulated.iloc[train_idx]
    test_rows = simulated.iloc[test_idx]
    status_model = RandomForestClassifier(
        n_estimators=180,
        max_depth=16,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=2311,
    )
    status_model.fit(train_rows[FEATURES], train_rows["label"])
    predicted = status_model.predict(test_rows[FEATURES])
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(train_rows[FEATURES], train_rows["label"])
    synthetic_metrics = {
        "source": "simulated household RO lifecycles only",
        "train_rows": int(len(train_rows)),
        "test_rows": int(len(test_rows)),
        "train_lifecycles": int(train_rows["lifecycle_id"].nunique()),
        "test_lifecycles": int(test_rows["lifecycle_id"].nunique()),
        "accuracy": round(float(accuracy_score(test_rows["label"], predicted)), 4),
        "macro_f1": round(float(f1_score(test_rows["label"], predicted, average="macro")), 4),
        "majority_baseline_macro_f1": round(
            float(f1_score(test_rows["label"], dummy.predict(test_rows[FEATURES]), average="macro")), 4
        ),
        "report": classification_report(
            test_rows["label"], predicted, labels=LABELS, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(
            test_rows["label"], predicted, labels=LABELS
        ).tolist(),
        "label_order": LABELS,
        "class_counts": {k: int(v) for k, v in simulated["label"].value_counts().items()},
    }

    # NREL source: train on steady-state and three ramp campaigns; reserve the
    # fourth complete ramp campaign as a genuinely separate experimental test.
    steady = _load_nrel_frame(RAW / "nrel_steady_state.zip", "steady_state/steady_state.csv")
    ramp_archive = RAW / "nrel_ramp.zip"
    training_frames = [steady.iloc[::5]]
    for dp in (100, 200, 300):
        training_frames.append(
            _load_nrel_frame(ramp_archive, f"ramp/ramp_dp_{dp}.csv").iloc[::8]
        )
    real_train = pd.concat(training_frames, ignore_index=True)
    real_test = _load_nrel_frame(ramp_archive, "ramp/ramp_dp_400.csv").iloc[::8]

    flow_model = HistGradientBoostingRegressor(
        max_iter=240,
        learning_rate=0.05,
        max_leaf_nodes=31,
        l2_regularization=0.05,
        random_state=2311,
    )
    flow_model.fit(real_train[NREL_FEATURES], real_train["permeate_flow_l_min"])
    real_prediction = flow_model.predict(real_test[NREL_FEATURES])
    nrel_metrics = {
        "source": "NREL experimental seawater RO; separate dp=400 ramp campaign held out",
        "train_rows": int(len(real_train)),
        "test_rows": int(len(real_test)),
        "mae_l_min": round(float(mean_absolute_error(real_test["permeate_flow_l_min"], real_prediction)), 4),
        "r2": round(float(r2_score(real_test["permeate_flow_l_min"], real_prediction)), 4),
        "mean_baseline_mae_l_min": round(
            float(mean_absolute_error(
                real_test["permeate_flow_l_min"],
                np.full(len(real_test), real_train["permeate_flow_l_min"].mean()),
            )), 4
        ),
        "pressure_range_bar": [
            round(float(real_train["pressure_bar"].min()), 2),
            round(float(real_train["pressure_bar"].max()), 2),
        ],
    }

    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "nrel_archives_sha256": {
            "steady_state": _sha256(RAW / "nrel_steady_state.zip"),
            "ramp": _sha256(RAW / "nrel_ramp.zip"),
        },
        "status_model": synthetic_metrics,
        "nrel_flow_model": nrel_metrics,
        "limitations": [
            "Status accuracy is measured only on simulated household RO lifecycles.",
            "NREL seawater RO equipment runs at much higher pressure than a household purifier.",
            "Neither dataset contains verified household filter replacement events; no remaining-life model is trained.",
        ],
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "status_model": status_model,
            "nrel_flow_model": flow_model,
            "features": FEATURES,
            "nrel_features": NREL_FEATURES,
        },
        MODEL_PATH,
    )
    METRICS_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
