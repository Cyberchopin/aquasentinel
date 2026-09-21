# Approved delivery contract

Feature freeze: September 27, 2026. Target submission: September 30 noon PDT.

The September 15 runnable prototype is preserved at `pre-hackathon-baseline`
(commit `0e74240817edc6f7bc9ed99e039a2102f297595d`). The tag was created later.
It is a bookkeeping name, not a determination of eligibility: organizer updates
say September 14 while Rules say September 16. Clarification email sent September
20; response pending. No history will be rewritten.

## Invariants

- Forecast captures append only with fetched_at and separate provider issue time
  when actually supplied. Fetch time is not publication time. Replay uses only
  versions already fetched AND imported by the replay instant.
- Archive/reanalysis evaluation is labelled **not as-issued forecast skill**.
- USGS discharge peaks are a **proxy for rain-driven runoff events**, not water
  quality truth or validation of the unusual-citizen-report rule.
- Every visible record shows real/synthetic provenance and its type (sensor,
  citizen report, or forecast). Sensor turbidity never votes as a citizen report.
- Arroyo Seco validates the pipeline; it is not an official OneAquaHealth pilot.
- The product narrative is ecosystem, animal and community health, with traceable
  evidence and human follow-up. Career positioning is not submission copy.

## Order and checks

1. Finish real USGS adapter, station config, record badges and regression tests.
2. Prepare and deploy minimal read-only replay on a user-approved free host;
   redeploy each completed P0. Account access remains required.
3. Append-only weather capture, forecast Watch/retraction outbox and proxy backtest.
4. One Health briefs and validated environmental FHIR export.
5. Map/intake, session sandbox, submission evidence and demo recording script.

Each P0 receives full unittest + benchmark results and a two-minute acceptance
path. No unattended future work is implied by these dates.

Citizen App: registration/export exploration started September 20. If no lawful
real export is available by September 23, drop the importer and retain the clearly
labelled custom demo schema. No invented official export schema.

Cut order if behind: map/intake polish, accessibility pass, hash chain. Do not cut
real data, Watch/retraction, One Health brief, FHIR, or deployment. Flag any cut.
