"""All fixture observations, locations, source identities and rain values are synthetic."""
from datetime import datetime, timedelta, timezone


def seed(store, base=None):
    base = base or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=4)
    events = [
        (0, 0, "weather-demo", "rain-1", "demo-creek-a", "rainfall", 12),
        (30, 31, "citizen-a", "report-1", "demo-creek-a", "turbidity", None),
        (60, 65, "citizen-b", "report-2", "demo-creek-a", "odor", None),
        (90, 160, "citizen-c", "report-3", "demo-creek-a", "normal", None),
        (45, 47, "citizen-d", "report-4", "demo-creek-b", "turbidity", None),
    ]
    for observed, received, source, external, stream, signal, value in events:
        payload = {"source_id": source, "external_id": external, "stream_id": stream,
                   "observed_at": (base + timedelta(minutes=observed)).isoformat(),
                   "lat": 33.68, "lon": -117.82, "signal": signal, "synthetic": True,
                   "note": "Synthetic development fixture. Not an actual environmental report."}
        if value is not None:
            payload.update(value=value, unit="mm", period_hours=6)
        store.ingest(payload, (base + timedelta(minutes=received)).isoformat())
