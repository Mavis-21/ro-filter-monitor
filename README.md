# Clearwell — RO Monitor Lab

A local dashboard for learning how a reverse-osmosis (RO) filter monitor could work. It has two pages: a **model playground** for simulated cases and a **sensor station** for a future USB-connected microcontroller.

## Quick start

Requires Python 3.9 or newer.

```bash
cd ro-filter-monitor
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). A trained model is included. To rebuild the model and the synthetic CSV, run `python3 train.py`. Only load model files from a trusted source because joblib uses Python pickle.

## How to use it

**Model playground:** Move the sliders, choose a preset, or click **Generate random test**. The random button draws one row from a simulated filter lifecycle that was excluded from model training. It shows both the simulated answer and the model's answer. The running click count is for exploration; the full test score below uses all held-out rows. Download the complete synthetic dataset from the dashboard or [`data/synthetic/ro_lifecycles.csv`](data/synthetic/ro_lifecycles.csv).

**Sensor station:** Connect a microcontroller by USB, refresh the port list, select its serial port, and click **Connect**. Then click **Check all sensors**, open the live view, and click **Predict from live sensors**. The software checks whether a recent, valid number arrived for each reading. That checks communication, not the physical calibration or water safety of a sensor. The live prediction works when the board follows the message format below.

## Four sensor groups

| Group | Reading sent to the Mac |
|---|---|
| Pump current | `current_a` in amperes |
| Permeate flow | `flow_l_min` in litres per minute |
| Pressure | `pressure_bar` in bar; a potentiometer can simulate this initially |
| Dual TDS | `raw_tds_ppm` and `output_tds_ppm` in ppm |

The fourth group has two measurements. Software calculates salt rejection as `(1 - output TDS / raw TDS) × 100`. The model also uses filter age, cumulative litres, pump runtime, and recent trends; these are **calculated or recorded over time**, not extra physical sensors. In the current live prototype, litres and runtime count only since connection, age is entered by hand, and trends are set to zero. Permanent history is a later step.

## Board-to-Mac serial format

Send one JSON line at **115200 baud**, ideally about once per second:

```json
{"current_a":1.5,"flow_l_min":1.7,"pressure_bar":6.6,"raw_tds_ppm":520,"output_tds_ppm":34}
```

Each line needs all five numeric fields. Your board firmware can use C or C++ to read the sensors and print the JSON line over USB serial. The pressure field may come from a potentiometer while testing; label it as simulated in any real-data collection. Board pin assignments, electrical scaling, and calibration depend on your exact board and sensors, so those need to be filled in when the hardware is chosen. A serial packet cannot prove a sensor is wired or calibrated correctly.

## Model and accuracy

The status classifier learns from **23,635 generated rows** across 260 simulated filter lifecycles. It predicts `normal`, `warning`, or `critical`. Each row has a timestamp, lifecycle ID, the five direct readings, calculated salt rejection, usage, trends, and a simulated label. The CSV's `split` column says whether a lifecycle was used for development or held out for final testing.

Training compares three choices on a validation set: the original random forest, a more complex random forest, and gradient boosting. The original random forest scored best on validation, so it remained the selected model. The final test held out **63 entire simulated lifecycles** (5,636 rows), preventing nearby readings from the same lifecycle from appearing in both training and test.

| Held-out simulation metric | Result |
|---|---:|
| Accuracy | 87.1% |
| Macro F1 (balances all three classes) | 0.810 |
| Critical recall | 88.9% |
| Warning F1 | 0.608 |

Exact results are in [`models/metrics.json`](models/metrics.json). These numbers describe performance on **simulated conditions only**. They do not estimate performance on your future sensors or real filters. The warning class is the weakest; tuning the model solely to increase a headline accuracy score could make that class worse.

Ways to improve the real system after the sensors are built:

1. Calibrate each sensor and collect genuine readings across different water sources, pumps, and filters.
2. Record filter installation and replacement dates, confirmed faults, and complete filter lifecycles. Human-reviewed labels are more useful than guessed labels.
3. Store history so flow, current, pressure trends, cumulative litres, and runtime reflect the actual filter lifecycle.
4. Compare simple rule-based thresholds, random forests, boosting, and time-series models using **whole unseen filters** for testing. Track warning F1 and critical recall as well as overall accuracy.
5. Add a remaining-useful-life model only after real replacement lifecycles exist; evaluate its error in days against a simple age/usage baseline.

No remaining-useful-life estimate is currently produced. The status model assesses the pump only while running and flags contradictory readings such as nonzero flow with near-zero current. TDS and salt rejection alone cannot certify drinking-water safety.

## Checks

```bash
python3 -m unittest discover -s tests -v
```

The dataset is original reproducible simulation from [`simulation.py`](simulation.py), not measured water-purifier data or a public research dataset.
