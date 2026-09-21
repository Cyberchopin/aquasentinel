"""Transparent baseline. Priority is not a probability or water-quality diagnosis."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math

RULE_VERSION = "triage-v0.2"
SIGNALS = {"turbidity", "odor", "normal", "rainfall"}


def utc(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO-8601 string with timezone")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp requires a timezone")
    return result.astimezone(timezone.utc).isoformat(timespec="microseconds")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate(payload, received_at):
    if not isinstance(payload, dict):
        raise ValueError("Observation must be an object")
    required = {"source_id", "external_id", "stream_id", "observed_at", "lat", "lon", "signal", "synthetic"}
    allowed = required | {"value", "unit", "period_hours", "note"}
    if required - payload.keys() or payload.keys() - allowed:
        raise ValueError("Missing or unknown observation fields")
    record = dict(payload)
    for key in ("source_id", "external_id", "stream_id"):
        if not isinstance(record[key], str) or not record[key].strip() or len(record[key]) > 100:
            raise ValueError(f"Invalid {key}")
        record[key] = record[key].strip()
    if record["signal"] not in SIGNALS:
        raise ValueError("Unsupported signal")
    if type(record["synthetic"]) is not bool:
        raise ValueError("synthetic must be a boolean")
    for key, bound in (("lat", 90), ("lon", 180)):
        value = record[key]
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > bound:
            raise ValueError(f"Invalid {key}")
    record["observed_at"] = utc(record["observed_at"])
    record["received_at"] = utc(received_at)
    if record["observed_at"] > record["received_at"]:
        raise ValueError("Observation cannot be in the future")
    if record["signal"] == "rainfall":
        value = record.get("value")
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1000 or record.get("unit") != "mm":
            raise ValueError("Rainfall must have a finite value in mm (0–1000)")
        if type(record.get("period_hours")) not in (int, float) or record["period_hours"] != 6:
            raise ValueError("This baseline requires a 6-hour accumulated rainfall observation")
    elif any(k in record for k in ("value", "unit", "period_hours")):
        raise ValueError("Numeric measurements are only supported for rainfall")
    if not isinstance(record.get("note", ""), str) or len(record.get("note", "")) > 1500:
        raise ValueError("Note must be text, at most 1500 characters")
    record.setdefault("note", "")
    record['source_type'] = 'synthetic' if record['synthetic'] else 'real'
    record['record_type'] = 'rainfall_context' if record['signal'] == 'rainfall' else 'citizen_report'
    record["id"] = digest([record["source_id"], record["external_id"]])[:24]
    return record


def assess(records, stream_id, as_of):
    as_of = utc(as_of)
    cutoff = (datetime.fromisoformat(as_of) - timedelta(hours=24)).isoformat(timespec="microseconds")
    rain_cutoff = (datetime.fromisoformat(as_of) - timedelta(hours=6)).isoformat(timespec="microseconds")
    evidence = sorted((r for r in records if r["stream_id"] == stream_id
                       and cutoff <= r["observed_at"] <= as_of and r["received_at"] <= as_of),
                      key=lambda r: (r["received_at"], r["id"]))
    evidence = [dict(r, source_type='synthetic' if r['synthetic'] else 'real',
        record_type='rainfall_context' if r['signal'] == 'rainfall' else 'citizen_report') for r in evidence]
    # Multiple reports from one declared source never count as corroboration.
    unusual = [r for r in evidence if r["signal"] in {"turbidity", "odor"}]
    normal = [r for r in evidence if r["signal"] == "normal"]
    fresh_rain = [r for r in evidence if r["signal"] == "rainfall" and r["observed_at"] >= rain_cutoff]
    latest_rain = max(fresh_rain, key=lambda r: (r["observed_at"], r["received_at"], r["id"]), default=None)
    wet = latest_rain is not None and latest_rain["value"] >= 5
    sources = sorted({r["source_id"] for r in unusual})
    state = "monitor"
    reasons = []
    if unusual:
        state = "needs_corroboration"
        reasons.append(f"{len(sources)} distinct declared source(s) report a change")
        if len(sources) >= 2 and wet and not normal:
            state = "review_recommended"
    else:
        reasons.append("No unusual citizen observation in the current 24-hour window")
    if latest_rain is None:
        reasons.append("Rainfall context missing or older than 6 hours")
    else:
        reasons.append(f"Latest 6-hour rainfall: {latest_rain['value']} mm; demo trigger is 5 mm")
    if normal and unusual:
        reasons.append("Conflicting normal observations require corroboration")
    reasons.append("Source identities and stream assignments are unverified in this local prototype")
    decision = {"rule_version": RULE_VERSION, "stream_id": stream_id, "state": state,
                "evidence": evidence, "reasons": reasons, "distinct_sources": len(sources),
                "support_ids": [r["id"] for r in unusual], "conflict_ids": [r["id"] for r in normal] if unusual else [],
                "rain_id": latest_rain["id"] if latest_rain else None,
                "synthetic_count": sum(r["synthetic"] for r in evidence)}
    decision["decision_hash"] = digest(decision)
    decision["as_of"] = as_of
    return decision
