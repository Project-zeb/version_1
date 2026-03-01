# Project-Zeb (Save India) - Version 1.0

**Official Release**: Version 1.0 - March 2026  
**Latest Version**: 2.0 (refer to latest branch for additional functionality)  
**Repository**: [github.com/Project-zeb/version_1](https://github.com/Project-zeb/version_1)  
**License**: See LICENSE file

## Live Disaster Alert Integration

This project now supports backend ingestion of external alert feeds and serves them as JSON for mobile UI.

### Environment variables

Add these optional variables in `.env`:

- `ALERT_SYNC_INTERVAL_SECONDS=120` (poll window; default is 120 seconds)
- `NDMA_CAP_FEED_URL=https://sachet.ndma.gov.in/cap_public_website.xml`
- `IMD_RSS_FEED_URL=https://mausam.imd.gov.in/`
- `CWC_FEED_URL=https://ffs.india-water.gov.in/`

### Backend endpoints

- `GET /api/mobile-alerts` → returns stored alerts and performs sync if cache is stale.
- `POST /api/mobile-alerts/sync` → manual sync trigger.
- `POST /api/mobile-alerts/sync?force=true` → force sync immediately.

### Notes

- NDMA SACHET can return `403` for some environments unless access is whitelisted or routed through an approved channel.
- IMD/CWC endpoints can also change structure or availability; keep feed URLs configurable in `.env`.

## Google Cloud Always Free - Main App Auto Start

Use this after setting up the internal API service so the website also runs continuously on the VM.

1) Prepare environment and dependencies:

```bash
cd projectz_v.2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Create `.env` (or update it) with at least:

```env
PORT=8001
APP_URL_SCHEME=https
INTERNAL_ALERTS_API_URL=http://127.0.0.1:5100/api/alerts
INTERNAL_ALERTS_API_KEY=<same key used by internal API>
INTERNAL_ALERTS_API_KEY_HEADER=X-Internal-API-Key
MOBILE_ALERTS_SOURCE_POLICY=live_only
PRIMARY_DB=sqlite
SQLITE_DB_PATH=app.db
secret_key=<your-random-secret>
```

3) Install and start `systemd` service:

```bash
./scripts/setup_main_gcp_service.sh
```

4) Verify:

```bash
sudo systemctl status projectz-main-web
sudo journalctl -u projectz-main-web -f
curl -sS http://127.0.0.1:8001/
```

5) Restart after code changes:

```bash
sudo systemctl restart projectz-main-web
```

Tip:

- Open GCP firewall for your app port (`8001`) if you access it directly from browser.

## Google Cloud Always Free - Nginx + HTTPS (Domain)

After `projectz-main-web` service is running, use Nginx as reverse proxy and enable HTTPS with Let's Encrypt.

1) Point your domain DNS `A` record to your VM external IP.

2) Ensure GCP firewall allows inbound `80` and `443`.

3) On VM, run:

```bash
cd projectz_v.2
DOMAIN=yourdomain.com EMAIL=you@example.com ./scripts/setup_nginx_https.sh
```

4) Verify:

```bash
curl -I http://yourdomain.com
curl -I https://yourdomain.com
sudo systemctl status nginx
```

Notes:

- Script installs `nginx`, `certbot`, and `python3-certbot-nginx`.
- It creates Nginx site config from `deploy/nginx/projectz.conf.template`.
- It enables HTTP→HTTPS redirect automatically.

## Google Cloud Firewall (One Command)

Use this to open inbound `80/443` and (optionally) tag your VM.

```bash
cd projectz_v.2
PROJECT_ID=<your-project-id> ./scripts/setup_gcp_firewall.sh
```

Apply the network tag to your VM in the same run:

```bash
PROJECT_ID=<your-project-id> INSTANCE_NAME=<vm-name> INSTANCE_ZONE=<zone> ./scripts/setup_gcp_firewall.sh
```

Notes:

- Script path: `scripts/setup_gcp_firewall.sh`
- Default firewall rule name: `projectz-allow-web`
- Default target tag: `projectz-web`

## Beginner One-Command Setup (VM)

If you are starting from zero, run everything with one script:

```bash
cd projectz_v.2
./scripts/full_gcp_setup.sh
```

With firewall + VM tag + HTTPS in same run:

```bash
PROJECT_ID=<your-project-id> INSTANCE_NAME=<vm-name> INSTANCE_ZONE=<zone> DOMAIN=yourdomain.com EMAIL=you@example.com ./scripts/full_gcp_setup.sh
```

Requirements for this script:

- Folder layout on VM must be sibling directories:
	- `projectz_v.2`
	- `internal api`
- VM user must have `sudo` access.
- DNS A record must point to VM IP if using HTTPS.