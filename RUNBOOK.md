# LegaFetch operations runbook

## Scope

The production stack runs on the Netcup VPS under `/opt/legafetch`. Caddy
terminates public HTTP(S), the Node.js gateway handles the public API boundary,
and the Python service performs retrieval and LLM work.

## Deploy

Preferred path: merge to `main` and enable the guarded GitHub Actions deploy
job with `NETCUP_DEPLOY_ENABLED=true`. The workflow runs gateway build/tests,
syncs the release, rebuilds the API and gateway, then checks both `/health` and
`/ready` plus the public smoke test.

Manual path:

```bash
./deploy.sh --eval
```

The default deployment rebuilds only the Node.js gateway. When Python API code
or dependencies change, use `DEPLOY_SERVICES="api gateway" ./deploy.sh --eval`.

## Diagnose

```bash
ssh netcup 'cd /opt/legafetch && docker compose ps'
ssh netcup 'docker logs --tail=200 legafetch-gateway'
ssh netcup 'docker logs --tail=200 legafetch-api'
curl -fsS https://api.legafetch.com/health
curl -fsS https://api.legafetch.com/ready
```

`/health` proves the gateway process responds. `/ready` proves the gateway can
reach the Python dependency. A 502 from the gateway indicates an upstream
availability or timeout problem; it is not a successful AI response.

## Rollback

`deploy.sh` tags the current `legafetch-api:latest` and
`legafetch-gateway:latest` images as `:rollback` before building. If readiness
does not recover within five minutes, it restores those tags and restarts the
affected compose services. Confirm the rollback with:

```bash
ssh netcup 'cd /opt/legafetch && docker compose ps'
./scripts/smoke-production.sh https://api.legafetch.com
node scripts/latency-smoke.mjs https://api.legafetch.com 20 5
```

## Incident safety

Never paste `.env`, API keys, session cookies, customer documents, or full
production logs into issues or chat. If Qdrant is unhealthy, do not delete its
storage volume; inspect logs and snapshots first.

## Backup and restore evidence

The repository's operational measurement log records a checksum-verified
Qdrant snapshot and an isolated restore test that reached a green collection
with `9,876,424` points. See `OLCUM.md` for the dated evidence and the read/write
mount requirement. A future restore drill must use a disposable Qdrant
container and must never mount the production storage as a write target.

The scheduled GitHub Actions uptime check is an external liveness signal. A
failed workflow is evidence to investigate, not proof that alert delivery is
instant or complete.

The latest live gateway deployment and public smoke evidence is recorded in
`LIVE-VERIFICATION.md`. The readiness latency recorded there is dependency-chain
latency, not a full authenticated AI query benchmark.
