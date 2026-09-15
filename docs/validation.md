# Validation — September 15, 2026

## Automated checks

`python -m unittest discover -s tests -v` — **21 tests passed** on bundled Python 3.12.14 / Windows 11.

Coverage includes duplicate idempotency and conflicting ID reuse, source-level corroboration, cross-stream separation at identical coordinates, missing/stale/dry rainfall, six-hour rainfall units, conflicting reports, late-arrival replay isolation, review staleness, timestamp validation, restart consistency and empty snapshots.

HTTP tests use a separate temporary database and local server: ingestion → duplicate → snapshot → review; invalid bodies/timestamps; cross-origin writes; unknown file paths.

## Browser checks

Tested the local UI through the Codex in-app browser:

- Rewound the scenario to 17:42 UTC: three visible records, Review recommended, and disabled review submission while viewing history.
- Returned to present: the late normal report appeared and changed the automatic state to Needs corroboration.
- Saved a synthetic development review: Follow-up required appeared with a preserved note.
- Added a synthetic observation: evidence count increased and the previous review was flagged as no longer current.

The browser checks use synthetic records. They are workflow checks, not environmental effectiveness evaluation. The checked UI has a responsive single-column layout in the narrow Codex panel.

## Microbenchmark

See `benchmark.json` for the exact measured run and environment. It uses 1,000 synthetic records, 10 streams, 1,000 duplicate replays and 100 snapshot queries. Restart equality is checked. Timings measure local store operations, not network/browser latency; no concurrent-load, predictive accuracy or production-scale claim.

## Remaining limitations

- No real data adapter, independently labeled dataset or trained model.
- No PostGIS/topology-based reach matching; stream IDs are supplied by callers.
- No authenticated citizen/reviewer identities; local loopback-only deployment.
- Rules and thresholds are illustrative; review priority is not pollution probability or a water-safety finding.
- Queue/recovery under process crashes, sustained/concurrent load, accessibility audit and deployment validation remain future work.
