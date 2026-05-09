# Phase 8: Deployment & Production — Progress

## Session 1: 2025-04-20 (original implementation)

**Goal**: Set up Docker-based deployment for Law Agent.

**What was built:**
- Multi-stage Dockerfile (builder → runtime, non-root user)
- docker-compose.yml with postgres, phoenix, app services
- `.env.example` with all required variables documented
- Health check module planned but not fully wired

**Status at end of session**: Dockerfile and compose mostly done; health routes commented out (Chainlit API not known).

---

## Session 2: 2026-05-09 (deployment fix — made fully working)

**Goal**: Make `docker compose up -d` produce a fully healthy stack.

**Time log**:
- 11:30 Audit existing files — found 6 distinct bugs blocking deploy
- 11:45 Fix settings.py DB env vars, create health.py, add middleware
- 12:00 Colima I/O error recovery, Docker Compose plugin install
- 12:15 Build succeeds (22 steps, all layers cached on second run)
- 12:30 Fix POSTGRES_INITDB_ARGS typo, split init into .sql + .sh
- 12:45 Fix Phoenix image name (arizephoenix not arizehq), fix /healthz path
- 13:00 Fix PHOENIX_ENDPOINT env var, add middleware (not route) for health
- 13:15 All three services healthy — /health and /ready return correct JSON

---

## Bugs Fixed in Session 2

### 1. settings.py only read DB_PASSWORD from env
**Problem**: Docker Compose sets `DB_HOST=postgres`, `DB_USER=postgres`, etc. via env vars,
but `settings.py` only overrode `DB_PASSWORD`. The app connected to `localhost` (config.yaml
default) instead of the `postgres` Docker service.
**Solution**: Extended `from_yaml()` to read all five DB env vars (`DB_HOST`, `DB_USER`,
`DB_PORT`, `DB_NAME`, `DB_PASSWORD`) and `PHOENIX_ENDPOINT`.

### 2. Health endpoints implemented wrong (routes, not middleware)
**Problem**: Chainlit registers a `/{full_path:path}` catch-all at module level. Any route
added to `chainlit.server.app` after that is shadowed — `/health` returned Chainlit's SPA HTML.
**Solution**: Used `BaseHTTPMiddleware` instead of route decorators. Middleware runs before
routing and correctly intercepts `/health` and `/ready`.

### 3. `health.py` was never created
**Problem**: `progress.md` said task 8.4 was "COMPLETED" but `src/law_agent/health.py` did
not exist. The commented-out routes in `app.py` confirmed this.
**Solution**: Created `health.py` with `check_database_health()`, `check_phoenix_health()`,
`get_health_status()`, `get_readiness()`.

### 4. docker-compose.yml volume `./config` doesn't exist
**Problem**: `./config:/app/config` was mounted but there is no `config/` directory — config
is `config.yaml` at the repo root.
**Solution**: Changed to `./config.yaml:/app/config.yaml` (file mount, not directory).

### 5. Wrong Phoenix image name (`arizehq` → `arizephoenix`)
**Problem**: Image `arizehq/phoenix:latest` doesn't exist on Docker Hub.
**Solution**: Correct name is `arizephoenix/phoenix:latest`.

### 6. POSTGRES_INITDB_ARGS passed `-c` flag (runtime flag, not initdb flag)
**Problem**: `POSTGRES_INITDB_ARGS: "-c shared_preload_libraries=..."` caused `initdb` to
exit with "unrecognized option", crashing the postgres container.
**Solution**: Removed that arg; `pg_stat_statements` is not needed for this project.

### 7. `CREATE DATABASE` in SQL init file (can't run in transaction block)
**Problem**: Docker Postgres runs SQL init files inside a transaction. `CREATE DATABASE`
cannot execute inside a transaction block.
**Solution**: Split into two files: `init-db.sql` (CREATE ROLE, runs fine in transaction)
and `init-db.sh` (CREATE DATABASE via psql shell command, runs outside transaction).

### 8. Phoenix health check used `/health` instead of `/healthz`
**Problem**: Docker healthcheck for Phoenix: `curl http://localhost:6006/health` → 404.
Phoenix's actual endpoint is `/healthz`.
**Solution**: Changed Docker healthcheck to use Python urllib (no curl in Phoenix image) and
use `/healthz` path. Also updated `health.py` to use `/healthz` when probing Phoenix.

### 9. Dockerfile builder stage missing `README.md`
**Problem**: `pyproject.toml` references `README.md` as the project readme. `uv pip install .`
in the builder stage failed because `README.md` wasn't copied.
**Solution**: Added `COPY pyproject.toml README.md ./` in the builder stage.

### 10. Dockerfile `config` copy was wrong
**Problem**: `COPY --chown=appuser:appuser config ./config` — no `config/` directory exists.
**Solution**: `COPY --chown=appuser:appuser config.yaml .` and added `chainlit.md .`.

---

## Final State (2026-05-09)

All three services start healthy on a fresh `docker compose up -d`:

```
NAME                 STATUS
law-agent-postgres   Up (healthy)   :5432
law-agent-phoenix    Up (healthy)   :6006, :4317, :9090
law-agent-app        Up (healthy)   :8000
```

Health endpoints:
- `GET /health` → `{"status":"healthy","components":{"database":{"status":"healthy"},"phoenix":{"status":"healthy"}}}`
- `GET /ready` → `{"ready":true,"status":"healthy"}`

Tests: 304 passed (no regressions).

---

## For Future Developers

1. **Middleware, not routes, for health checks**: Chainlit's SPA catch-all route is
   registered at module import time. Any routes you add after that are shadowed. Use
   `BaseHTTPMiddleware` on `chainlit.server.app` instead.

2. **`CREATE DATABASE` needs a shell script**: PostgreSQL's Docker entrypoint runs `.sql`
   files in a transaction block. `CREATE DATABASE` can't run there. Put it in a `.sh` file.

3. **Phoenix image is `arizephoenix/phoenix`**: Not `arizehq/phoenix`.

4. **Phoenix health endpoint is `/healthz`**: Not `/health`. No curl in the container — use
   Python urllib or wget for healthchecks.

5. **All DB and Phoenix env vars must be explicit in docker-compose**: The settings system
   only reads from config.yaml + a small set of env overrides — it does NOT use `DATABASE_URL`.
   Set `DB_HOST`, `DB_USER`, `DB_PORT`, `DB_NAME`, `DB_PASSWORD`, and `PHOENIX_ENDPOINT` individually.
