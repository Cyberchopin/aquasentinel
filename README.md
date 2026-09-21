# AquaSentinel

**What did we know when a freshwater concern was raised — and does that decision still apply?**

AquaSentinel helps water ecologists, public-health officers and parks staff review
freshwater evidence, replay late reports, and see when an old warning or human
review no longer fits the evidence. It connects environmental monitoring to
transparent One Health follow-up.

## Run in two minutes

Python 3.11+; the application core has no third-party Python dependencies.

```sh
python -m aquasentinel.server --demo --usgs-fixture --weather-dir data/weather
```

Open http://127.0.0.1:8765. Choose `USGS-11098000` for real sensor background or
`demo-creek-a` for the synthetic Watch, escalation and retraction story. Move the
replay slider; then return to present, save a review, add a synthetic report, and
see the review become stale. Buttons export evidence, a printable One Health brief,
and an environmental FHIR R4 collection.

Fresh session without deleting existing data: `python scripts/demo_reset.py`.
Follow the server command it prints. Full recording path: [4:30 script](docs/DEMO_SCRIPT.md).

## What is implemented

- Real USGS daily discharge with raw response checksums, units and date semantics.
- Append-only Open-Meteo forecast captures with `fetched_at`, separate unknown
  provider issue time, and import time. Replay never uses a later capture.
- Illustrative future-rainfall Watch; snapshot-bound, deduplicated dry-run alerts
  escalate to review and show retraction when the evidence changes.
- Late citizen reports and immutable-by-application ingestion, deterministic triage,
  and review history bound to exact evidence snapshots.
- REAL / SYNTHETIC and SENSOR / CITIZEN labels, separated evidence panels.
- Pinned Leaflet 1.9.4, real USGS river geometry, distinct synthetic demo reaches,
  spherical distance matching, coordinate/map intake, and before/after feedback.
- Non-diagnostic briefs for three One Health audiences and FHIR R4 exports.
- Read-only hosting mode and isolated, bounded public-demo sessions.

## Real data and reproducibility

Arroyo Seco near Pasadena is used **only to validate the pipeline**, not presented
as a OneAquaHealth pilot. [Station configuration](config/station.json) controls the
station, city, coordinates, river geometry file and Watch threshold. Switching to
another supported USGS stream requires editing this configuration and capturing
its data/geometry; it does not require changing application code.

Real archive: February 1–8, 2024, discharge in ft³/s. The captured Open-Meteo
forecast and historical reanalysis are separate files. Current dry weather may
produce no Watch; use the labelled synthetic scenario to demonstrate retraction.

```sh
python -m aquasentinel.usgs
python -m aquasentinel.weather --capture data/weather
python -m unittest discover -s tests -v
python scripts/benchmark.py
python scripts/backtest.py
python scripts/http_e2e.py
python -m aquasentinel.audit runtime/aquasentinel.sqlite3
```

The application runs offline from committed captures. Explicit weather fetching
requires network access and appends a new file; an old offline forecast expires
and is never silently relabelled as current. Map tiles need network access, while
river geometry is local. [USGS attribution](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits);
[Open-Meteo](https://open-meteo.com/) data CC BY 4.0; map tiles © OpenStreetMap contributors.

## Hosting and evidence

[Deployment instructions](docs/DEPLOYMENT.md) include Docker and Render Free.
**Public deployment is pending account access; no public demo URL is claimed.**
Screenshots/video will be captured from the frozen build, rather than using mockups.

- [Architecture](docs/ARCHITECTURE.md)
- [Validation](docs/validation.md) and [benchmark](docs/benchmark.json)
- [Illustrative backtest and real proxy limits](docs/BACKTEST.md)
- [FHIR mapping](docs/fhir-mapping.md)
- [Judging evidence](docs/JUDGING_MAP.md) and [submission description](docs/DEVPOST_DESCRIPTION.md)

## Baseline and eligibility

The September 15 runnable prototype is at `pre-hackathon-baseline`, commit
`0e74240817edc6f7bc9ed99e039a2102f297595d`. The tag was created on September 20;
no commit was rewritten or backdated. That baseline already included ingestion,
replay, rule triage, review binding, a local UI and tests. Real adapters, forecasts,
alerts, geographic intake, One Health briefs and FHIR were added afterwards.

[Organizer updates](https://oneaquahealth-ieee-hackathon.devpost.com/updates) state
September 14–30; [Rules](https://oneaquahealth-ieee-hackathon.devpost.com/rules) state
September 16–30. Written clarification on registration, dates and solo eligibility
was requested September 20; no eligibility determination is claimed.

## Limitations

Thresholds are illustrative, with no validated field forecast skill. Real discharge
peaks are a runoff **proxy**, not water-quality truth or validation of unusual
citizen reports. Reanalysis is **not as-issued forecast skill**. Synthetic results
are separated from real-data findings. No diagnosis, disease prediction, polluter
identification or measured health benefit is claimed.

Source identities and reviewers are unauthenticated. Snapshot hashes identify
content consistency. A local hash-chained insert log detects inconsistency under its verify command; pre-existing rows are reported as unlogged legacy data. This is not proof against a database owner who can rewrite data.
Alerts are dry-run, not external notifications. FHIR validation is base-R4
structural checking, not certification or OAH implementation-guide conformance.
The Citizen App export is pending registration; if unavailable September 23, the
custom clearly labelled demo format remains. No guessed official schema is used.

This is a single-process demonstration with limited concurrency, not a production
monitoring service. No trained ML model, photo attachments or multi-city product.
