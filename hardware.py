"""USB serial reader for a future microcontroller sending newline JSON."""

from __future__ import annotations

import json
import math
import threading
import time
from collections import deque

SENSOR_FIELDS = ("current_a", "flow_l_min", "pressure_bar", "raw_tds_ppm", "output_tds_ppm")
SENSOR_RANGES = {
    "current_a": (0, 15),
    "flow_l_min": (0, 10),
    "pressure_bar": (0, 20),
    "raw_tds_ppm": (0.001, 5000),
    "output_tds_ppm": (0, 5000),
}

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


class SensorBridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.connection = None
        self.port = None
        self.latest = {}
        self.received_at = 0.0
        self.error = None
        self.history = deque(maxlen=300)
        self.cumulative_litres = 0.0
        self.runtime_hours = 0.0

    @staticmethod
    def ports():
        if list_ports is None:
            return []
        return [{"device": p.device, "description": p.description} for p in list_ports.comports()]

    def connect(self, port: str):
        if serial is None:
            raise ValueError("pyserial is missing. Install requirements.txt first.")
        valid_ports = {p["device"] for p in self.ports()}
        if port not in valid_ports:
            raise ValueError("Choose a connected USB serial port from the list.")
        self.disconnect()
        connection = serial.Serial(port, 115200, timeout=1)
        with self.lock:
            self.connection = connection
            self.port = port
            self.latest = {}
            self.received_at = 0.0
            self.error = None
            self.history.clear()
            self.cumulative_litres = 0.0
            self.runtime_hours = 0.0
        threading.Thread(target=self._read, args=(connection,), daemon=True).start()

    def disconnect(self):
        with self.lock:
            old = self.connection
            self.connection = None
            self.port = None
            self.latest = {}
            self.received_at = 0.0
        if old is not None:
            old.close()

    def _read(self, connection):
        while connection.is_open:
            with self.lock:
                if self.connection is not connection:
                    break
            try:
                line = connection.readline().decode("utf-8", errors="replace").strip()
                if line:
                    self.ingest(line)
            except Exception as exc:
                with self.lock:
                    self.error = str(exc)
                break

    def ingest(self, line: str):
        try:
            packet = json.loads(line)
            if not isinstance(packet, dict):
                raise ValueError("Expected a JSON object")
            values = {}
            for key in SENSOR_FIELDS:
                value = packet.get(key)
                low, high = SENSOR_RANGES[key]
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high:
                    values[key] = float(value)
            now = time.monotonic()
            with self.lock:
                if self.received_at and now > self.received_at:
                    hours = min((now - self.received_at) / 3600, 1 / 60)
                    self.cumulative_litres += self.latest.get("flow_l_min", 0) * hours * 60
                    if self.latest.get("current_a", 0) > 0.1:
                        self.runtime_hours += hours
                self.latest = values
                self.received_at = now
                self.history.append(values)
                self.error = None
        except (ValueError, json.JSONDecodeError) as exc:
            with self.lock:
                self.error = f"Unreadable sensor packet: {exc}"

    def status(self):
        with self.lock:
            values = dict(self.latest)
            fresh = bool(self.received_at and time.monotonic() - self.received_at <= 3)
            return {
                "port": self.port,
                "connected": self.connection is not None and self.connection.is_open,
                "fresh": fresh,
                "sensor_status": {key: "replying" if fresh and key in values else "waiting" for key in SENSOR_FIELDS},
                "values": values,
                "error": self.error,
                "cumulative_litres_since_connect": round(self.cumulative_litres, 3),
                "runtime_hours_since_connect": round(self.runtime_hours, 3),
                "sample_count": len(self.history),
            }


bridge = SensorBridge()
