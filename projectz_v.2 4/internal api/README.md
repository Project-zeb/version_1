# Internal Disaster API - Version 1.0

**Service**: Backend API for disaster alert aggregation  
**Version**: 1.0  
**Status**: Stable  
**Repository**: [github.com/Project-zeb/version_1](https://github.com/Project-zeb/version_1)

---

## Overview

The Internal Disaster API is a Flask-based backend service that:

- Aggregates disaster alerts from official government sources
- Provides secure REST API with JWT authentication
- Runs automatic sync scheduler every 5 minutes
- Supports SQLite (development) and PostgreSQL (production)
- Manages API keys with admin rotation capability

**Supported Alert Sources**:
- NDMA SACHET CAP Feed
- data.gov.in (OpenGov Data)
- MOSDAC (Meteorological)

---

## Technology Stack

- **Framework**: Flask 3.0.0+
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **ORM**: SQLAlchemy 2.0.25+
- **Migrations**: Alembic 1.13.1+
- **Server**: Gunicorn 22.0.0+
- **Task Scheduler**: APScheduler
- **Authentication**: PyJWT 2.8.0+

---

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_api_key.py
python run.py

# Server: http://localhost:5100
```

---

## Configuration

Create `.env` file:

```env
INTERNAL_API_KEY=generated-key-here
ADMIN_API_KEY=generated-admin-key-here
DATABASE_URL=sqlite:///disaster_api.db
POLL_INTERVAL_SECONDS=300
ENABLE_SCHEDULER=true
```

---

## API Endpoints

### Health
```bash
GET /health
GET /api/sources/status
```

### Alerts
```bash
GET /api/alerts
GET /api/alerts/<id>
POST /api/sync
```

### Authentication
```bash
POST /api/auth/token
GET /api/admin/keys (admin only)
POST /api/admin/keys/rotate (admin only)
```

---

## Database Setup

### SQLite (Development)
```bash
# No setup required, auto-created
python run.py
```

### PostgreSQL (Production)
```bash
docker-compose up -d postgres

# Or manually:
createdb disaster_api
createuser api_user
```

Update `.env`:
```env
DATABASE_URL=postgresql+psycopg2://api_user:password@localhost:5432/disaster_api
```

---

## Deployment (GCP)

```bash
./scripts/setup_gcp_service.sh
sudo systemctl start internal-disaster-api
sudo journalctl -u internal-disaster-api -f
```

---

## API Key Management

### Generate Keys
```bash
python scripts/generate_api_key.py
```

### Rotate Keys (Admin)
```bash
curl -X POST http://localhost:5100/api/admin/keys/rotate \
  -H "X-Admin-API-Key: your-admin-key" \
  -d '{"grace_seconds": 300}'
```

---

## Integration with Main App

Configure projectz_v.2/.env:
```env
INTERNAL_ALERTS_API_URL=http://127.0.0.1:5100/api/alerts
INTERNAL_ALERTS_API_KEY=<key-from-here>
```

---

## Troubleshooting

### API Key Generation Fails
```bash
alembic upgrade head
python scripts/generate_api_key.py
```

### Sync Not Running
```bash
curl http://localhost:5100/api/sources/status \
  -H "X-Internal-API-Key: your-key"
tail -50 /var/log/internal-disaster-api.log
```

---

## Documentation

- **Setup**: See this README
- **Deployment**: Follow scripts/ and deploy/ directories
- **API Use**: Refer to endpoint examples above
- **Database**: Review migrations in alembic/versions/
- **Main App**: See projectz_v.2/README.md for integration

---

**Last Updated**: March 2026  
**Status**: Stable Release (v1.0)  
**Repository**: github.com/Project-zeb/version_1

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_api_key.py
python scripts/generate_api_key.py
# Put first key as INTERNAL_API_KEY, second as ADMIN_API_KEY in .env
python run.py
```

Server: `http://localhost:5000`

## 3) Authentication modes

All `/api/*` routes are protected.

- API key mode:
  - `X-Internal-API-Key: <key>`
  - or `Authorization: Bearer <key>`
- JWT mode:
  - Get token from `POST /api/auth/token`
  - Use `Authorization: Bearer <jwt>`

Admin routes (`/api/admin/*`) require admin privileges.

## 4) JWT flow

1. Request token (using API key or admin key):

```bash
curl -X POST http://localhost:5000/api/auth/token \
  -H "X-Internal-API-Key: <your-internal-key>" \
  -H "Content-Type: application/json" \
  -d '{"expires_minutes": 30}'
```

2. Use returned JWT:

```bash
curl http://localhost:5000/api/alerts \
  -H "Authorization: Bearer <jwt>"
```

## 5) Admin key rotation (safe, no restart)

Rotate API keys with optional grace period:

```bash
curl -X POST http://localhost:5000/api/admin/keys/rotate \
  -H "X-Admin-API-Key: <your-admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"grace_seconds": 300, "label": "rotation-1"}'
```

- Returns the new API key once.
- Old API keys stay valid for `grace_seconds`, then expire.

List key metadata:

```bash
curl http://localhost:5000/api/admin/keys \
  -H "X-Admin-API-Key: <your-admin-key>"
```

## 6) Endpoints

- `GET /health`
- `GET /api/alerts`
- `GET /api/alerts/<id>`
- `GET /api/sources/status`
- `POST /api/sync`
- `POST /api/auth/token`
- `GET /api/admin/keys`
- `POST /api/admin/keys/rotate`

## 7) Environment variables

Use `.env.example` as template.

Important values:

- `DATABASE_URL`:
  - empty -> uses SQLite from `DB_PATH`
  - PostgreSQL example:
    `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/disaster_api`
- `INTERNAL_API_KEY=<long-random-key>`
- `ADMIN_API_KEY=<different-long-random-key>`
- `REQUIRE_API_KEY=true`
- `JWT_SECRET=` (optional, defaults to API/admin key material)
- `POLL_INTERVAL_SECONDS=300`
- `OGD_DATASET_URL` and `MOSDAC_ENDPOINT_URL` (optional)

## 8) Optional PostgreSQL (free with Docker)

```bash
docker compose up -d postgres
```

Then set:

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/disaster_api
```

## 9) Migrations

```bash
alembic upgrade head
```

## 10) Google Cloud Always Free (auto-sync even when laptop is off)

Use this when deployed on a GCP VM. The API will run as a background `systemd` service and keep syncing automatically.

1. SSH into your VM and clone/copy this `internal api` folder.

2. Setup Python and env:

```bash
cd "internal api"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_api_key.py
python scripts/generate_api_key.py
```

Put first generated key into `INTERNAL_API_KEY`, second into `ADMIN_API_KEY` in `.env`.

3. Install and start the service:

```bash
./scripts/setup_gcp_service.sh
```

4. Verify service status:

```bash
sudo systemctl status internal-disaster-api
sudo journalctl -u internal-disaster-api -f
curl -sS http://127.0.0.1:5100/health
```

5. Optional scheduler tuning in `.env`:

- `POLL_INTERVAL_SECONDS=300` (every 5 minutes)
- `ENABLE_SCHEDULER=true`
- `RUN_SYNC_ON_STARTUP=true`

Notes:

- Service is configured with one gunicorn worker to avoid duplicate scheduler threads.
- This runs on the VM, so syncing continues even when your personal device is powered off.
