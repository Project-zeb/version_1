import atexit
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from flask import Flask, g, jsonify, request

from disaster_api import db
from disaster_api.auth_service import AuthService
from disaster_api.config import Settings, load_settings
from disaster_api.scheduler import PollingScheduler
from disaster_api.services.aggregator import DisasterAggregator


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _parse_int(value: Optional[Any], default: int, min_value: int, max_value: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _should_start_scheduler(app: Flask, settings: Settings) -> bool:
    if not settings.enable_scheduler:
        return False
    # Avoid duplicate scheduler thread in Flask debug reloader parent process.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return False
    return True


def create_app(settings: Optional[Settings] = None) -> Flask:
    _configure_logging()
    app = Flask(__name__)
    current_settings = settings or load_settings()

    db.init_db(current_settings.database_url)
    auth_service = AuthService(current_settings)
    aggregator = DisasterAggregator(current_settings)
    scheduler = PollingScheduler(current_settings.poll_interval_seconds, aggregator.run_cycle)
    app_logger = logging.getLogger(__name__)

    app.config["SETTINGS"] = current_settings
    app.extensions["auth_service"] = auth_service
    app.extensions["aggregator"] = aggregator
    app.extensions["scheduler"] = scheduler

    if current_settings.require_api_key and not (
        current_settings.internal_api_key or current_settings.admin_api_key
    ):
        app_logger.warning(
            "REQUIRE_API_KEY is enabled but no bootstrap API keys were configured."
        )

    @app.before_request
    def authorize_internal_routes():
        if not request.path.startswith("/api/"):
            return None
        requires_admin = request.path.startswith("/api/admin/")
        principal = auth_service.authenticate_request(request, require_admin=requires_admin)
        if principal is not None:
            g.auth_principal = principal
            return None
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "message": (
                        f"Provide API key in '{current_settings.api_key_header}' "
                        f"or '{current_settings.admin_api_key_header}', "
                        "or use Authorization Bearer JWT."
                    ),
                }
            ),
            401,
        )

    @app.get("/health")
    def health() -> tuple:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return jsonify({"status": "ok", "timestamp_utc": now}), 200

    @app.get("/api/alerts")
    def get_alerts() -> tuple:
        limit = _parse_int(request.args.get("limit"), default=500, min_value=1, max_value=5000)
        source = request.args.get("source")
        severity = request.args.get("severity")
        area = request.args.get("area")
        since = request.args.get("since")

        alerts = db.list_alerts(
            current_settings.database_url,
            limit=limit,
            source=source,
            severity=severity,
            area=area,
            since=since,
        )
        return jsonify({"count": len(alerts), "items": alerts}), 200

    @app.get("/api/alerts/<int:alert_id>")
    def get_alert(alert_id: int) -> tuple:
        alert = db.get_alert_by_id(current_settings.database_url, alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        return jsonify(alert), 200

    @app.get("/api/sources/status")
    def get_source_status() -> tuple:
        runs = db.get_source_runs(current_settings.database_url)
        return jsonify({"count": len(runs), "items": runs}), 200

    @app.post("/api/sync")
    def run_sync() -> tuple:
        summary = aggregator.run_cycle()
        return jsonify(summary), 200

    @app.post("/api/auth/token")
    def create_access_token() -> tuple:
        data = request.get_json(silent=True) or {}
        requested_minutes = data.get("expires_minutes")
        principal = getattr(g, "auth_principal", {"subject": "internal-client", "role": "api"})
        token_payload = auth_service.issue_jwt(principal, requested_minutes=requested_minutes)
        return jsonify(token_payload), 200

    @app.get("/api/admin/keys")
    def get_api_keys() -> tuple:
        return jsonify(auth_service.list_api_keys()), 200

    @app.post("/api/admin/keys/rotate")
    def rotate_api_keys() -> tuple:
        data = request.get_json(silent=True) or {}
        grace_seconds = _parse_int(data.get("grace_seconds"), default=300, min_value=0, max_value=86400)
        label_raw = data.get("label")
        label = str(label_raw).strip() if label_raw is not None else None
        rotation = auth_service.rotate_api_key(grace_seconds=grace_seconds, label=label)
        return jsonify(rotation), 200

    if _should_start_scheduler(app, current_settings):
        scheduler.start(run_immediately=current_settings.run_sync_on_startup)
        atexit.register(scheduler.stop)
        app_logger.info(
            "Background polling enabled: every %s seconds",
            current_settings.poll_interval_seconds,
        )
    else:
        app_logger.info("Background polling disabled")

    return app
