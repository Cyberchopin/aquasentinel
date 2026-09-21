# Decision provenance for One Health

```mermaid
flowchart TD
  Citizen[Labelled citizen reports] --> Receipt[Server receipt time + validation]
  USGS[USGS daily discharge + raw provenance] --> Archive[Retrospective sensor archive]
  Weather[Open-Meteo forecast captures] --> Versions[Append-only fetched_at versions]
  Receipt --> DB[(SQLite)]
  Archive --> DB
  Versions --> DB
  DB --> Replay[As-of selection: received / fetched AND imported]
  Replay --> Triage[Illustrative citizen triage]
  Replay --> Watch[Future rainfall Watch]
  Triage --> Snapshot[Deterministic evidence snapshot hash]
  Watch --> Snapshot
  Snapshot --> Reviews[Human reviews become stale on change]
  Snapshot --> Alerts[Dry-run outbox: dedupe / escalation / retraction]
  Snapshot --> Brief[Three-audience One Health brief]
  Snapshot --> FHIR[Environmental FHIR R4 collection]
  Snapshot --> UI[Leaflet map + timeline + intake feedback]
```

The core runs on Python stdlib, SQLite and a single-process HTTP server. Forecast
provider issue time remains separate from local fetch time and may be unknown.
USGS sensor aggregates never become citizen reports. Reanalysis cannot drive Watch.

Public read-only mode rejects writes. Public interactive mode clones the shared
baseline into bounded, cookie-selected session databases; writes never reach the
shared baseline. Sessions expire after one hour, 50 concurrent sessions maximum,
120 requests per minute per session. This is a bounded demonstration, not an
authenticated operational service or a distributed production architecture.

SQLite insert triggers append a prev_hash chain for new observations, reviews, datasets, forecast captures and outbox emissions. `python -m aquasentinel.audit DATABASE` verifies hashes and recorded rows. Legacy rows are counted honestly as unlogged, not backdated. A database owner can recompute the chain; there is no external trust anchor. Alert retraction is a deterministic as-of projection against the current snapshot, not an externally delivered cancellation.
