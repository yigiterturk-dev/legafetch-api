# Observability coverage

This map answers operator questions without logging legal queries, document
contents, API keys, cookies, or model prompts.

| Journey / failure | Detection signal | Diagnosis signal | Response path | Evidence |
|---|---|---|---|---|
| Gateway is alive | `/health` | structured Fastify request logs | restart/redeploy gateway | gateway health route, compose healthcheck |
| AI dependency is unavailable | `/ready` returns `503` | gateway warning with request path and error metadata | inspect API/Qdrant, use rollback if deploy-related | readiness route, `RUNBOOK.md` |
| Caller lacks credentials | `401` response | request ID and status code; no credential value logged | fix caller/configuration | auth regression test |
| AI request times out/fails | `502` + `Retry-After` | gateway error with request ID/path | retry bounded request, inspect upstream | failure regression test |
| Deployment breaks service | health gate fails | compose status and tail logs | restore `:rollback` images | `deploy.sh`, `RUNBOOK.md` |
| Public service is down | scheduled smoke workflow fails | health/readiness/auth smoke output | inspect VPS and Caddy | `.github/workflows/uptime.yml` |
| Qdrant data is damaged | API readiness/search symptoms | Qdrant logs and snapshot inventory | isolated restore drill | `OLCUM.md`, `RUNBOOK.md` |

## Privacy and cardinality controls

- The gateway forwards a request ID but does not log request bodies, API keys,
  cookies, legal queries, uploaded files, or model prompts.
- Paths are logged for diagnosis; do not add user IDs, query strings, or raw
  document identifiers without a retention and cardinality review.
- Public smoke tests use synthetic requests only.

## Runtime unknowns

Repository evidence cannot prove alert delivery, dashboard freshness, log
retention, or time-to-acknowledge. The scheduled workflow is an external signal
but is not a substitute for an on-call paging system.

## Smallest next instrumentation step

If traffic volume grows, add a metrics backend with bounded labels for request
status, route family, and upstream outcome. Never use raw URL, query, customer,
or document identifiers as metric labels.
