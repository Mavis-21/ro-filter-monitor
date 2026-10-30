"""Train and evaluate a household RO status demo on simulated lifecycles."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(max(1, (os.cpu_count() or 2) - 1)))

import joblib
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.utils.class_weight import compute_sample_weight

from core import FEATURES, LABELS
from simulation import make_simulated_lifecycles

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
DATA_PATH = ROOT / "data" / "synthetic" / "ro_lifecycles.csv"


def train() -> dict:
    rows = make_simulated_lifecycles()
    outer = GroupShuffleSplit(n_splits=1, test_size=0.24, random_state=2311)
    development_index, test_index = next(outer.split(rows[FEATURES], rows.label, rows.lifecycle_id))
    development = rows.iloc[development_index]
    test = rows.iloc[test_index]
    inner = GroupShuffleSplit(n_splits=1, test_size=0.23, random_state=6421)
    train_index, validation_index = next(
        inner.split(development[FEATURES], development.label, development.lifecycle_id)
    )
    fit_rows = development.iloc[train_index]
    validation = development.iloc[validation_index]

    candidates = {
        "random_forest_baseline": RandomForestClassifier(
            n_estimators=180, max_depth=16, min_samples_leaf=3,
            class_weight="balanced_subsample", n_jobs=-1, random_state=2311,
        ),
        "random_forest_refined": RandomForestClassifier(
            n_estimators=240, max_depth=22, min_samples_leaf=2,
            class_weight="balanced_subsample", n_jobs=-1, random_state=2311,
        ),
        "gradient_boosting": HistGradientBoostingClassifier(
            max_iter=220, learning_rate=0.05, max_leaf_nodes=31,
            l2_regularization=0.1, random_state=2311,
        ),
    }
    validation_scores = {}
    for name, candidate in candidates.items():
        weights = compute_sample_weight("balanced", fit_rows.label) if name == "gradient_boosting" else None
        candidate.fit(fit_rows[FEATURES], fit_rows.label, sample_weight=weights)
        prediction = candidate.predict(validation[FEATURES])
        validation_scores[name] = round(float(f1_score(validation.label, prediction, average="macro")), 4)

    winner = max(validation_scores, key=validation_scores.get)
    model = candidates[winner]
    weights = compute_sample_weight("balanced", development.label) if winner == "gradient_boosting" else None
    model.fit(development[FEATURES], development.label, sample_weight=weights)
    predicted = model.predict(test[FEATURES])

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(development[FEATURES], development.label)
    report = classification_report(test.label, predicted, labels=LABELS, output_dict=True, zero_division=0)

    rows["split"] = "development"
    rows.loc[test_index, "split"] = "test"
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(DATA_PATH, index=False)

    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "status_model": {
            "source": "simulated household RO lifecycles only",
            "selected_model": winner,
            "validation_macro_f1_by_model": validation_scores,
            "train_rows": int(len(development)),
            "test_rows": int(len(test)),
            "train_lifecycles": int(development.lifecycle_id.nunique()),
            "test_lifecycles": int(test.lifecycle_id.nunique()),
            "accuracy": round(float(accuracy_score(test.label, predicted)), 4),
            "macro_f1": round(float(f1_score(test.label, predicted, average="macro")), 4),
            "majority_baseline_macro_f1": round(float(f1_score(test.label, baseline.predict(test[FEATURES]), average="macro")), 4),
            "report": report,
            "confusion_matrix": confusion_matrix(test.label, predicted, labels=LABELS).tolist(),
            "label_order": LABELS,
            "class_counts": {key: int(value) for key, value in rows.label.value_counts().items()},
        },
        "limitations": [
            "All status labels and accuracy scores come from simulated household RO lifecycles.",
            "No real filter replacement lifecycles or remaining-life model are available yet.",
        ],
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"status_model": model, "features": FEATURES}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
