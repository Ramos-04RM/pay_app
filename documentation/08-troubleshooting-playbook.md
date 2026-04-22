# Troubleshooting Playbook

## Incident First Response
1. Confirm symptom and scope
2. Capture logs before restart
3. Verify container status
4. Validate DB connectivity and migration state
5. Run focused smoke checks

## Basic Diagnostic Commands

```powershell
docker compose ps
docker compose logs web --tail=200
docker compose logs db --tail=200
docker compose logs nginx --tail=200
curl http://localhost:8080/healthz/
Get-Content .\logs\app.jsonl -Tail 50
Get-Content .\logs\security.jsonl -Tail 50
```

## Structured Audit Log Notes
- Log file path: `logs/app.jsonl`
- Security log path: `logs/security.jsonl`
- Format: one JSON object per line (JSONL)
- Rotation/retention: daily, keep last 90 files
- Core keys for dashboards/alerts: `time`, `level`, `event`, `username`, `request_id`, `path`
- Prefer Grafana/Loki queries by `event` + `level` and then drill into `context`

## Common Symptoms

### Health check fails
- Check if `web` container is up
- Check Gunicorn startup errors from `entrypoint.sh`
- Verify DB readiness and env vars (`POSTGRES_HOST`, `POSTGRES_PORT`)

### Login or CSRF issues
- Verify `DJANGO_CSRF_TRUSTED_ORIGINS`
- Verify `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` align with HTTP/HTTPS

### Decryption failures
- Verify `APP_ENCRYPTION_KEY` exists in runtime env
- Confirm request user is authenticated and session is still valid
- Check `logs/security.jsonl` for `secret.decrypt.failed` events and failure context

### Cabinet delete fails
Expected when linked pay records exist due to `Pay.cabinet` `DO_NOTHING` policy.
- Reassign or delete dependent services first

### Daily payment mismatch
- Confirm cabinet has `is_daily_payment=True`
- Confirm active services have valid positive monthly prices
- Recheck daily divisor assumptions (`DAILY_DIVISOR=28`)

## Safe Recovery Checklist
- [ ] Logs captured before restart
- [ ] No secrets printed or copied
- [ ] Root cause documented
- [ ] Smoke checks pass after fix
- [ ] Added/updated tests for regression prevention

