# Environmental FHIR R4 mapping

Target: base FHIR 4.0.1 collection Bundle, not a clinical message or a claim of
conformance to the OneAquaHealth implementation guide.

| Source | Resource / field | Meaning |
|---|---|---|
| Stream | Location | Environmental subject; no patient invented |
| Citizen assertion | Observation, preliminary, valueString | Subjective report, explicitly synthetic or unverified real |
| Rainfall context | Observation.valueQuantity in UCUM mm | Six-hour accumulation, not turbidity |
| USGS daily flow | Observation.valueQuantity, UCUM `[ft_i]3/s` | Sensor-derived daily aggregate, not water-quality event |
| USGS date | effectiveDateTime, date precision only | No fabricated UTC instant |
| Receipt | Observation.note | Availability to application; not provider issued time |
| Review | Basic artifact + Provenance | Original review snapshot hash; stale reviews never target current observations |
| Current follow-up | Task, requested, intent proposal | Environmental follow-up, not a clinical order |

Bundle identifier is the snapshot hash. Stable UUID references resolve within the
collection. Plain-language codes are used instead of invented LOINC codes. No
claim of clinical validation, terminology validation, or HL7 certification.
Forecasts remain in evidence JSON; they are not disguised as measured FHIR observations.

Validation uses optional `fhir.resources==6.5.0` (R4) and `pydantic<2`; core exports
work without either. Install `requirements-extras.txt` in a separate environment.
Structural validation does not establish environmental semantic interoperability
or enforce a project-specific implementation guide. See `validation.md` for results.

References checked September 21, 2026:
- https://hl7.org/fhir/R4/observation.html
- https://hl7.org/fhir/R4/provenance.html
- https://hl7.org/fhir/R4/task.html
