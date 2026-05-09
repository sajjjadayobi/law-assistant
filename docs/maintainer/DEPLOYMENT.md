# Deployment Guide — Law Agent

Complete production deployment guide using Docker Compose. Tested on 2026-05-09.

---

## Prerequisites

- Docker 20.10+ (tested with 29.1.3)
- Docker Compose 2.0+ (`docker compose version`)
- 4GB RAM minimum, 8GB recommended
- 30GB disk (Docker images ~3GB, data volumes grow over time)

---

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url> law-agent && cd law-agent

# 2. Create .env from template
cp .env.example .env
nano .env   # fill in: LLM_AUTH_TOKEN, LLM_BASE_URL, CHAINLIT_AUTH_SECRET

# 3. Build and start all services
docker compose build
docker compose up -d

# 4. Wait ~30s for health checks to pass, then verify
docker compose ps
curl http://localhost:8000/health
```

---

## Environment Variables

All secrets go in `.env`. Never commit this file.

```bash
# Required
LLM_AUTH_TOKEN=sk-...          # LiteLLM / Anthropic API key
LLM_BASE_URL=https://...       # LiteLLM proxy URL (leave blank for direct Anthropic)
CHAINLIT_AUTH_SECRET=...       # JWT secret: openssl rand -base64 32

# Optional — defaults already set in docker-compose.yml
# DB_PASSWORD=postgres_password   # Change in production!
# LOG_LEVEL=INFO
# LOGGING_FORMAT=json
```

Generate `CHAINLIT_AUTH_SECRET`:
```bash
openssl rand -base64 32
```

---

## Service Architecture

| Service | Port | Purpose |
|---------|------|---------|
| `law-agent-app` | 8000 | Chainlit UI + Law Agent |
| `law-agent-postgres` | 5432 | Documents + conversation history + Phoenix DB |
| `law-agent-phoenix` | 6006 | Arize Phoenix observability UI |
| phoenix OTLP | 4317 | OpenTelemetry trace ingestion |

**Startup order**: postgres must be healthy before phoenix or app start.

---

## Health Checks

The app exposes two endpoints:

```bash
# Overall health (database + phoenix)
curl http://localhost:8000/health
# {"status":"healthy","components":{"database":{"status":"healthy"},"phoenix":{"status":"healthy"}}}

# Readiness (database only — sufficient for traffic)
curl http://localhost:8000/ready
# {"ready":true,"status":"healthy","details":{"status":"healthy","message":"..."}}
```

Status values:
- `healthy` — all components working
- `degraded` — Phoenix down (app still serves traffic normally)
- `unhealthy` — database down (app cannot function)

---

## Database Initialization

On first start, Postgres runs these scripts in order:
1. `init-db.sql` — creates the `phoenix` PostgreSQL role
2. `init-db.sh` — creates the `phoenix` database (must be shell; `CREATE DATABASE` cannot run in a transaction block)
3. `docs/architecture/migration/schema.sql` — creates `documents`, `relations`, FTS config for `law_agent`

The init scripts only run when the data volume is empty (first deploy). They do not re-run on restart.

**To load data into the database**, you need to import the legal documents separately — the schema creates empty tables.

---

## Monitoring

**Arize Phoenix** at http://localhost:6006:
- Traces: each user question = one `user_turn` CHAIN span with tool call children
- Feedback: thumbs 👍/👎 appear as annotations on spans
- Token usage: input/output tokens tracked per span

**Logs**:
```bash
docker compose logs -f app      # Application logs
docker compose logs -f postgres # Database logs (verbose if log_statement=all)
docker compose logs -f phoenix  # Phoenix logs
```

Set `LOGGING_FORMAT=json` in `.env` for structured production logs.

---

## Common Operations

```bash
# View service status
docker compose ps

# Restart a service
docker compose restart app

# View recent logs
docker compose logs --tail=50 app

# Stop everything (keeps data volumes)
docker compose down

# Stop and delete all data (⚠️ irreversible)
docker compose down -v

# Rebuild after code changes
docker compose build app
docker compose up -d app
```

---

## Production Checklist

- [ ] Set a strong `CHAINLIT_AUTH_SECRET` (32+ random bytes)
- [ ] Set a strong `DB_PASSWORD` in both `.env` and `docker-compose.yml`
- [ ] Set `LOGGING_FORMAT=json` in `.env` for structured logs
- [ ] Put Nginx/Traefik in front of port 8000 (TLS termination)
- [ ] Block port 5432 and 4317 from public access
- [ ] Optionally block port 6006 (Phoenix UI) or add auth in front
- [ ] Set up daily database backups (see Backup section)

---

## Backup

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p /backups/law-agent

# Law Agent database (documents + conversation history)
docker compose exec -T postgres pg_dump -U postgres law_agent \
  | gzip > /backups/law-agent/law_agent_$DATE.sql.gz

# Phoenix observability database
docker compose exec -T postgres pg_dump -U postgres phoenix \
  | gzip > /backups/law-agent/phoenix_$DATE.sql.gz

# Keep 7 days
find /backups/law-agent -mtime +7 -delete
```

Schedule daily:
```bash
(crontab -l; echo "0 2 * * * /opt/law-agent/backup.sh") | crontab -
```

---

## Troubleshooting

### App won't start
```bash
docker compose logs app | head -50
docker compose ps postgres   # Must be healthy first
```

### Phoenix migration failure
If Phoenix exits with "failed to migrate" on restart, the database may be dirty from a partial migration. Fix:
```bash
docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS phoenix;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE phoenix OWNER phoenix;"
docker compose restart phoenix
```

### Database connection refused
Check `DB_HOST` is set to `postgres` (the Docker service name), not `localhost`:
```bash
docker compose exec app env | grep DB_
```

### Health check returns HTML instead of JSON
This means the Chainlit SPA catch-all is intercepting `/health`. The fix is to use
`BaseHTTPMiddleware` (not `@app.get`) for health routes — see `src/law_agent/ui/app.py`.

---

## Known Issues / Notes

- **`log_statement=all`** in the postgres command generates verbose logs. Set to `none` or `ddl` in production by editing `docker-compose.yml`.
- **`version: '3.8'`** in docker-compose.yml is obsolete; Docker Compose v2 ignores it (shows a warning). Safe to remove.
- **Phoenix image**: `arizephoenix/phoenix:latest` (not `arizehq/phoenix`).
- **Phoenix health endpoint**: `/healthz` (not `/health`) — no curl in the container; Python urllib is used.

---

**Last Updated**: 2026-05-09  
**Tested with**: Docker 29.1.3, Docker Compose 5.1.3, Colima 0.8.x (macOS arm64)
