# Save India Project – Version 5.0

This folder holds the **5.0 release** of the Save India application.  It is the current, feature‑complete snapshot of the system and is provided for archive, review and deployment purposes.  Later development continues elsewhere; treat the contents of this directory as a self‑contained, immutable release.

Two cooperating components live here:

* `internal api` – a lightweight Flask service that ingests multiple external alert feeds and exposes them via a simple authenticated HTTP API.  It can run independently and is designed to operate on the Google Cloud "always free" tier.
* `projectZ_V5` – the web front‑end and mobile UI (also Flask) used by administrators and by the public interface.  It talks to the internal API for live alert information but can fall back to cached data if necessary.

Every subfolder contains its own `requirements.txt`, configuration examples and helper scripts; the steps below show how to bring the entire stack to life on a single machine.

---

## What's new in 5.0

This release builds on the architecture introduced in versions 3.x and 4.x and adds a number of refinements:

* **One‑command local startup** – `projectZ_V5/start_local.sh` (and accompanying Windows helpers) create virtual environments, install dependencies, generate API keys and launch both services with sensible defaults.
* **Improved authentication** – internal API supports API keys, JWT tokens and has on‑the‑fly key rotation with grace periods.  Front end can authenticate against Google OAuth or local accounts.
* **Pluggable data backends** – front end continues to support SQLite by default, with optional MySQL and PostgreSQL backends and bidirectional sync logic for hybrid deployments.
* **Resilient alert ingestion** – polling interval is configurable; scheduler thread is tolerant of upstream failures.  New `auto_fallback` policy for mobile alerts chooses cached data if live sources are unavailable.
* **Deployment scripts** – convenience helpers for GCP firewall rules, `systemd` services, Cloudflare tunnels and Nginx/HTTPS are included and tested on current Linux images.
* **Windows support** – a set of batch scripts under `projectZ_V5/scripts` let developers prepare and run both components on Windows without WSL.
* **Documentation overhaul** – this README and the companion sub‑folder READMEs have been rewritten for clarity and completeness.  Previous versions’ documentation is preserved in sibling directories for reference.

---

## Comparison with earlier releases

The `versions_history` folder alongside this release contains previous versions; the most relevant are summarized below.

| Version | Key differences compared to 5.0 |
|--------|---------------------------------|
| **3.0** | Monolithic split internal-api/front-end architecture, SQLite default, MySQL optional, simple alert polling, no JWT, manual key rotation, basic deployment scripts. |
| **4.x** | (intermediate) added push notifications, public API, React‑based front end, improved UI/UX.  Documentation was informal and scattered. |
| **5.0** | Refactored startup, comprehensive authentication modes, new helper scripts, Windows helpers, fully documented and ready for archival. |

For historical details consult the README files inside each numbered version folder; they remain part of the repository.

---

## Repository layout (v5.0)

```
v5.0/
  ├─ README.md             ← this file
  ├─ internal api/          ← Flask service that collects and serves alerts
  │   ├─ requirements.txt
  │   ├─ .env.example
  │   ├─ scripts/           ← migration and deployment helpers
  │   └─ README.md          ← service‑specific documentation
  ├─ projectZ_V5/           ← web front end and UI
  │   ├─ requirements.txt
  │   ├─ .env.example
  │   ├─ scripts/           ← deployment helpers plus Windows batch files
  │   ├─ start_local.sh     ← one‑command local launch
  │   └─ README.md          ← front‑end documentation
  └─ (other runtime artifacts are git‑ignored)
```

---

## Quick start (Linux / macOS / WSL)

1. Clone or copy this folder somewhere convenient; the example GitHub mirror is `https://github.com/Project-zeb/version_1`.

2. Run the one‑liner from the `projectZ_V5` directory:

   ```bash
   cd projectZ_V5
   ./start_local.sh
   ```

   The script will create virtual environments, install dependencies, populate `.env` files with sensible defaults (including randomly generated API keys) and launch both the internal API (`:5100`) and the main app (`:2000`).  If you wish to override any settings edit the generated `.env` files before rerunning.

3. Visit `http://127.0.0.1:2000/` in your browser to see the front‑end and click through the various pages.  Alerts are served by the companion API; consult the `internal api/README.md` for endpoint details.


## Quick start (Windows)

1. Open a PowerShell prompt and change into the `v5.0` directory:
   ```powershell
   cd 'C:\Users\Ayaan\Desktop\Project-Zeb\versions_history\v5.0'
   ```

2. Run the setup helper:
   ```powershell
   .\projectZ_V5\scripts\setup_windows.bat
   ```
   This will create virtual environments for both services and copy the example `.env` files.

3. Edit `projectZ_V5\.env` and `"internal api"\.env` to adjust any configuration values you care about.  In particular, confirm the database settings if you are using MySQL/PostgreSQL instead of SQLite.

4. Start the API and web app with the provided batch files:
   ```powershell
   .\projectZ_V5\scripts\run_api.bat
   .\projectZ_V5\scripts\run_web.bat
   ```

5. The services listen on the same ports as the shell script version (`5100` and `2000`).  Use your browser to explore the site.


## Deployment notes

The `projectZ_V5/scripts` directory contains several shell helpers for deploying the stack to Google Cloud and other Linux environments:

* `setup_main_gcp_service.sh` – installs a `systemd` service for the front end.
* `setup_gcp_firewall.sh` – adds firewall rules allowing HTTP/HTTPS traffic.
* `setup_nginx_https.sh` – configures Nginx and obtains Let's Encrypt certificates.
* `setup_cloudflare_tunnel.sh` – creates a Cloudflare tunnel with a fixed subdomain.
* Additional utility scripts are documented in the individual subfolder READMEs.

Most of the logic is unchanged from earlier versions; the scripts have been exercised on current Ubuntu LTS images.


## Preparing for push to GitHub

Before committing and pushing this directory to the `version_1` repository, perform the following checks:

1. **Secrets:** ensure there are no real passwords, API keys, database files or other sensitive data in the tree.  `.env` files must be reviewed or removed; the script will regenerate them on first run.
2. **Runtime artifacts:** delete any `*.db`, `*.pyc`, `.venv` directories or other build products.  The existing `.gitignore` already covers these, but run `git status` to verify.
3. **Documentation:** verify that the README files accurately describe the contents.  Update the version table above if additional historical context is needed.
4. **Windows scripts:** test the batch helpers on a clean Windows machine if possible; they should run without changing system state.

Once the checks are complete the folder is ready to be pushed.  Treat version 5.0 as a frozen release; further development happens in more recent branches or a separate repository.

---

For any questions about the history or layout of the project, consult the commit logs or the earlier version READMEs in this `versions_history` hierarchy.  They were written by the project team and contain additional context if you are curious about the architecture changes over time.
