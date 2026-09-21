# AquaSentinel — decisions that stay connected to their evidence

Urban freshwater reports can arrive late, conflict, or refer to a different
reach. Water ecologists, public-health officers and parks staff need to understand
what was known when a concern was raised, and whether a later finding changes it.

AquaSentinel is decision provenance for citizen-science early warning: it answers
not just what the evidence says now, but what we knew at 14:05, who decided what,
and whether that decision still applies.

The prototype combines clearly labelled citizen demonstrations, real USGS daily
discharge, USGS river geometry and captured Open-Meteo forecasts. Its replay uses
only data received by the selected time. Forecast versions are retained rather
than overwritten. An illustrative rainfall Watch and a dry-run alert outbox bind
warnings to evidence; later changes retract their current applicability. Human
reviews remain in history and become stale when their snapshot changes.

Printable One Health briefs route the same evidence to ecological, public-health
and animal-health/parks audiences without making diagnoses. Environmental FHIR R4
collections make observations and review provenance inspectable by other systems.

Primary track: Track 6, Resilience Informatics. Supporting themes: Track 3 human
review and explainability; Track 7 interoperability. The intended impact is more
transparent coordination around ecosystem, animal and community wellbeing.

Arroyo Seco is a pipeline-validation location, not a OneAquaHealth pilot. Citizen
reports in the demo are synthetic. USGS discharge peaks are a runoff PROXY, not
water-quality events. Archive/reanalysis does not establish as-issued forecast
skill. The thresholds are illustrative; no field efficacy, health benefit,
polluter identification or disease prediction is claimed. Reviewers are demo
operators, not authenticated experts. Alerts are never actually sent.

Before submission: replace the pending demo URL with a verified public deployment,
attach the recorded 3–5 minute video, and record the organizer's eligibility reply.
The September 15 runnable baseline is preserved without rewriting Git history.
