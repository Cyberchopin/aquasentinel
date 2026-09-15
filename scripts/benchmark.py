"""Local synthetic microbenchmark; not throughput under concurrent production load."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aquasentinel.store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/benchmark.json")
    args = parser.parse_args()
    base = datetime(2026, 9, 15, 8, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as folder:
        store = Store(str(Path(folder) / "benchmark.sqlite3"))
        records = [dict(source_id=f"source-{i%25}", external_id=str(i), stream_id=f"creek-{i%10}",
                        observed_at=(base + timedelta(seconds=i)).isoformat(), lat=33.68, lon=-117.82,
                        signal="turbidity", synthetic=True) for i in range(1000)]
        start = time.perf_counter()
        for r in records:
            store.ingest(r, "2026-09-15T09:00:00Z")
        ingest_seconds = time.perf_counter() - start
        duplicates = sum(store.ingest(r, "2026-09-15T10:00:00Z")["duplicate"] for r in records)
        before = store.snapshot("creek-0", "2026-09-15T12:00:00Z")
        times = []
        for _ in range(100):
            start = time.perf_counter()
            store.snapshot("creek-0", "2026-09-15T12:00:00Z")
            times.append((time.perf_counter()-start)*1000)
        store.close()
        reopened = Store(str(Path(folder) / "benchmark.sqlite3"))
        stable = before == reopened.snapshot("creek-0", "2026-09-15T12:00:00Z")
        reopened.close()
    result = dict(dataset="1000 synthetic observations / 10 streams / 25 declared sources",
                  python=platform.python_version(), platform=platform.platform(),
                  measured_at=datetime.now(timezone.utc).isoformat(),
                  ingest_seconds=round(ingest_seconds, 4), duplicate_replays=duplicates,
                  snapshot_runs=100, records_per_snapshot=100,
                  snapshot_median_ms=round(statistics.median(times), 4),
                  snapshot_p95_ms=round(sorted(times)[math.ceil(.95*len(times))-1], 4),
                  identical_after_restart=stable,
                  limitations="Single-process local SQLite microbenchmark; synthetic data; no predictive accuracy, concurrent throughput or production-scale claim.")
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
