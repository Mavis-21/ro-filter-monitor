"""Download the two public NREL archives used by train.py."""

from __future__ import annotations

import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DESTINATION = ROOT / "data" / "raw"
SOURCES = {
    "nrel_steady_state.zip": "https://mhkdr.openei.org/files/649/steady_state.zip",
    "nrel_ramp.zip": "https://mhkdr.openei.org/files/649/ramp.zip",
}


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename, url in SOURCES.items():
        path = DESTINATION / filename
        if path.exists():
            print(f"Already present: {path}")
            continue
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, path)
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
