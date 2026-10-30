# Clearwell RO Monitor — 3D concept assembly

`clearwell_ro_concept.glb` is a coloured 3D concept assembly in millimetres. It is for explaining the project, checking component placement, and planning the first physical prototype.

Open it in a 3D viewer that supports GLB, or use `clearwell_ro_concept.obj` in a CAD or rendering tool. The GLB is also stored in the account's 3DEXPERIENCE 3DDrive as `clearwell_ro_concept.glb`.

## What the model contains

1. A wall panel with three pre-filter housings.
2. An RO membrane housing above the filters.
3. A pump on vibration mounts.
4. Orange raw-water tubing, blue purified-water tubing, and a dark waste-water line.
5. A permeate-flow meter, pressure transducer, raw-water TDS probe, and output-water TDS probe.
6. A separate electronics enclosure with a USB-C microcontroller-board placeholder, headers, status LEDs, and a temporary pressure potentiometer.
7. Colour-coded conceptual sensor wires that converge at the board.

The model uses an assumed 620 mm × 440 mm wall panel. It does not claim the exact dimensions, electrical pins, voltage levels, pressure rating, membrane type, or tubing diameter of the parts you eventually buy.

## Flow path

```text
Raw input → 3 pre-filters → pump → RO membrane → flow sensor → clean-water outlet
                                      └──────────→ waste-water outlet
```

The sensor readings feed the microcontroller through the enclosure:

```text
current + flow + pressure + raw TDS + output TDS → USB-C board → Mac dashboard → status model
```

## About simulation

This assembly is useful for a visual design review and for deciding where each component will sit. A real fluid simulation needs the real pump curve, membrane geometry, water temperature, raw-water TDS, tubing inner diameter, flow rate, and pressure limits. Add those after choosing parts; then use the account's Fluid Model Creation and Fluid Scenario Creation apps to simulate pressure drop and flow.

## Rebuilding it

The source is [`tools/generate_assembly.py`](../tools/generate_assembly.py). From the project folder, run:

```bash
PYTHONPATH=.vendor python3 tools/generate_assembly.py
```
