"""Single-file station configuration; no claim of official pilot status."""
import json
import os
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "config" / "station.json"


def station():
    return json.loads(Path(os.environ.get("AQUASENTINEL_CONFIG", DEFAULT)).read_text(encoding="utf-8"))
