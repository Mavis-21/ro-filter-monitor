# Clearwell — RO Monitor Lab

A local research prototype for a reverse-osmosis (RO) purifier. Change the sensor values in a white-themed dashboard and inspect a model's `normal`, `warning`, or `critical` response.

## What is trained

1. **Household status demo:** a random-forest classifier trained on reproducible **simulated** RO filter lifecycles. Its labels represent simulated healthy, early-degradation, and severe-degradation states. The dashboard uses this model for the sensor playground.
2. **NREL research model:** a gradient-boosted regressor trained on the public NREL steady-state data and three variable-pressure ramp campaigns. It predicts experimental permeate flow. The entire fourth ramp campaign was held out for testing.

These are separate models because NREL's seawater experiment runs at roughly **34–63 bar**, while the household simulator uses much lower pressure. NREL data does not contain pump current, household filter history, or verified replacement dates. **There is no trained remaining-useful-life model yet.** A displayed simulation accuracy is not a claim of field accuracy.

## Quick start

Requires Python 3.9 or newer.

```bash
cd ro-filter-monitor
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 download_data.py
python3 train.py
python3 -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). The included `models/model.joblib` is a trained convenience copy; run `train.py` to reproduce it with the documented sources. Only load model files from a trusted source: joblib files use Python's pickle format.

Run the focused checks with:

```bash
python3 -m unittest discover -s tests -v
```

## What each sensor means

| Input | Meaning |
|---|---|
| Pump current | Electrical motor load in amperes |
| Permeate flow | Purified water produced each minute |
| Pressure | Hydraulic pressure; may initially come from a potentiometer simulation |
| Raw and output TDS | Approximate dissolved-solid readings before and after RO |
| Salt rejection | `(1 - output TDS / raw TDS) × 100` |
| Cumulative litres, age, runtime | Use since this filter was installed |
| Trends | Percentage change during a recent week |

The dashboard is a **manual experiment**. It does not ingest a physical ESP32 device yet. The status model is evaluated only while the pump is running. When current and flow are both near zero, it returns `off` rather than pretending to assess filter health. Contradictory readings such as flowing water with near-zero pump current are flagged for inspection.

Conductivity-derived TDS depends on temperature and water composition. TDS and salt rejection alone do not certify drinking-water safety.

## Results from the included training run

The exact metrics are saved in [`models/metrics.json`](models/metrics.json). The synthetic test held out **63 complete simulated lifecycles** rather than random individual readings. The NREL test held out the entire **400 psi ramp campaign**.

| Evaluation | Result | Scope |
|---|---:|---|
| Status accuracy | 87.1% | Simulated household scenarios only |
| Status macro F1 | 0.810 | Simulated household scenarios only |
| Critical recall | 88.9% | Simulated household scenarios only |
| NREL permeate-flow MAE | 0.216 L/min | Separate experimental campaign |
| NREL permeate-flow R² | 0.949 | Separate experimental campaign |

The warning class is currently the weakest (F1 about 0.608). Additional real, independently confirmed examples are necessary before using any status for maintenance decisions.

## Data and attribution

The NREL files are downloaded from the [Department of Energy / NREL dataset page](https://catalog.data.gov/dataset/experimental-wave-desalination-data-with-variable-feed-and-pressure-input). The work is credited there to Kurby Sitterley, Zach Binger, and Scott Jenne and is available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). `download_data.py` fetches `steady_state.zip` and `ramp.zip` from that source. Raw downloads are ignored by Git; `train.py` reads them without modifying the source files.

The household simulator in `simulation.py` is original generated data for this prototype, **not a public research dataset or real sensor data**. It uses a fixed seed so results can be reproduced.

## Next real-data milestone

Connect the ESP32 sensors and record timestamp, device ID, filter ID, measured values, pump state, calibration state, and every filter installation/replacement event. Keep simulated pressure readings marked as simulated. After enough complete RO membrane lifecycles are collected, compare a simple age/usage baseline against regression and survival models using whole lifecycles held out for evaluation. Deploy a model only if it improves on the baseline and its error in days is acceptable.
