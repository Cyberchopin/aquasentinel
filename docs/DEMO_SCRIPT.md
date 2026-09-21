# 4:30 demonstration shot list

Preparation: run `python scripts/demo_reset.py`, then the printed server command.
Use the local writable demo for the recording; public read-only mode disables writes.
The seeded scenario starts at the hour four hours before reset. Let T be that UTC
hour. Replay slider minutes are relative to the browser's current six-hour window;
use the displayed UTC clock to find the specified times rather than assuming a fixed
slider value. Do not claim the synthetic scene happened in Arroyo Seco.

| Video time | Exact UI path / replay time | Narration |
|---|---|---|
| 0:00–0:25 | Open home, keep USGS-11098000 | Who needs trustworthy environmental evidence and why |
| 0:25–0:55 | Environmental background → Source and provenance | Eight real sensor aggregates, dates, units; separate from citizen reports |
| 0:55–1:20 | Scroll to map and Rainfall Watch | Real geometry; forecast capture time is not provider publication time |
| 1:20–1:50 | Stream → demo-creek-a; slider clock to T+00:05 | Synthetic wet forecast; dry-run Watch was recorded against a snapshot |
| 1:50–2:20 | Slider to T+01:06 | Two declared citizens plus synthetic rain recommend review; escalation recorded |
| 2:20–2:45 | Slider to T+02:45, then T+03:05 | Late normal report changes evidence; newer dry forecast removes Watch; old alerts retracted |
| 2:45–3:15 | Return to present → Reason → enter “Check conflicting reports” → Save review | Human review binds to exact evidence |
| 3:15–3:40 | Latitude 33.68; Longitude -117.82 → Add synthetic report | Before/after feedback; saved review becomes stale |
| 3:40–4:05 | One Health brief; browser Print preview | Three audiences; facts, uncertainty, follow-up, no diagnosis |
| 4:05–4:30 | FHIR export; show mapping and BACKTEST docs | Location subject, review provenance, real proxy limits; closing question: does this decision still apply? |

Recording is not yet produced. Replace deployment placeholders and verify the exact
path once more in the final frozen build before recording.
