# Minimal read-only replay

Prepared for Render free web service. Not yet deployed: account access required.
No paid plan, payment information or persistent disk is authorized.

1. Sign in at https://dashboard.render.com/ and create a Blueprint from this public
   repository's `render.yaml`. Check that the service plan is Free before applying.
2. Alternatively create a Docker web service with the public repository URL,
   Free plan, and health check `/api/health`.
3. Open the resulting URL. Confirm health mode is `read-only-replay`, open the
   station archive, move the slider, and confirm writes receive HTTP 403.
4. After each P0 push, verify the new deployment and repeat these checks.

Local equivalent: `python -m aquasentinel.server --read-only --demo --usgs-fixture --weather-dir data/weather`.
Container equivalent: `docker build -t aquasentinel .` then
`docker run --rm -p 8765:8765 aquasentinel`.

Render free services sleep when idle and use ephemeral files; startup restores
the committed fixtures. Their original receipt times are retained, but app import
times restart honestly. This is an offline captured replay, not live monitoring.
The initial public version rejects all writes; session sandbox writes are still
pending. Do not expose the local writable mode. Container execution has not yet
been verified in this workspace.

Reference: https://render.com/docs/free (checked September 21, 2026).
