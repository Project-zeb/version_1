# Save India Project – Version 3.0

This document describes the state of the **Save India** application at version 3.0.  This release is preserved for historical purposes; the active product continues on in later versions, but the code and documentation in this directory are enough for a new team member to install, run and understand the system as it stood at the time.

The repository is split into two cooperating pieces:

1. **internal api** – a small Flask service that collects alert feeds, exposes a simple HTTP API, and handles authentication and key rotation.
2. **projectz v3** – the web front‑end (also Flask) used by operators and by the public mobile interface.

Both components can be run independently; the web front‑end talks to the internal API for live alert data.  Each folder contains its own `requirements.txt` and supporting scripts, but the steps below show how to bring the whole stack to life on a single machine.

---

## Features in version 3.0

* Proper separation of data collection and presentation (internal API + front‑end).
* Dual database support in the front end (SQLite by default, optional MySQL with bidirectional sync).
* Authentication on the internal API with API keys, JWT tokens and admin endpoints.
* Key rotation without restarting the API service.
* Periodic polling of multiple external sources (NDMA SACHET, MOSDAC, data.gov.in).
* Google OAuth login and basic user management in the front end.
* Mobile‑friendly templates for alerts, reports and SOS screens; offline fallback page.
* Environment‑driven configuration throughout – nothing is hard‑coded.
* Ready for deployment to a Linux VM (scripts included for systemd and GCP setup).

---

## Getting started (Unix-like systems)

### 1. Clone and navigate

```bash
# this repository is intended for archival history; replace the URL with
# whatever location you are using to store it (private git, zip archive, etc.)
cd /path/to/where/you/keep/projects
git clone <repository-url> projectz‑v3
cd projectz-v3
```

### 2. Internal API

```bash
cd "internal api"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edit later
python scripts/generate_api_key.py   # run twice
# put first key into INTERNAL_API_KEY and second into ADMIN_API_KEY inside .env
python run.py
```

The API listens on `http://localhost:5100` by default.  Use `curl` or your browser to hit `/health` and `/api/alerts` once the service is running.

> See `internal api/README.md` for more detailed notes about auth, migrations and GCP deployment.

### 3. Web application

```bash
cd "../projectz v3"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in values described below
python app.py              # or use `flask run` if you prefer
```

By default the front end will attempt to reach the internal API at `http://127.0.0.1:5100/api/alerts`.  Verify the `.env` variables `INTERNAL_ALERTS_API_URL` and `INTERNAL_ALERTS_API_KEY` are set appropriately.

### 4. Database migrations

The internal API uses Alembic; run `alembic upgrade head` from the `internal api` folder when the service is stopped.  The front end creates its own tables on first launch.

### 5. Windows support

A few `.bat` helpers are provided in the scripts folder (see below).  They are simple wrappers around the commands above and assume you are using PowerShell.

---

## Environment configuration

Each service reads a `.env` file in its directory.  Templates are included (`.env.example`).  Required variables are listed in the respective README files; the web app template is shown below:

```
# database selection
PRIMARY_DB=sqlite
SQLITE_DB_PATH=app.db
# or for MySQL use DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# application behaviour
SECRET_KEY=             # random string for Flask session
APP_URL_SCHEME=http

# optional Google OAuth (used for login)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

# mobile alert defaults
MOBILE_ALERTS_SOURCE_POLICY=live_only
SACHET_CAP_URL=https://sachet.ndma.gov.in/CapFeed

# internal api access (fetch alerts)
INTERNAL_ALERTS_API_URL=http://127.0.0.1:5100/api/alerts
INTERNAL_ALERTS_API_KEY=
INTERNAL_ALERTS_API_KEY_HEADER=X-Internal-API-Key
```

The internal API has its own `.env.example` describing its variables; copy and edit that file before first run.

---

## Windows batch helpers

In `projectz v3\scripts` you will find the following convenience files:

* `setup_windows.bat` – creates virtual environments for both components and copies `.env.example` files.
* `run_api.bat` – activates the API venv and starts `run.py`.
* `run_web.bat` – activates the web venv and starts `app.py`.

Use PowerShell to execute them, for example:

```powershell
cd "C:\Users\Ayaan\Desktop\Project-Zeb\versions_history\v3.0\ProjectZ_version3"
.\projectz v3\scripts\setup_windows.bat
```

Lines in the batch files are commented to explain each step; the scripts do nothing destructive and are safe to rerun.

---

> **Security note:**
> This archive contains no real credentials or secret keys.  Every
> `.env` file is ignored by the `.gitignore` entries and the helper
> scripts do not embed any sensitive values.  Before pushing this folder
> to any remote repository or sharing it with others, verify that
> no accidental API keys, database passwords or other private data have
> been committed.

## Version history

Detailed notes are maintained in `VERSION_HISTORY.md` but a quick summary of the major differences between 2.x and 3.0 is listed here.

| Version | Highlights |
|--------|------------|
| **2.x** | Monolithic Flask app.  SQLite only.  Alerts pulled directly in the front end.  No API key authentication.  No OAuth login.  Basic mobile templates. |
| **3.0** | Split internal API + front end.  Dual database backend with sync.  API authentication with key rotation and JWT.  Google OAuth.  Systemd/GCP deployment scripts.  Improved mobile UI and offline support. |

The project continued beyond v3.0; later releases added features such as push notifications, an external-facing public API, and a redesigned React front end.  Those changes are not present in this branch.

---

## Additional notes

* The `internal api` service is intentionally lightweight so that it can run on low‑cost Google Cloud "always free" VMs and keep syncing even when your laptop is off.
* The front end's database proxy layer allows transparent switching between SQLite and MySQL without rewriting any SQL statements.
* When migrating from earlier versions, preserve the SQLite file if you wish to keep existing user accounts; the proxy will work with it.

---

For more background or questions about the history of the project consult the commit log or reach out to the original author.  This README is intended as the final documentation for version 3.0 and should not require any additional AI‑generated embellishments.

---

## Final checklist

1. Remove any development `.db` files or other runtime artifacts from the repository.  They are already gitignored but double‑check by running `git status`.
2. Ensure both component directories contain only the `requirements.txt`, source code, scripts and the documentation added above.  No personal notes or credentials should be stored.
3. Confirm `.env.example` files are up‑to‑date and contain no real values.  These templates may be safely committed.
4. Run the Windows batch scripts and shell scripts to make sure they execute without errors on a clean environment; they are intended to be reproducible helpers.

With the preceding items satisfied the folder is ready for archival or “push” to your version‑history repository.  Treat this version as immutable; further active development occurs in the newer branches of the product.
