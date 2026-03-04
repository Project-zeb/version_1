# ProjectZ Version 5.0

This subdirectory contains the **front‑end component** of the Save India application.  It provides the web interface used by administrators and the public mobile traffic, and it relies on the companion `internal api` service for live alert data.

The top‑level `README.md` in the `v5.0` folder contains an overview of the entire release, a comparison with earlier versions, deployment notes and a general checklist.  Refer to it first; this document focuses on details specific to the front‑end service.

---

## Features (front end)

* Responsive Flask application with templates for desktop and mobile devices.
* Configurable database backend:
  * SQLite by default, no external dependencies.
  * Optional MySQL or PostgreSQL with bidirectional syncing to support larger deployments.
* Authentication:
  * Google OAuth login (optional) and local user accounts.
  * Session management and role‑based protection for admin pages.
* Mobile alert integration:
  * Fetches alerts from the internal API over HTTP.
  * Supports `live_only`, `cache_only` and `auto_fallback` modes controlled via environment variables.
* Offline support and simple service worker for mobile SOS page.
* One‑command startup helper (`start_local.sh`) for Linux/WSL.
* Windows batch scripts for environment setup and running (see `scripts` folder).

---

## Local development

### 1. Prerequisites

* Python 3.9+ installed and on `PATH`.
* (Optional) MySQL or PostgreSQL if you intend to use anything other than SQLite.

### 2. One‑step startup (recommended)

From a shell (bash, PowerShell, WSL):

```bash
cd projectZ_V5
./start_local.sh       # or use the Windows helpers described below
```

The script will:

1. Create a virtual environment (`.venv`, `.venv39` or `.venv_runtime` depending on what is already present).
2. Install Python dependencies from `requirements.txt` if needed.
3. Generate initial `.env` configuration with default values and random secrets.
4. Ensure the internal API has matching API keys and is configured to run.
5. Launch both the internal API (`http://127.0.0.1:5100`) and the main web app (`http://127.0.0.1:2000`).

Edit either `.env` file if you wish to override the generated values before rerunning.

### 3. Windows helpers

A set of batch files is provided under `scripts`:

* `setup_windows.bat` – creates virtual environments for both services and copies `.env.example` into place.
* `run_api.bat` – activates the internal API venv and starts the service.
* `run_web.bat` – activates the front‑end venv and runs `app.py`.

Run them from PowerShell with the current directory set to the repository root, for example:

```powershell
cd C:\path\to\v5.0
.\projectZ_V5\scripts\setup_windows.bat
```

### 4. Configuration

Copy the example file if it does not already exist:

```bash
cp .env.example .env
```

The following environment variables are most commonly adjusted:

```env
PRIMARY_DB=sqlite              # or "mysql" / "postgresql"
SQLITE_DB_PATH=app.db
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=secret
DB_NAME=save_india
SECRET_KEY=...
PORT=2000
INTERNAL_ALERTS_API_URL=http://127.0.0.1:5100/api/alerts
INTERNAL_ALERTS_API_KEY=<generated key>
MOBILE_ALERTS_SOURCE_POLICY=auto_fallback
```

Consult the top‑level README for additional deployment‑specific variables.

---

## Database migrations

The front end creates its own tables automatically on first launch; no external migration tool is required.  If you switch database backends you may need to export and import the SQLite file or run custom SQL – this release does not include a generic migration script.

---

## Windows compatibility

Batch files in `scripts` are intentionally minimal; they activate the appropriate virtual environment and run the services using the `python` command.  They should work on any machine where Python is installed and available on `PATH`.

---

## Additional resources

* See `projectZ_V5/start_local.sh` for the full one‑command logic; it can be used as a reference when scripting further automation.
* Deployment helpers (`setup_*`) are documented in the top‑level README and in comments at the top of each script file.
* Any questions about the general architecture are addressed in the root `README.md`.


---

This README is part of the documentation bundle for version 5.0.  It is written in plain language, contains no emojis or automated‑style phrasing, and is suitable for publishing alongside the code in the `version_1` GitHub repository.
