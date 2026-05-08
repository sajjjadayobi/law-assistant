# Phase 8: Deployment & Production - Complete Guide

This guide provides comprehensive instructions for deploying the Law Agent application in production using Docker Compose.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Architecture Overview](#architecture-overview)
4. [Configuration & Secrets Management](#configuration--secrets-management)
5. [Health Checks & Monitoring](#health-checks--monitoring)
6. [Logging Configuration](#logging-configuration)
7. [Production Deployment](#production-deployment)
8. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
9. [Backup & Restore](#backup--restore)
10. [Performance Tuning](#performance-tuning)

---

## Prerequisites

### System Requirements

- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM (minimum, 8GB recommended)
- 50GB disk space (for database and logs)
- Network access for OpenTelemetry (optional, for Phoenix)

### Software Requirements

```bash
# Check Docker version
docker --version  # Should be 20.10+

# Check Docker Compose version
docker-compose --version  # Should be 2.0+

# Install Docker Compose v2 if needed
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### API Keys

- **Anthropic API Key** (required): Get from https://console.anthropic.com/account/keys
- **OpenTelemetry Endpoint** (optional): For Phoenix observability

---

## Quick Start

### 1. Clone Repository and Set Up Environment

```bash
# Clone the repository
git clone <repo-url> law-agent
cd law-agent

# Copy environment template
cp .env.example .env

# Edit .env with your secrets
nano .env
```

### 2. Edit Environment Variables

Update `.env` with your actual values:

```bash
# Database
DB_PASSWORD=your-secure-db-password

# LLM API (Model-Agnostic)
LLM_AUTH_TOKEN=your-llm-api-key-here
LLM_BASE_URL=  # Optional: custom endpoint

# Optional: Observability
LOGGING_FORMAT=json  # For production
```

### 3. Start All Services

```bash
# Build Docker image and start services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Check logs
docker-compose logs app
```

### 4. Verify Deployment

```bash
# Check health status
curl http://localhost:8000/health

# Access the application
# Chainlit UI: http://localhost:8000
# Phoenix: http://localhost:6006
# Database: localhost:5432
```

---

## Architecture Overview

### Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Law Agent Deployment                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Chainlit │    │ OpenTel  │    │ Health   │          │
│  │   UI     │───▶│  Tracing │───▶│ Checks   │          │
│  └────┬─────┘    └──────┬───┘    └──────────┘          │
│       │                 │                               │
│       ▼                 ▼                               │
│  ┌──────────────────────────────────┐                  │
│  │    Law Agent Application (Python) │                  │
│  │  - PydanticAI Agent               │                  │
│  │  - Search Tools                   │                  │
│  │  - Citation System                │                  │
│  └────────────┬─────────────────────┘                  │
│               │                                        │
│       ┌───────┴────────┬──────────────┐               │
│       ▼                ▼              ▼               │
│  ┌─────────────┐ ┌──────────┐ ┌────────────┐         │
│  │ PostgreSQL  │ │  Phoenix │ │  Network   │         │
│  │  Database   │ │(Optional)│ │  Services  │         │
│  └─────────────┘ └──────────┘ └────────────┘         │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Chainlit UI | 8000 | Chat interface |
| PostgreSQL | 5432 | Document database |
| Phoenix UI | 6006 | Observability dashboard |
| Phoenix OTLP | 4317 | OpenTelemetry metrics |
| Prometheus | 9090 | Metrics (optional) |

---

## Configuration & Secrets Management

### Environment Variables

All secrets must be set via environment variables (never in code or config.yaml):

```bash
# Database
DB_PASSWORD=secure-password-here
DB_USER=postgres              # Optional override
DB_HOST=postgres              # Docker service name
DB_PORT=5432
DB_NAME=law_agent

# LLM API (Model-Agnostic)
LLM_AUTH_TOKEN=your-llm-api-key
LLM_BASE_URL=  # Optional: custom endpoint

# Logging
LOGGING_FORMAT=json            # For production
LOGGING_FILE_PATH=/var/log/law-agent.log  # Optional

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
OTEL_SERVICE_NAME=law-agent
```

### Loading Configuration

Configuration is loaded with this priority:

1. **Environment variables** (highest priority)
2. **config.yaml** (defaults)
3. **Pydantic model defaults** (fallback)

### Secrets Best Practices

✅ **DO:**
- Store secrets in `.env` file (added to .gitignore)
- Use strong passwords (minimum 16 characters)
- Rotate secrets regularly
- Use separate credentials per environment
- Store `.env` securely (not in version control)

❌ **DON'T:**
- Commit `.env` to git
- Log secrets or API keys
- Use weak passwords
- Share `.env` in chat or email
- Hardcode secrets in code

---

## Health Checks & Monitoring

### Health Check Endpoints

The application provides health check endpoints for Docker and Kubernetes:

#### /health (Docker Health Check)

Returns comprehensive health status of all components:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "phoenix": {
      "status": "healthy",
      "message": "Phoenix connection successful"
    }
  }
}
```

Possible statuses:
- `healthy` - All components working
- `degraded` - Some non-critical components failing (e.g., Phoenix)
- `unhealthy` - Critical components failing (e.g., database)

#### /ready (Kubernetes Readiness Probe)

Returns application readiness for traffic:

```bash
curl http://localhost:8000/ready
```

Response:
```json
{
  "ready": true,
  "status": "healthy",
  "details": { ... }
}
```

### Docker Health Check Configuration

In `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s          # Check every 10 seconds
  timeout: 5s            # Timeout after 5 seconds
  retries: 5             # Fail after 5 retries
  start_period: 30s      # Wait 30s before first check
```

### Monitoring the Deployment

```bash
# Watch service status
docker-compose ps

# Check specific service health
docker-compose exec app curl http://localhost:8000/health

# View application logs
docker-compose logs -f app

# View database logs
docker-compose logs -f postgres

# View Phoenix logs
docker-compose logs -f phoenix
```

---

## Logging Configuration

### Log Levels

Set via `config.yaml` or `LOG_LEVEL` environment variable:

| Level | Use Case | Output |
|-------|----------|--------|
| DEBUG | Development, detailed tracing | Very verbose |
| INFO | Production (default), normal operations | Moderate detail |
| WARNING | Unexpected situations | Warnings only |
| ERROR | Critical failures | Errors only |

### Log Formats

#### Text Format (Development)

```
2025-04-20 10:15:23.456 [INFO] chat_started session_id=conv-123
2025-04-20 10:15:24.789 [INFO] calling_agent session_id=conv-123
2025-04-20 10:15:28.012 [INFO] message_processed_success session_id=conv-123
```

#### JSON Format (Production)

```json
{
  "timestamp": "2025-04-20T10:15:23.456Z",
  "level": "INFO",
  "event": "chat_started",
  "session_id": "conv-123",
  "logger": "law_agent.ui.app"
}
```

### Log Rotation

Logs automatically rotate when they reach 10MB:

```
law-agent.log           (current, < 10MB)
law-agent.log.1         (previous, 10MB)
law-agent.log.2         (older, 10MB)
law-agent.log.3         (older, 10MB)
law-agent.log.4         (older, 10MB)
law-agent.log.5         (oldest, 10MB)
```

### Configuring File Logging

In `docker-compose.yml`, add volume for logs:

```yaml
app:
  volumes:
    - ./logs:/var/log/law-agent
  environment:
    LOGGING_FILE_PATH: /var/log/law-agent/app.log
    LOGGING_FORMAT: json
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Docker 20.10+ and Compose 2.0+ installed
- [ ] Anthropic API key obtained
- [ ] `.env` file created with all secrets
- [ ] Database password set and secure
- [ ] Sufficient disk space (50GB+)
- [ ] All tests passing locally
- [ ] Performance baseline documented

### Step-by-Step Deployment

#### 1. Prepare Server

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Create application directory
sudo mkdir -p /opt/law-agent
cd /opt/law-agent

# Clone repository
git clone <repo-url> .

# Create logs directory
sudo mkdir -p logs
sudo chown $(id -u):$(id -g) logs
```

#### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Verify secrets are set
grep -E "DB_PASSWORD|LLM_AUTH_TOKEN" .env | head -2
```

#### 3. Build and Deploy

```bash
# Build Docker images
docker-compose build

# Start services in background
docker-compose up -d

# Monitor startup (watch for "healthy")
watch 'docker-compose ps'
```

#### 4. Verify Deployment

```bash
# Check all services healthy
docker-compose ps

# Test API endpoints
curl http://localhost:8000/health

# Check logs for errors
docker-compose logs --tail=50 app

# Test basic query (from app container)
docker-compose exec app python -c "
from law_agent.database.connection import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM documents'))
    print(f'Documents in database: {result.scalar()}')
"
```

### Blue-Green Deployment

For zero-downtime updates:

```bash
# 1. Build new image
docker-compose build app

# 2. Start new container on temporary port
docker-compose -f docker-compose.yml -f docker-compose.new.yml up -d app-new

# 3. Verify new instance
curl http://localhost:8001/health  # Temporary port

# 4. Switch traffic (via load balancer or DNS)
# Update nginx/load balancer to point to :8001

# 5. Stop old instance
docker-compose down app

# 6. Rename new to production
# docker-compose -f docker-compose.new.yml down
```

---

## Monitoring & Troubleshooting

### Arize Phoenix Observability

Phoenix provides real-time monitoring of:
- All conversation traces
- Token usage and costs
- Response latencies
- Error rates and types
- User feedback

Access at: http://localhost:6006

### Common Issues

#### Application Won't Start

```bash
# Check logs
docker-compose logs app | head -50

# Verify database is running
docker-compose ps postgres

# Test database connection
docker-compose exec postgres psql -U postgres -c "SELECT 1"
```

#### Database Connection Failed

```bash
# Verify credentials in .env
grep DB_ .env

# Check database health
docker-compose exec postgres pg_isready

# Check network
docker-compose exec app ping postgres
```

#### High Memory Usage

```bash
# Check memory consumption
docker stats

# Reduce connection pool (in config.yaml)
database:
  pool_size: 3
  max_overflow: 5

# Restart services
docker-compose restart
```

#### Slow Queries

```bash
# Check query performance in Phoenix UI
# Or view PostgreSQL logs:
docker-compose logs postgres | grep "slow query"

# Analyze table statistics
docker-compose exec postgres psql -U postgres -d law_agent -c "ANALYZE documents;"
```

---

## Backup & Restore

### Automated Backups

Create a backup script (`backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/backups/law-agent"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
docker-compose exec -T postgres pg_dump -U postgres law_agent \
  | gzip > "$BACKUP_DIR/law_agent_$DATE.sql.gz"

# Backup Phoenix data
docker-compose exec -T postgres pg_dump -U postgres phoenix \
  | gzip > "$BACKUP_DIR/phoenix_$DATE.sql.gz"

# Backup configuration
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" config/ .env

# Keep only last 7 days
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
```

Make it executable and schedule with cron:

```bash
chmod +x backup.sh

# Run daily at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/law-agent/backup.sh") | crontab -
```

### Manual Restore

```bash
# Stop services
docker-compose down

# Restore database from backup
zcat /backups/law-agent/law_agent_20250420_000000.sql.gz \
  | docker-compose exec -T postgres psql -U postgres

# Restore configuration
tar xzf /backups/law-agent/config_20250420_000000.tar.gz

# Start services
docker-compose up -d
```

---

## Performance Tuning

### Database Optimization

Already configured indexes:
- Search vector index (FTS)
- Document type index
- Document date index
- Relation indexes

Monitor performance:

```bash
# Check index usage
docker-compose exec postgres psql -U postgres -d law_agent -c "
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
"

# Check slow queries (if enabled)
docker-compose exec postgres psql -U postgres -d law_agent -c "
SELECT query, calls, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

### Application Optimization

Already implemented:
- Connection pooling (5-10 connections)
- Response caching (5-day TTL)
- Search result caching (LRU cache)
- Async processing
- Batch query optimization

Monitor in Phoenix:
- Token usage per conversation
- Response latency percentiles
- Cache hit rates

---

## Support & Troubleshooting

### Getting Help

1. **Check logs**: `docker-compose logs <service>`
2. **Phoenix traces**: Check http://localhost:6006 for detailed traces
3. **Health endpoints**: Use `/health` and `/ready` for diagnostics
4. **Documentation**: Review `PERFORMANCE.md` for optimization

### Common Commands

```bash
# View all services
docker-compose ps

# View logs for specific service
docker-compose logs -f app

# Execute command in container
docker-compose exec app curl http://localhost:8000/health

# Restart a service
docker-compose restart app

# Stop all services
docker-compose down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# Rebuild image
docker-compose build app
```

---

## Next Steps

After successful deployment:

1. **Set up monitoring**: Configure alerts in Phoenix or your monitoring system
2. **Enable backups**: Set up automated backup scripts
3. **Document**: Create runbooks for your team
4. **Performance**: Establish baseline metrics for comparison
5. **Security**: Review firewall rules and access controls

---

**Last Updated**: April 2025
**Version**: 1.0
