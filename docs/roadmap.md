# Research and engineering plan

## The question

When observations are late, duplicated, missing or contradictory, how does a stream triage system's review workload and missed-event rate change? Under what conditions should it request more evidence?

This is a candidate empirical question, not a novelty or publication claim. The current implementation establishes data/replay invariants, not an ML finding.

## Milestones

### M0 — complete locally on September 15

Validated ingestion, persistence, deterministic replay, snapshot-bound reviews, browser demo, contract tests, microbenchmark. All development scenarios synthetic.

### M1 — real data and geographic matching

- Select one freshwater reach with overlapping weather and environmental observations. Record station coordinates, variable definitions, units, valid intervals, coverage, attribution and usage terms.
- Preserve downloaded raw payloads, retrieval times, provider update times and checksums. A historical download's retrieval time must not be represented as the original live publication time.
- Separate true historical availability from retrospective counterfactual simulation. Without original publication times, explicitly call the replay retrospective, not leakage-free live replay.
- Start with a working real connector, explicit offline fixtures and schema validation. No private UCLA/MIT/GT research data is needed.
- Move the repository layer to PostgreSQL/PostGIS and test reach assignment, distance, adjacency, migrations, pagination and query plans. Point proximity alone is insufficient for river connectivity.

Candidate check: USGS-11048550 (San Diego Creek at Lane Road near Irvine) is a real site, but its current page shows no available continuous/daily/field data. Do not choose it just for geographic familiarity. [Station page](https://waterdata.usgs.gov/monitoring-location/USGS-11048550/).

USGS offers [modern OGC data APIs](https://api.waterdata.usgs.gov/docs/ogcapi), including time-series metadata and daily data. This is a researched candidate source, not an integrated adapter. A daily discharge value cannot stand in for a six-hour rainfall accumulation or ground-truth contamination label.

### M2 — independent evaluation

- Define one label before choosing a model: for example expert-rated need for a follow-up investigation. Physical contamination labels require appropriate measurements; report wording is not ground truth.
- Compare fixed rules, a robust temporal baseline (e.g. historical median/MAD) and a multi-source method. Tune only on training/validation data.
- Split by time and, if enough sites exist, hold out sites; keep observations from the same event in one split. Avoid random row splits.
- Run ablations: no weather context, no source deduplication, no freshness filter, no abstention. Measure false reviews per site-day, missed labeled events, review coverage, delay and workload.
- Report uncertainty intervals and failed cases. Only report calibration error if the model actually emits probabilistic predictions and enough independently labeled data exists.
- Treat synthetic corruption experiments separately from real-world effectiveness. A high synthetic test pass rate is not precision/recall on environmental incidents.

### M3 — operational evidence

Bound queues and implement retry/dead-letter behavior only when an asynchronous adapter exists. Test restart recovery, duplicates after retry and malformed upstream payloads. Measure end-to-end p50/p95 at a documented load, resource use and cloud cost. A single-process SQLite run is not distributed AI infrastructure.

### Optional robotics bridge after the hackathon

Study where an observer should collect the next measurement to reduce uncertainty under a time budget. Start with an explicit simulated sampling policy and baseline comparison. Real robot navigation, ROS2, control, collision avoidance and sensor calibration belong in AegisLand/TASL work until this project has a justified need.

## Portfolio completion gate

Promote AquaSentinel into the main resume only after M1 and one defensible M2 experiment, with reproducible commands, raw evidence, a clear individual contribution and at least one external usability/domain review. The current milestone can be described as work in progress.
