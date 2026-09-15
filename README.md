# AquaSentinel

**A replayable data system for reviewing urban freshwater observations.**

Started September 15, 2026 for OneAquaHealth IEEE Global Hackathon, Track 6 — Resilience Informatics. This is the first local vertical slice, not a finished competition submission.

## Run

Python 3.11+; no third-party packages required for this milestone.

```sh
python -m aquasentinel.server --demo
```

Open http://127.0.0.1:8765. The server binds only to loopback. `--demo` seeds an empty database once; it never overwrites user records. The default database is `runtime/aquasentinel.sqlite3`; use `--db path/to/new.sqlite3` for a fresh scenario. Seeded timestamps are relative to first launch; to replay the full story on a later day use a new database. Stop with Ctrl+C.

```sh
python -m unittest discover -s tests -v
python scripts/benchmark.py
```

## Try the story

1. Choose `demo-creek-a`. Starter rainfall and observations are all synthetic.
2. Rewind to before the first report: Monitor.
3. Advance to the first report: Needs corroboration.
4. Advance past the second declared source: Review recommended.
5. Advance past receipt of a late conflicting report: Needs corroboration again.
6. Return to present, enter a reason and save a review.
7. Add a synthetic observation: the previous review stays in the audit history but no longer applies to the changed evidence.
8. Export the current evidence as JSON.

The second creek deliberately shares the first creek's fixture coordinates. Stream IDs prevent cross-stream corroboration; no GIS reach-matching algorithm has been implemented.

## Implemented

- Validated UTC observation contracts, coordinates, measurement units and rainfall accumulation period.
- SQLite persistence and indexed stream/receipt-time queries.
- Idempotency by `(source_id, external_id)`; conflicting reuse returns HTTP 409.
- Separate occurrence and receipt times; late observations never leak into prior as-of views.
- A deterministic 24-hour triage window with fresh six-hour accumulated rainfall context.
- Transparent rule baseline: two distinct **declared** unusual-report sources plus at least 5 mm rainfall, no conflicting normal report, recommends human review. The threshold is illustrative, not scientifically validated.
- Snapshot hashes bind reviews to exact evidence, reasons and rule version. A changed or expired context invalidates the applicability of the previous review while preserving its history.
- Local browser UI, historical playback, review, synthetic intake and evidence export.
- Automated core and HTTP tests plus a reproducible synthetic local microbenchmark.

## Architecture and boundaries

```text
Observation JSON → validation + idempotency → SQLite immutable-by-application event log
                                                   ↓
                          as-of query → deterministic triage → UI / JSON evidence
                                                   ↓
                                      snapshot-bound review history
```

The database is mutable by its owner; hashes identify snapshots and are not cryptographic proof against an attacker with database access. Declared source IDs are not authenticated identities. Reviews are made by a local demo operator, not an authenticated expert. There are no automated notifications or field actions.

The current UI uses a schematic creek, not a geographic map. There is no trained ML model, photo analysis, live weather adapter, PostGIS, queue, distributed execution, cloud deployment or actual robotic control yet. The current dependency-free core is an intentional portable baseline; FastAPI/PostGIS migration follows real data selection rather than being claimed in advance.

## API

| Route | Behavior |
|---|---|
| GET `/api/health` | Local service health |
| GET `/api/streams` | Known stream IDs |
| GET `/api/snapshot?stream=...&as_of=...` | Evidence available as of an ISO UTC timestamp (omit for present) |
| POST `/api/observations` | Validated observation, 201; duplicate 200; conflicting ID 409 |
| POST `/api/reviews` | `stream_id`, `decision_hash`, `action`, `note`; stale snapshot 409 |

Observation fields: `source_id`, `external_id`, `stream_id`, timezone-aware `observed_at`, `lat`, `lon`, `signal`, boolean `synthetic`, optional `note`. Rainfall additionally requires `value`, `unit: "mm"`, `period_hours: 6`. `received_at` is server-assigned in the public API. Signal values: `turbidity`, `odor`, `normal`, `rainfall`. Current allowed review outcomes: `dismissed`, `follow_up_required`.

## Evidence

See [validation record](docs/validation.md), [local benchmark](docs/benchmark.json), [research and implementation plan](docs/roadmap.md). Microbenchmark numbers exclude browser/network latency and are not production throughput or environmental detection accuracy.

## Competition

[Latest update](https://oneaquahealth-ieee-hackathon.devpost.com/updates) says September 14–30, deadline September 30 at 21:00 PDT. [Rules](https://oneaquahealth-ieee-hackathon.devpost.com/rules) still says September 16 and registration closes August 31. Registration status remains unconfirmed. Preserve these discrepancies and verify eligibility before submission.
