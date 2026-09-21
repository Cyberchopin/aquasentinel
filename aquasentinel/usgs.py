"""One bounded USGS daily-discharge chain, with byte-preserving provenance.

Daily dates stay dates: neither publication instants nor rainfall are inferred.
"""
import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .engine import utc, digest
from .config import station

SITE = station()["stream_id"]
BASE = "https://api.waterdata.usgs.gov/ogcapi/v1/collections"
FIXTURE = Path(__file__).resolve().parent.parent / "data" / "usgs-arroyo-seco-2024-02"
MAX_BYTES = 2_000_000


def urls(start, end):
    common = dict(f="json", monitoring_location_id=SITE, parameter_code="00060", statistic_id="00003")
    return {
        "daily.json": BASE + "/daily/items?" + urlencode(common | {"datetime": f"{start}/{end}", "limit": 40}),
        "series.json": BASE + "/time-series-metadata/items?" + urlencode(common | {"limit": 10}),
        "station.json": BASE + f"/monitoring-locations/items/{SITE}?f=json",
    }


def fetch_bundle(destination, start="2024-02-01", end="2024-02-08"):
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    if not 0 <= days <= 30:
        raise ValueError("Use an inclusive interval of at most 31 days")
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Use a new directory; captured evidence is never overwritten")
    artifacts = {}
    for filename, url in urls(start, end).items():
        with urlopen(Request(url, headers={"Accept": "application/json", "User-Agent": "AquaSentinel-research/0.2"}), timeout=30) as response:
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Response exceeds the bounded fixture size")
            json.loads(body)
            artifacts[filename] = (body, {"requested_url": url, "resolved_url": response.url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": response.status,
                "content_type": response.headers.get("Content-Type"), "etag": response.headers.get("ETag"),
                "last_modified_header": response.headers.get("Last-Modified"),
                "sha256": sha256(body).hexdigest(), "bytes": len(body)})
    manifest = {"schema_version": 1, "provider": "U.S. Geological Survey", "station_id": SITE,
                "requested_start": start, "requested_end": end,
                "attribution": "Credit: U.S. Geological Survey",
                "rights_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
                "original_publication_time": None,
                "time_semantics": "Retrospective daily summaries. Original publication time is unknown; last_modified is a revision timestamp, not initial availability.",
                "files": {k: v[1] for k, v in artifacts.items()}}
    # Validate everything before creating a deliverable directory.
    normalize({k: json.loads(v[0]) for k, v in artifacts.items()}, manifest)
    destination.mkdir(parents=True)
    for filename, (body, _) in artifacts.items():
        (destination / filename).write_bytes(body)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return load_bundle(destination)


def normalize(docs, manifest):
    if manifest.get("schema_version") != 1 or manifest.get("station_id") != SITE:
        raise ValueError("Unsupported manifest/station")
    station = docs["station.json"]
    p = station["properties"]
    if station["id"] != SITE or p["site_type_code"] != "ST":
        raise ValueError("Expected the configured stream station")
    lon, lat = station["geometry"]["coordinates"]
    if not all(type(v) in (int, float) and math.isfinite(v) for v in [lon, lat]) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("Invalid station coordinates")
    series = docs["series.json"]["features"]
    valid_series = {s["id"] for s in series if s["properties"].get("monitoring_location_id") == SITE
                    and s["properties"].get("parameter_code") == "00060"
                    and s["properties"].get("statistic_id") == "00003"
                    and s["properties"].get("unit_of_measure") == "ft^3/s"
                    and s["properties"].get("computation_period_identifier") == "Daily"}
    daily = docs["daily.json"]
    if any(link.get("rel") == "next" for link in daily.get("links", [])):
        raise ValueError("Paginated response: choose a smaller date window")
    records = []
    seen = set()
    for feature in daily["features"]:
        v = feature["properties"]
        if (v["monitoring_location_id"] != SITE or v["parameter_code"] != "00060"
                or v["statistic_id"] != "00003" or v["unit_of_measure"] != "ft^3/s"
                or v["time_series_id"] not in valid_series):
            raise ValueError("Unexpected station, variable, statistic, unit or series")
        day = date.fromisoformat(v["time"]).isoformat()
        if not manifest["requested_start"] <= day <= manifest["requested_end"] or day in seen:
            raise ValueError("Duplicate or out-of-window daily date")
        seen.add(day)
        raw = v["value"]
        value = None if raw is None else float(raw)
        if type(raw) is bool or (value is not None and (not math.isfinite(value) or value < 0)):
            raise ValueError("Invalid discharge; missing values must be null, never zero-filled")
        records.append({"provider_id": feature["id"], "measurement_date": day, "value": value,
                        "source_type": "real", "record_type": "sensor", "raw_value": raw, "unit": "ft^3/s", "parameter_code": "00060",
                        "statistic_id": "00003", "approval_status": v.get("approval_status"),
                        "qualifier": v.get("qualifier"), "provider_last_modified": v.get("last_modified"),
                        "time_series_id": v["time_series_id"]})
    if not records or not any(r["value"] is not None for r in records):
        raise ValueError("No usable discharge data in the response")
    records.sort(key=lambda r: r["measurement_date"])
    retrieved = max(utc(f["retrieved_at"]) for f in manifest["files"].values())
    return {"dataset_id": "usgs-daily-" + digest(manifest),
            "stream_id": SITE, "station_name": p["monitoring_location_name"], "lat": lat, "lon": lon,
            "station_time_zone": p.get("time_zone_abbreviation"),
            "measurement_time_semantics": "Provider calendar date for daily mean; no UTC instant or exact daily interval inferred.",
            "mode": "retrospective_archive", "variable": "Daily mean discharge", "unit": "ft^3/s",
            "synthetic": False, "retrieved_at": retrieved, "original_publication_time": None,
            "records": records, "provenance": manifest,
            "limitations": "Archived flow context only. Not rainfall, contamination truth, a live warning, or evidence that synthetic citizen reports occurred."}


def load_bundle(folder=FIXTURE):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    docs = {}
    if set(manifest["files"]) != {"daily.json", "series.json", "station.json"}:
        raise ValueError("Unexpected fixture files")
    for name, meta in manifest["files"].items():
        raw = (folder / name).read_bytes()
        if len(raw) != meta["bytes"] or sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(f"Checksum/size mismatch: {name}")
        for key in ("requested_url", "resolved_url"):
            parsed = urlparse(meta[key])
            if parsed.scheme != "https" or parsed.netloc != "api.waterdata.usgs.gov":
                raise ValueError("Unexpected source URL")
        utc(meta["retrieved_at"])
        docs[name] = json.loads(raw)
    return normalize(docs, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", type=Path, help="Download to a NEW directory; omit for offline verification")
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--start", default="2024-02-01")
    parser.add_argument("--end", default="2024-02-08")
    args = parser.parse_args()
    bundle = fetch_bundle(args.fetch, args.start, args.end) if args.fetch else load_bundle(args.fixture)
    print(json.dumps({"station": bundle["station_name"], "records": len(bundle["records"]),
                      "dates": [r["measurement_date"] for r in bundle["records"]],
                      "values": [r["value"] for r in bundle["records"]], "unit": bundle["unit"],
                      "mode": bundle["mode"], "retrieved_at": bundle["retrieved_at"]}, indent=2))


if __name__ == "__main__":
    main()
