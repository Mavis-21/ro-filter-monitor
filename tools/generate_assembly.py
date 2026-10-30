"""Generate an illustrative RO monitoring assembly in millimetres.

This is a concept layout, not a manufacturing drawing or electrical schematic.
Run with PYTHONPATH=.vendor python3 tools/generate_assembly.py
"""

from pathlib import Path

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "design"
OUT.mkdir(exist_ok=True)
scene = trimesh.Scene()


def add(name, mesh, color):
    mesh.visual.face_colors = color
    scene.add_geometry(mesh, node_name=name, geom_name=name)


def box(name, center, size, color):
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(center)
    add(name, mesh, color)


def sphere(name, center, radius, color):
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    mesh.apply_translation(center)
    add(name, mesh, color)


def rod(name, start, end, radius, color, sections=20):
    start, end = np.array(start, dtype=float), np.array(end, dtype=float)
    direction = end - start
    mesh = trimesh.creation.cylinder(radius=radius, height=np.linalg.norm(direction), sections=sections)
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction))
    mesh.apply_translation((start + end) / 2)
    add(name, mesh, color)


def route(name, points, radius, color):
    for i, (a, b) in enumerate(zip(points, points[1:])):
        rod(f"{name}_{i+1}", a, b, radius, color, 12)
    for i, point in enumerate(points[1:-1]):
        sphere(f"{name}_elbow_{i+1}", point, radius, color)


WHITE = [239, 244, 241, 255]
CREAM = [249, 250, 246, 255]
BLUE = [42, 113, 178, 255]
PALE_BLUE = [115, 181, 213, 255]
NAVY = [27, 60, 72, 255]
GREEN = [31, 135, 113, 255]
PCB = [24, 101, 77, 255]
BLACK = [37, 43, 48, 255]
METAL = [147, 158, 165, 255]
SILVER = [190, 202, 207, 255]
GOLD = [216, 168, 75, 255]
RAW = [244, 166, 54, 255]
PURIFIED = [47, 153, 202, 255]
RED = [213, 82, 71, 255]
YELLOW = [237, 202, 76, 255]

# Wall-mounted panel and support rails.
box("01_backplate_620x440mm", [0, 0, -10], [620, 440, 16], WHITE)
for x in (-280, 280):
    for y in (-190, 190):
        rod(f"mounting_bolt_{x}_{y}", [x, y, 0], [x, y, 7], 6, METAL)
box("lower_cartridge_rail", [-110, -127, 8], [370, 18, 18], NAVY)
box("upper_membrane_rail", [-90, 150, 8], [410, 18, 18], NAVY)

# Three cartridge filters. z is depth away from panel.
for idx, x in enumerate((-235, -115, 5), start=1):
    box(f"filter_{idx}_mount", [x, -105, 20], [72, 18, 30], METAL)
    rod(f"filter_{idx}_housing", [x, -88, 58], [x, 45, 58], 31, CREAM, 36)
    rod(f"filter_{idx}_head", [x, 42, 58], [x, 73, 58], 35, BLUE, 36)
    rod(f"filter_{idx}_base", [x, -91, 58], [x, -98, 58], 27, SILVER, 36)
    for side in (-1, 1):
        rod(f"filter_{idx}_port_{side}", [x + side*34, 58, 58], [x + side*52, 58, 58], 8, METAL)

# RO membrane cartridge above filters, with end caps and tubing ports.
rod("04_ro_membrane_housing", [-255, 160, 64], [120, 160, 64], 32, CREAM, 40)
for x in (-260, 125):
    rod(f"membrane_cap_{x}", [x-10, 160, 64], [x+10, 160, 64], 36, BLUE, 40)
for x in (-279, 143):
    rod(f"membrane_port_{x}", [x, 160, 64], [x+(17 if x>0 else -17), 160, 64], 7, METAL)

# Pressure pump and vibration mounts.
box("05_pump_mount", [175, -100, 28], [112, 96, 18], BLACK)
rod("05_pump_motor", [175, -80, 68], [175, 4, 68], 43, NAVY, 40)
rod("05_pump_head", [175, 4, 68], [175, 35, 68], 35, METAL, 36)
for y in (-65, -35, -5):
    rod(f"pump_cooling_fin_{y}", [175, y-2, 68], [175, y+2, 68], 46, BLACK, 36)
for x in (126, 224):
    box(f"pump_foot_{x}", [x, -105, 15], [14, 64, 20], METAL)

# Flow direction: raw input -> filters -> pump -> membrane -> clean output.
route("raw_inlet_orange", [[-295, -170, 49], [-285, -170, 49], [-285, 58, 49], [-280, 58, 58]], 5, RAW)
route("filter1_to_filter2", [[-183, 58, 58], [-169, 89, 58], [-167, 89, 58], [-167, 58, 58]], 5, RAW)
route("filter2_to_filter3", [[-63, 58, 58], [-48, 89, 58], [-47, 89, 58], [-47, 58, 58]], 5, RAW)
route("filters_to_pump", [[57, 58, 58], [90, 58, 58], [90, -118, 58], [130, -118, 68]], 5, RAW)
route("pump_to_membrane", [[210, 35, 68], [240, 35, 68], [240, 173, 68], [143, 173, 68], [143, 160, 64]], 5, RAW)
route("clean_water_blue", [[-296, 160, 64], [-300, 160, 64], [-300, 193, 64], [280, 193, 64], [280, 112, 64]], 5, PURIFIED)
route("waste_water_dark", [[-279, 160, 64], [-279, 113, 90], [-275, 113, 90], [-275, -175, 90]], 4, NAVY)

# Inline flow sensor, pressure sensor and the two TDS probes.
rod("06_permeate_flow_meter_clear_body", [246, 159, 64], [246, 126, 64], 15, PALE_BLUE, 24)
rod("06_flow_meter_rotor", [246, 151, 64], [246, 135, 64], 5, NAVY)
rod("07_pressure_sensor_tee", [240, 86, 68], [251, 86, 68], 10, METAL)
rod("07_pressure_transducer_body", [251, 86, 68], [276, 86, 68], 14, BLACK)
rod("08_raw_tds_probe", [-285, -148, 49], [-254, -148, 49], 6, GOLD)
rod("09_output_tds_probe", [280, 136, 64], [249, 136, 64], 6, GOLD)

# Separate sealed electronics enclosure, open front to expose board and wires.
box("10_electronics_enclosure_base", [177, -147, 8], [220, 122, 16], CREAM)
for x in (70, 284):
    box(f"enclosure_side_{x}", [x, -147, 36], [7, 122, 50], WHITE)
for y in (-204, -90):
    box(f"enclosure_edge_{y}", [177, y, 36], [220, 7, 50], WHITE)
box("11_geeky_board_placeholder_PCB", [175, -147, 45], [130, 64, 5], PCB)
box("board_main_chip", [171, -147, 50], [28, 23, 5], BLACK)
box("board_usb_c_socket", [246, -147, 50], [18, 12, 9], SILVER)
for i in range(10):
    x = 119 + i*12
    box(f"board_header_top_pin_{i+1}", [x, -111, 51], [5, 6, 7], GOLD)
    box(f"board_header_bottom_pin_{i+1}", [x, -183, 51], [5, 6, 7], GOLD)
for i in range(4):
    box(f"board_status_LED_{i+1}", [137+i*11, -147, 51], [5, 5, 3], GREEN if i<3 else YELLOW)

# Wiring is conceptual and grouped by sensor; no exact electrical pins are claimed.
route("wire_current_red", [[173, -50, 100], [275, -50, 100], [275, -120, 72], [220, -120, 55]], 2, RED)
route("wire_flow_blue", [[246, 141, 80], [263, 141, 80], [263, -100, 80], [200, -111, 55]], 2, PURIFIED)
route("wire_pressure_yellow", [[276, 86, 68], [287, 86, 68], [287, -110, 68], [182, -111, 55]], 2, YELLOW)
route("wire_raw_tds_orange", [[-254, -148, 49], [-245, -173, 115], [85, -173, 115], [85, -183, 55], [155, -183, 55]], 2, RAW)
route("wire_output_tds_green", [[249, 136, 64], [255, 136, 110], [296, 136, 110], [296, -196, 110], [178, -183, 55]], 2, GREEN)
route("wire_common_ground_black", [[125, -183, 55], [90, -183, 72], [90, -82, 72]], 2, BLACK)

# Potentiometer stand-in for pressure calibration during development.
box("12_pressure_potentiometer_training_only", [261, -183, 48], [25, 25, 10], BLUE)
rod("12_pressure_potentiometer_knob", [261, -183, 53], [261, -183, 67], 8, BLACK)

scene.export(OUT / "clearwell_ro_concept.glb")
scene.export(OUT / "clearwell_ro_concept.obj")
print(f"Wrote {OUT / 'clearwell_ro_concept.glb'} with {len(scene.geometry)} named objects")
