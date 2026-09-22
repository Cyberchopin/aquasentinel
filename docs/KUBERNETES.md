# Self-managed Kubernetes handoff

The provided manifests run a single read-only replay replica. No cluster action,
image publication or cloud deployment was performed by the agent.

## Push the existing repository

Use the existing local checkout (it contains the original history and baseline tag):

```powershell
cd C:\Users\wangs\Documents\Codex\2026-09-15\iee-devpost-project\outputs\aquasentinel
git push --atomic origin main refs/tags/pre-hackathon-baseline
```

If your machine has a working GitHub CLI login but a broken Git credential helper:

```powershell
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push --atomic origin main refs/tags/pre-hackathon-baseline
```

Do not force-push if remote history has changed. Fetch and inspect first.
The separate `.bundle` handoff preserves all commits and the baseline tag; a ZIP
contains source only. To transfer to another machine:

```sh
git clone aquasentinel-history.bundle aquasentinel
cd aquasentinel
git remote set-url origin https://github.com/Cyberchopin/aquasentinel.git
git push --atomic origin main refs/tags/pre-hackathon-baseline
```

## Build and publish your image

Replace the registry name in these commands and `k8s/kustomization.yaml` if needed.
Log in to your chosen registry with your own credentials.

```sh
docker build -t ghcr.io/cyberchopin/aquasentinel:v0.2 .
docker push ghcr.io/cyberchopin/aquasentinel:v0.2
kubectl apply --dry-run=server -k k8s
kubectl apply -k k8s
kubectl -n aquasentinel rollout status deployment/aquasentinel
kubectl -n aquasentinel port-forward service/aquasentinel 8765:80
```

Open http://127.0.0.1:8765. `/api/health` should report `read-only-replay`.
The GHCR name is an example target, not an already published image. A private image
requires your namespace's imagePullSecret. Match build architecture to cluster nodes.
For public access, route your own Ingress/Gateway and TLS hostname to Service
`aquasentinel`, port 80. No domain, ingress class or TLS secret has been guessed.

## Data and operation

- The image contains captured public data and synthetic demonstrations. It does
  not fetch new forecasts at startup. Old forecast captures expire honestly.
- SQLite uses an emptyDir. Restart recreates demo state and import timestamps;
  this is intentional for a disposable read-only demonstration, not durable storage.
- The single-process Python HTTP service is a bounded prototype. Start with one
  replica. Avoid interpreting local benchmark timings as production throughput.
- For interactive isolated sessions replace container args with:
  `["--host", "0.0.0.0", "--public-demo", "--public-origin", "https://YOUR-DOMAIN", "--demo", "--usgs-fixture", "--weather-dir", "data/weather"]`
  and set command to `["python", "-m", "aquasentinel.server"]`.
  Retain one replica; session databases are in memory and reset on restart.
  Your ingress must preserve the original Host header. Use read-only mode first.

Validation: application tests passed in the development environment. Docker build,
Kubernetes API validation and cluster rollout must be run in your environment;
those tools/cluster are not available here.
