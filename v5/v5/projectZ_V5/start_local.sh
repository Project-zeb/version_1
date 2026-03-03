#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_DIR="$ROOT_DIR"
INTERNAL_DIR="$(cd "$ROOT_DIR/.." && pwd)/internal api"
INTERNAL_VENV="$INTERNAL_DIR/.venv"
MAIN_VENV=""

if [[ ! -d "$INTERNAL_DIR" ]]; then
  echo "Error: sibling folder 'internal api' not found."
  echo "Expected: $(cd "$ROOT_DIR/.." && pwd)/internal api"
  exit 1
fi

read_env_value() {
  local file="$1"
  local key="$2"
  if [[ ! -f "$file" ]]; then
    return 0
  fi
  grep -E "^${key}=" "$file" | tail -n 1 | cut -d'=' -f2- || true
}

upsert_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp_file
  tmp_file="$(mktemp)"

  if [[ -f "$file" ]]; then
    awk -v k="$key" -v v="$value" '
      BEGIN { replaced=0 }
      $0 ~ ("^" k "=") {
        print k "=" v
        replaced=1
        next
      }
      { print }
      END {
        if (!replaced) {
          print k "=" v
        }
      }
    ' "$file" > "$tmp_file"
  else
    printf "%s=%s\n" "$key" "$value" > "$tmp_file"
  fi

  mv "$tmp_file" "$file"
}

ensure_venv() {
  local app_dir="$1"
  local venv_dir="$2"
  local requirements_file="$3"
  local stamp_file="$venv_dir/.deps_installed"
  local created_venv=0
  local need_install=0

  if [[ ! -x "$venv_dir/bin/python" ]]; then
    echo "Creating virtualenv: $venv_dir"
    python3 -m venv "$venv_dir"
    created_venv=1
  fi

  if [[ ! -f "$requirements_file" ]]; then
    return 0
  fi

  if [[ "$created_venv" == "1" || "${FORCE_PIP_INSTALL:-0}" == "1" ]]; then
    need_install=1
  elif [[ -f "$stamp_file" && "$requirements_file" -nt "$stamp_file" ]]; then
    need_install=1
  elif [[ ! -f "$stamp_file" ]]; then
    if "$venv_dir/bin/python" -c "import flask,requests" >/dev/null 2>&1; then
      date -u +"%Y-%m-%dT%H:%M:%SZ" > "$stamp_file"
      need_install=0
    else
      need_install=1
    fi
  fi

  if [[ "$need_install" == "1" ]]; then
    echo "Installing dependencies for: $app_dir"
    "$venv_dir/bin/python" -m pip install --upgrade pip
    "$venv_dir/bin/python" -m pip install -r "$requirements_file"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$stamp_file"
  fi
}

choose_main_venv() {
  if [[ -x "$MAIN_DIR/.venv/bin/python" ]]; then
    MAIN_VENV="$MAIN_DIR/.venv"
    return
  fi
  if [[ -x "$MAIN_DIR/.venv_runtime/bin/python" ]]; then
    MAIN_VENV="$MAIN_DIR/.venv_runtime"
    return
  fi
  if [[ -x "$MAIN_DIR/.venv39/bin/python" ]]; then
    MAIN_VENV="$MAIN_DIR/.venv39"
    return
  fi
  MAIN_VENV="$MAIN_DIR/.venv"
}

echo "Preparing internal API environment..."
if [[ ! -f "$INTERNAL_DIR/.env" ]]; then
  cp "$INTERNAL_DIR/.env.example" "$INTERNAL_DIR/.env"
fi
ensure_venv "$INTERNAL_DIR" "$INTERNAL_VENV" "$INTERNAL_DIR/requirements.txt"

internal_api_key="$(read_env_value "$INTERNAL_DIR/.env" "INTERNAL_API_KEY")"
if [[ -z "${internal_api_key:-}" ]]; then
  internal_api_key="$(openssl rand -hex 32)"
fi

admin_api_key="$(read_env_value "$INTERNAL_DIR/.env" "ADMIN_API_KEY")"
if [[ -z "${admin_api_key:-}" ]]; then
  admin_api_key="$(openssl rand -hex 32)"
fi

upsert_env_value "$INTERNAL_DIR/.env" "INTERNAL_API_KEY" "$internal_api_key"
upsert_env_value "$INTERNAL_DIR/.env" "ADMIN_API_KEY" "$admin_api_key"
upsert_env_value "$INTERNAL_DIR/.env" "ENABLE_SCHEDULER" "true"
upsert_env_value "$INTERNAL_DIR/.env" "RUN_SYNC_ON_STARTUP" "true"
upsert_env_value "$INTERNAL_DIR/.env" "FLASK_PORT" "5100"

echo "Preparing main app environment..."
choose_main_venv
echo "Using main app virtualenv: $MAIN_VENV"
if [[ ! -f "$MAIN_DIR/.env" ]]; then
  cat > "$MAIN_DIR/.env" <<EOF
PRIMARY_DB=sqlite
SQLITE_DB_PATH=app.db
PORT=2000
SECRET_KEY=$(openssl rand -hex 24)
INTERNAL_ALERTS_API_URL=http://127.0.0.1:5100/api/alerts
INTERNAL_ALERTS_API_KEY=$internal_api_key
INTERNAL_ALERTS_API_KEY_HEADER=X-Internal-API-Key
INTERNAL_API_AUTOSTART=true
INTERNAL_API_SYNC_ON_ALERT_REQUEST=true
INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS=300
INTERNAL_API_POLL_INTERVAL_SECONDS=300
SQLITE_BOOTSTRAP_FROM_MYSQL=0
SQLITE_CONTINUOUS_SYNC_FROM_MYSQL=0
MYSQL_REVERSE_SYNC_FROM_SQLITE=0
MOBILE_ALERTS_SOURCE_POLICY=auto_fallback
EOF
fi

upsert_env_value "$MAIN_DIR/.env" "PRIMARY_DB" "sqlite"
upsert_env_value "$MAIN_DIR/.env" "SQLITE_BOOTSTRAP_FROM_MYSQL" "0"
upsert_env_value "$MAIN_DIR/.env" "SQLITE_CONTINUOUS_SYNC_FROM_MYSQL" "0"
upsert_env_value "$MAIN_DIR/.env" "MYSQL_REVERSE_SYNC_FROM_SQLITE" "0"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_ALERTS_API_URL" "http://127.0.0.1:5100/api/alerts"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_ALERTS_API_KEY_HEADER" "X-Internal-API-Key"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_ALERTS_API_KEY" "$internal_api_key"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_API_AUTOSTART" "true"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_API_SYNC_ON_ALERT_REQUEST" "true"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS" "300"
upsert_env_value "$MAIN_DIR/.env" "INTERNAL_API_POLL_INTERVAL_SECONDS" "300"
upsert_env_value "$MAIN_DIR/.env" "MOBILE_ALERTS_SOURCE_POLICY" "auto_fallback"

ensure_venv "$MAIN_DIR" "$MAIN_VENV" "$MAIN_DIR/requirements.txt"

echo "Starting Flask app at http://127.0.0.1:2000"
cd "$MAIN_DIR"
exec "$MAIN_VENV/bin/python" app.py
