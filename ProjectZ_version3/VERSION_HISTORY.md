# Version History for Save India Project

This document records the major changes and motivations for each public version of the codebase.  Version 3.0 is considered the last release of this branch; subsequent versions (4.x, 5.x) were developed in a separate repository and are not included here.

## 3.0 (March 2026)

* Split the monolithic application into two cooperating services: the **internal API** is responsible for collecting alerts from external sources and serving them via a restricted HTTP API; the **web front‑end** renders pages for operators and the public.
* Internal API introduces API key authentication, JWT tokens and an administrative key rotation endpoint.  Keys can be replaced on the fly with a configurable grace period.
* Front‑end supports two database backends (SQLite by default, optional MySQL).  A lightweight proxy layer keeps the SQL syntax uniform and a background thread keeps SQLite in sync with MySQL.
* Added Google OAuth integration for user login and simple user account management.
* Redesigned mobile‑friendly HTML templates and implemented an offline fallback page for the SOS screen.
* Configuration of every behaviour via environment variables; no hard‑coded strings or URLs remain.
* Added deployment scripts for Google Cloud VMs (systemd unit files, firewall helpers, full bootstrap script).
* Introduced `alembic` migrations for the internal API database and a pre‑created `run.py` entry point.
* Overall the codebase was refactored for clarity and maintainability; unnecessary dependencies were removed.

### Comparison with earlier 2.x series

| area | 2.x behaviour | 3.0 behaviour |
|------|--------------|---------------|
| Architecture | Single Flask process | Two separate Flask services (API + front end) |
| Authentication | None / minimal | API keys, JWT, Google OAuth, admin roles |
| Database | SQLite only | SQLite or MySQL with sync proxy |
| External sources | Pulled directly by front end | Centralised in internal API; scheduler thread |
| Deployment | Manual | Scripts for systemd and GCP automation |
| Mobile UI | Basic | Responsive templates, offline support |
| Version tracking | Not documented | This file and README added |

## Earlier releases (summary)

* **2.7** – added OAuth and basic user locking.
* **2.5** – initial rollout of mobile views and alert listing.
* **2.0** – original prototype with SQLite and hard‑coded CAP URL, intended for proof of concept.

(The 2.x history dates back to 2024; most of the internal commits are available in the version control system but are not reproduced here.)

---

This file may be updated as changes are back‑ported to the archived code, but the intention is for 3.0 to be the final documented version in this folder.