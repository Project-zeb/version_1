# Production Setup Guide – Save India v3.0

This document describes the steps required to deploy the complete version 3.0
stack as a production‑style service on a single host (Linux or Windows).  It
assumes the code has already been checked out in the `ProjectZ_version3`
directory.

The two components (internal API and web front end) are independent but run
against the same filesystem; the front end fetches alert data from the API over
HTTP.  Both can be served with `gunicorn` and managed by `systemd` on Linux or
as long–running services on Windows.

> For strictly development use the simple quick start in the main README; this
> page is for when you want something closer to a real deployment.

---

## 1. Prepare the environment

1. Install Python 3.11 or later.
2. Ensure `git`, `curl`/`wget` and a C compiler (for optional packages) are
   available.  On Ubuntu/Debian:
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-venv python3-pip \
       build-essential git nginx
   ```
3. Create a directory for logs if desired, e.g. `/var/log/saveindia` and give
   the appropriate user write permission.

---

## 2. Create virtual environments

We rely on readable `venv`s so you can inspect installed packages or run
interactive shells.

```bash
cd /path/to/ProjectZ_version3
python3 -m venv .venv-all          # optional combined environment
source .venv-all/bin/activate
pip install --upgrade pip
pip install -r full_requirements.txt
# or, if preferred, create separate venvs in each component folder
```

Using the combined `venv` simplifies deployment but is not required.

---

## 3. Configuration files

Each component reads a `.env` file in its directory.  Copy and edit the examples
provided.

```bash
cp "internal api"/.env.example "internal api"/.env
cp "projectz v3"/.env.example "projectz v3"/.env
```

Populate values such as database connection strings, the two API keys, a
sensible `SECRET_KEY` for the web app, OAuth credentials if you intend to
enable Google login, and adjust ports (`FLASK_PORT` for the API, `PORT` for the
web app) if you wish to serve on non‑default ports.  Use environment variables
or a secrets manager if you prefer not to keep these files on disk.

> **Important:** never commit the `.env` files.  They are already excluded by
> `.gitignore`.

---

## 4. Database migrations (API)

Before starting the API service run:

```bash
cd "internal api"
alembic upgrade head
```

This will apply the schema to whatever database you have configured
(`DATABASE_URL` or default SQLite).  The web front end creates its own tables
on first launch automatically.

---

## 5. Systemd services (Linux)

Two unit files are included in the repository under the appropriate `scripts`
directory.  Install them as follows:

```bash
sudo cp "internal api/deploy/internal-disaster-api.service" /etc/systemd/system/
sudo cp "projectz v3/deploy/projectz-main-web.service" /etc/systemd/system/

# reload and enable
sudo systemctl daemon-reload
sudo systemctl enable internal-disaster-api
sudo systemctl enable projectz-main-web

# start immediately
sudo systemctl start internal-disaster-api
sudo systemctl start projectz-main-web
```

Review the service files to ensure paths and environment variable references match
your setup; they simply activate the virtual environment and run `gunicorn`.

The API listens by default on `127.0.0.1:5100`; you can front it with `nginx`
if exposing to the public.

---

## 6. Windows setup

Most production Windows deployments use a dedicated service manager such as
`nssm` or Windows Services.  The `scripts` folder contains `setup_windows.bat`
which can install and run the components but is intended for development.  For a
more robust installation, use something like:

```powershell
# create venvs (as shown earlier)
# install aal the dependencies
# then register each script as a service using sc.exe or nssm
nssm install "SaveIndiaAPI" "C:\path\to\python.exe" "C:\path\to\ProjectZ_version3\internal api\run.py"
# configure environment variables through the service GUI
```

Customizing services is beyond the scope of this document; the batch file
`setup_production.bat` (see below) simply replicates the venv creation step and
copies `.env.example` files.

---

## 7. Firewall and reverse proxy

If the host is accessible externally you should use a reverse proxy (nginx is
recommended) and a firewall to restrict direct access to the internal API port.
A sample `nginx` configuration is provided in
`projectz v3/deploy/nginx/projectz.conf.template`.

---

## 8. Startup and testing

Once both services are running, test them locally:

```bash
curl http://127.0.0.1:5100/health
curl http://127.0.0.1:5100/api/alerts
curl http://127.0.0.1:8001/          # or whichever port your web app uses
```

Create an admin API key, request a JWT and ensure the front-end can fetch alerts.

---

## 9. Backups and maintenance

* Schedule a cron job (or Windows task) to back up your database file or
  periodically dump the MySQL/PostgreSQL data.
* Keep Python dependencies up to date carefully; pin versions in
  `full_requirements.txt` to avoid unexpected upgrades.
* Log rotation can be handled by `logrotate` (Linux) or built into your
  service manager.

---

## 10. Cleanup

Before distributing or archiving this release, remove any development database
files and log files.  Confirm the repository contains only source, docs, and
example configuration.  Then tag the commit as `v3.0` and store it in your
version‑history system.

---

This completes the production setup procedure for Save India v3.0.  For later
versions consult the documentation in their respective repositories.