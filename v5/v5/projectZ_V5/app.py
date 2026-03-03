from flask import Flask, url_for, render_template, redirect, request,session, jsonify, send_file, abort
from dotenv import load_dotenv
import os
import json
import math
import atexit
import secrets
import base64
import hashlib
import mimetypes
import shutil
import subprocess
import requests # api will be called using this libraray
import sqlite3
import decimal
import threading
import time as time_module
import tempfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
try:
    from authlib.integrations.flask_client import OAuth
    AUTHLIB_IMPORT_ERROR = None
except Exception as authlib_import_exc:  # noqa: BLE001
    OAuth = None
    AUTHLIB_IMPORT_ERROR = authlib_import_exc
# import bcrypt


# Load environment variables from .env file


load_dotenv()

# Database config
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
DB_PATH = os.getenv("SQLITE_DB_PATH", "app.db")
DB_PRIMARY = str(os.getenv("PRIMARY_DB", "sqlite") or "sqlite").strip().lower()
if DB_PRIMARY not in ["mysql", "sqlite"]:
    DB_PRIMARY = "sqlite"
MYSQL_USE_PURE = str(os.getenv("MYSQL_USE_PURE", "1") or "1").strip().lower() not in ["0", "false", "no", "off"]
SQLITE_BOOTSTRAP_FROM_MYSQL = str(os.getenv("SQLITE_BOOTSTRAP_FROM_MYSQL", "0") or "0").strip().lower() in ["1", "true", "yes", "on"]
SQLITE_CONTINUOUS_SYNC_FROM_MYSQL = str(os.getenv("SQLITE_CONTINUOUS_SYNC_FROM_MYSQL", "0") or "0").strip().lower() in ["1", "true", "yes", "on"]
MYSQL_REVERSE_SYNC_FROM_SQLITE = str(os.getenv("MYSQL_REVERSE_SYNC_FROM_SQLITE", "0") or "0").strip().lower() in ["1", "true", "yes", "on"]
SQLITE_SYNC_INTERVAL_SEC = max(5, int(os.getenv("SQLITE_SYNC_INTERVAL_SEC", "5")))
MYSQL_CONNECTION_REQUIRED = (
    DB_PRIMARY == "mysql"
    or SQLITE_BOOTSTRAP_FROM_MYSQL
    or SQLITE_CONTINUOUS_SYNC_FROM_MYSQL
    or MYSQL_REVERSE_SYNC_FROM_SQLITE
)

USE_SQLITE = False
ACTIVE_DB_BACKEND = None
conn = None
cursor = None
mysql_conn = None
mysql_cursor = None
sqlite_conn = None
sqlite_cursor = None
sqlite_sync_lock = threading.Lock()
sqlite_sync_thread_started = False


def _to_bool_env(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ["1", "true", "yes", "on"]


INTERNAL_API_AUTOSTART = _to_bool_env(os.getenv("INTERNAL_API_AUTOSTART"), True)
INTERNAL_API_SYNC_ON_ALERT_REQUEST = _to_bool_env(os.getenv("INTERNAL_API_SYNC_ON_ALERT_REQUEST"), True)
INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS = max(
    5, int((os.getenv("INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS") or "300").strip() or "300")
)
INTERNAL_API_START_TIMEOUT_SECONDS = max(
    5, int((os.getenv("INTERNAL_API_START_TIMEOUT_SECONDS") or "20").strip() or "20")
)
INTERNAL_API_AUTOSTART_LOG = os.getenv("INTERNAL_API_AUTOSTART_LOG", os.path.join(tempfile.gettempdir(), "internal_api_autostart.log"))

_internal_api_process = None
_internal_api_started_by_main = False
_internal_api_log_handle = None
_internal_api_sync_lock = threading.Lock()
_internal_api_last_sync_monotonic = 0.0
_internal_api_last_sync_attempt_utc = None
_internal_api_last_sync_success_utc = None


def _internal_api_alerts_url():
    return (os.getenv("INTERNAL_ALERTS_API_URL") or "http://127.0.0.1:5100/api/alerts").strip()


def _internal_api_base_url():
    alerts_url = _internal_api_alerts_url()
    parsed = urlparse(alerts_url)

    if not parsed.scheme or not parsed.netloc:
        return "http://127.0.0.1:5100"

    path = parsed.path or ""
    if "/api/" in path:
        prefix = path.split("/api/", 1)[0]
    else:
        prefix = path.rsplit("/", 1)[0] if "/" in path else ""

    prefix = prefix.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{prefix}"


def _internal_api_health_url():
    return f"{_internal_api_base_url()}/health"


def _internal_api_sync_url():
    return f"{_internal_api_base_url()}/api/sync"


def _internal_api_auth_headers():
    key = (os.getenv("INTERNAL_ALERTS_API_KEY") or "").strip()
    header = (os.getenv("INTERNAL_ALERTS_API_KEY_HEADER") or "X-Internal-API-Key").strip() or "X-Internal-API-Key"
    return {header: key} if key else {}


def _internal_api_is_healthy(timeout_seconds=2):
    try:
        response = requests.get(_internal_api_health_url(), timeout=timeout_seconds)
        return response.status_code == 200
    except Exception:
        return False


def _internal_api_workdir():
    configured = (os.getenv("INTERNAL_API_DIR") or "").strip()
    if configured and os.path.isdir(configured):
        return configured

    base_dir = os.path.dirname(os.path.abspath(__file__))
    sibling = os.path.abspath(os.path.join(base_dir, "..", "internal api"))
    if os.path.isdir(sibling):
        return sibling
    return None


def _internal_api_python_bin(workdir):
    # Cross-platform: Windows uses Scripts, Linux uses bin
    win_venv_python = os.path.join(workdir, ".venv", "Scripts", "python.exe")
    unix_venv_python = os.path.join(workdir, ".venv", "bin", "python")
    if os.path.isfile(win_venv_python):
        return win_venv_python
    if os.path.isfile(unix_venv_python):
        return unix_venv_python
    # Fallback to system python
    return "python"


def _stop_internal_api_started_by_main():
    global _internal_api_process, _internal_api_log_handle

    if _internal_api_started_by_main and _internal_api_process and _internal_api_process.poll() is None:
        try:
            _internal_api_process.terminate()
            _internal_api_process.wait(timeout=5)
        except Exception:
            try:
                _internal_api_process.kill()
            except Exception:
                pass

    if _internal_api_log_handle:
        try:
            _internal_api_log_handle.close()
        except Exception:
            pass
        _internal_api_log_handle = None


atexit.register(_stop_internal_api_started_by_main)


def ensure_internal_api_running():
    global _internal_api_process, _internal_api_started_by_main, _internal_api_log_handle

    if _internal_api_is_healthy():
        return True

    if not INTERNAL_API_AUTOSTART:
        return False

    workdir = _internal_api_workdir()
    if not workdir:
        print("⚠️ INTERNAL_API_AUTOSTART is enabled, but internal api folder was not found.")
        return False

    python_bin = _internal_api_python_bin(workdir)
    env = os.environ.copy()
    env.setdefault("ENABLE_SCHEDULER", "true")
    env.setdefault("RUN_SYNC_ON_STARTUP", "true")
    env.setdefault("POLL_INTERVAL_SECONDS", (os.getenv("INTERNAL_API_POLL_INTERVAL_SECONDS") or "300").strip() or "300")

    if _internal_api_log_handle is None:
        _internal_api_log_handle = open(INTERNAL_API_AUTOSTART_LOG, "a", encoding="utf-8")

    # Check if dependencies are installed
    req_path = os.path.join(workdir, "requirements.txt")
    try:
        import importlib.util
        spec = importlib.util.find_spec("sqlalchemy")
        if spec is None:
            raise ImportError
    except ImportError:
        print("\n[ERROR] Internal API dependencies not installed. Please run: pip install -r 'internal api/requirements.txt'\n")
        return False

    try:
        _internal_api_process = subprocess.Popen(
            [python_bin, "run.py"],
            cwd=workdir,
            env=env,
            stdout=_internal_api_log_handle,
            stderr=_internal_api_log_handle,
        )
        _internal_api_started_by_main = True
    except Exception as exc:
        print(f"⚠️ Failed to auto-start internal API: {exc}\n[HINT] Check if Python is installed and dependencies are present in 'internal api/.venv' or globally.")
        return False

    deadline = time_module.monotonic() + INTERNAL_API_START_TIMEOUT_SECONDS
    while time_module.monotonic() < deadline:
        if _internal_api_is_healthy(timeout_seconds=1):
            print("✅ Internal API auto-started and healthy")
            return True
        if _internal_api_process and _internal_api_process.poll() is not None:
            break
        time_module.sleep(0.4)

    return _internal_api_is_healthy(timeout_seconds=1)


def sync_internal_api_if_needed(force=False):
    global _internal_api_last_sync_monotonic, _internal_api_last_sync_attempt_utc, _internal_api_last_sync_success_utc

    if not INTERNAL_API_SYNC_ON_ALERT_REQUEST and not force:
        return

    now = time_module.monotonic()
    if not force and (now - _internal_api_last_sync_monotonic) < INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS:
        return

    if not _internal_api_sync_lock.acquire(blocking=False):
        return

    try:
        now = time_module.monotonic()
        if not force and (now - _internal_api_last_sync_monotonic) < INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS:
            return

        if not _internal_api_is_healthy(timeout_seconds=1):
            ensure_internal_api_running()
        if not _internal_api_is_healthy(timeout_seconds=2):
            return

        _internal_api_last_sync_attempt_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        _internal_api_last_sync_monotonic = time_module.monotonic()
        try:
            response = requests.post(
                _internal_api_sync_url(),
                headers=_internal_api_auth_headers(),
                timeout=15,
            )
            if response.status_code < 400:
                _internal_api_last_sync_success_utc = _internal_api_last_sync_attempt_utc
        except Exception:
            pass
    finally:
        _internal_api_sync_lock.release()


class DatabaseCursorProxy:
    def __init__(self, target_cursor, backend):
        self._target_cursor = target_cursor
        self._backend = backend

    def _normalize_query(self, query):
        if self._backend == "sqlite":
            return query.replace('%s', '?')
        return query

    def execute(self, query, params=None):
        normalized_query = self._normalize_query(query)
        if params is None:
            return self._target_cursor.execute(normalized_query)
        return self._target_cursor.execute(normalized_query, params)

    def executemany(self, query, seq_of_params):
        normalized_query = self._normalize_query(query)
        return self._target_cursor.executemany(normalized_query, seq_of_params)

    def __getattr__(self, item):
        return getattr(self._target_cursor, item)


class DatabaseConnectionProxy:
    def __init__(self, target_conn, backend):
        self._target_conn = target_conn
        self._backend = backend

    def commit(self):
        return self._target_conn.commit()

    def rollback(self):
        return self._target_conn.rollback()

    def close(self):
        return self._target_conn.close()

    def cursor(self):
        return DatabaseCursorProxy(self._target_conn.cursor(), self._backend)

    def __getattr__(self, item):
        return getattr(self._target_conn, item)


def connect_mysql():
    global mysql_conn, mysql_cursor

    try:
        import mysql.connector
    except ImportError:
        print("⚠️ MySQL connector not available")
        return

    if not db_host or not db_user or not db_name:
        print("⚠️ MySQL config incomplete. Set DB_HOST, DB_USER and DB_NAME to enable MySQL.")
        return

    try:
        mysql_conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            use_pure=MYSQL_USE_PURE
        )
        mysql_cursor = mysql_conn.cursor()
        mode = "pure" if MYSQL_USE_PURE else "c-ext"
        print(f"✅ MySQL connected ({mode})")
    except Exception as err:
        mysql_conn = None
        mysql_cursor = None
        print(f"❌ MySQL connection failed: {err}")


def connect_sqlite():
    global sqlite_conn, sqlite_cursor

    try:
        sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("PRAGMA journal_mode=WAL")
        sqlite_cursor.execute("PRAGMA synchronous=NORMAL")
        print(f"✅ SQLite connected ({DB_PATH})")
    except Exception as err:
        sqlite_conn = None
        sqlite_cursor = None
        print(f"❌ SQLite connection failed: {err}")


def select_active_database():
    global conn, cursor, USE_SQLITE, ACTIVE_DB_BACKEND

    selected_backend = None
    selected_conn = None
    selected_cursor = None

    if DB_PRIMARY == "mysql":
        if mysql_conn and mysql_cursor:
            selected_backend = "mysql"
            selected_conn = mysql_conn
            selected_cursor = mysql_cursor
        elif sqlite_conn and sqlite_cursor:
            selected_backend = "sqlite"
            selected_conn = sqlite_conn
            selected_cursor = sqlite_cursor
    else:
        if sqlite_conn and sqlite_cursor:
            selected_backend = "sqlite"
            selected_conn = sqlite_conn
            selected_cursor = sqlite_cursor
        elif mysql_conn and mysql_cursor:
            selected_backend = "mysql"
            selected_conn = mysql_conn
            selected_cursor = mysql_cursor

    if not selected_conn or not selected_cursor:
        conn = None
        cursor = None
        USE_SQLITE = False
        ACTIVE_DB_BACKEND = None
        print("❌ No database connection available")
        return

    conn = DatabaseConnectionProxy(selected_conn, selected_backend)
    cursor = DatabaseCursorProxy(selected_cursor, selected_backend)
    USE_SQLITE = selected_backend == "sqlite"
    ACTIVE_DB_BACKEND = selected_backend
    print(f"✅ Active database: {selected_backend.upper()} (PRIMARY_DB={DB_PRIMARY})")


if MYSQL_CONNECTION_REQUIRED:
    connect_mysql()
connect_sqlite()
select_active_database()

app=Flask(__name__) #create name of Flask app which is name here
app.config['PREFERRED_URL_SCHEME'] = os.getenv('APP_URL_SCHEME', 'http')

# Initialize database tables
def _create_tables_for_backend(current_conn, current_cursor, backend):
    if backend == "sqlite":
        create_users_table = """
        CREATE TABLE IF NOT EXISTS Users (
            User_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name VARCHAR(100) NOT NULL,
            username VARCHAR(30) UNIQUE NOT NULL,
            email_id VARCHAR(100) UNIQUE NOT NULL,
            is_blocked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            password_hash VARCHAR(255) NOT NULL,
            role TEXT DEFAULT 'USER' CHECK(role IN ('ADMIN', 'USER')),
            phone VARCHAR(10)
        );
        """

        create_disasters_table = """
        CREATE TABLE IF NOT EXISTS Disasters (
            Disaster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            verify_status BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            media BLOB,
            media_type TEXT CHECK(media_type IN ('video','image')),
            reporter_id INTEGER NOT NULL,
            admin_id INTEGER,
            disaster_type VARCHAR(100) NOT NULL,
            description TEXT,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            address_text VARCHAR(255),
            FOREIGN KEY (reporter_id) REFERENCES Users(User_id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES Users(User_id) ON DELETE SET NULL
        );
        """
    else:
        create_users_table = """
        CREATE TABLE IF NOT EXISTS Users (
            User_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            username VARCHAR(30) UNIQUE NOT NULL,
            email_id VARCHAR(100) UNIQUE NOT NULL,
            is_blocked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('ADMIN', 'USER') DEFAULT 'USER',
            phone VARCHAR(10)
        );
        """

        create_disasters_table = """
        CREATE TABLE IF NOT EXISTS Disasters (
            Disaster_id INT AUTO_INCREMENT PRIMARY KEY,
            verify_status BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            media LONGBLOB,
            media_type ENUM('video','image'),
            reporter_id INT NOT NULL,
            admin_id INT NULL,
            disaster_type VARCHAR(100) NOT NULL,
            description TEXT,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            address_text VARCHAR(255),
            FOREIGN KEY (reporter_id) REFERENCES Users(User_id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES Users(User_id) ON DELETE SET NULL
        );
        """

    current_cursor.execute(create_users_table)
    current_cursor.execute(create_disasters_table)
    current_conn.commit()


def init_database():
    """Create Users and Disasters tables for all connected backends"""
    backends = [
        ("mysql", mysql_conn, mysql_cursor),
        ("sqlite", sqlite_conn, sqlite_cursor),
    ]

    initialized_any = False
    for backend_name, backend_conn, backend_cursor in backends:
        if not backend_conn or not backend_cursor:
            continue
        try:
            _create_tables_for_backend(backend_conn, backend_cursor, backend_name)
            print(f"✅ Tables initialized ({backend_name.upper()})")
            initialized_any = True
        except Exception as err:
            print(f"❌ Error initializing {backend_name.upper()} tables: {err}")

    if not initialized_any:
        print("❌ Database connection not available")


def bootstrap_sqlite_from_mysql_if_empty():
    """Seed SQLite from MySQL one time when SQLite has no data."""
    if not mysql_conn or not mysql_cursor or not sqlite_conn or not sqlite_cursor:
        return

    try:
        sqlite_cursor.execute("SELECT COUNT(*) FROM Users")
        sqlite_users = sqlite_cursor.fetchone()[0]
        sqlite_cursor.execute("SELECT COUNT(*) FROM Disasters")
        sqlite_disasters = sqlite_cursor.fetchone()[0]

        if sqlite_users > 0 or sqlite_disasters > 0:
            return

        mysql_cursor.execute("SELECT COUNT(*) FROM Users")
        mysql_users = mysql_cursor.fetchone()[0]
        mysql_cursor.execute("SELECT COUNT(*) FROM Disasters")
        mysql_disasters = mysql_cursor.fetchone()[0]

        if mysql_users == 0 and mysql_disasters == 0:
            return

        mysql_cursor.execute(
            """
            SELECT User_id, full_name, username, email_id, is_blocked, created_at, password_hash, role, phone
            FROM Users
            """
        )
        users_rows = mysql_cursor.fetchall()
        if users_rows:
            sqlite_cursor.executemany(
                """
                INSERT OR REPLACE INTO Users
                (User_id, full_name, username, email_id, is_blocked, created_at, password_hash, role, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                users_rows
            )

        mysql_cursor.execute(
            """
            SELECT Disaster_id, verify_status, created_at, media, media_type, reporter_id, admin_id,
                   disaster_type, description, latitude, longitude, address_text
            FROM Disasters
            """
        )
        disaster_rows = mysql_cursor.fetchall()
        if disaster_rows:
            sqlite_cursor.executemany(
                """
                INSERT OR REPLACE INTO Disasters
                (Disaster_id, verify_status, created_at, media, media_type, reporter_id, admin_id,
                 disaster_type, description, latitude, longitude, address_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                disaster_rows
            )

        sqlite_conn.commit()
        print(f"✅ SQLite bootstrap complete (users={len(users_rows)}, disasters={len(disaster_rows)})")
    except Exception as err:
        print(f"⚠️ SQLite bootstrap skipped: {err}")


def _normalize_value_for_sqlite(value):
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=' ')
    return value


def _normalize_value_for_mysql(value):
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


def sync_mysql_to_sqlite(force=False):
    """Mirror users + disasters from MySQL into SQLite."""
    if not mysql_conn or not mysql_cursor or not sqlite_conn:
        return False

    acquired = sqlite_sync_lock.acquire(blocking=force)
    if not acquired:
        return False

    try:
        mysql_cur = mysql_conn.cursor()
        sqlite_cur = sqlite_conn.cursor()

        mysql_cur.execute(
            """
            SELECT User_id, full_name, username, email_id, is_blocked, created_at, password_hash, role, phone
            FROM Users
            ORDER BY User_id
            """
        )
        users_rows = [tuple(_normalize_value_for_sqlite(v) for v in row) for row in mysql_cur.fetchall()]

        mysql_cur.execute(
            """
            SELECT Disaster_id, verify_status, created_at, media, media_type, reporter_id, admin_id,
                   disaster_type, description, latitude, longitude, address_text
            FROM Disasters
            ORDER BY Disaster_id
            """
        )
        disaster_rows = [tuple(_normalize_value_for_sqlite(v) for v in row) for row in mysql_cur.fetchall()]

        sqlite_cur.execute("BEGIN IMMEDIATE")
        sqlite_cur.execute("DELETE FROM Disasters")
        sqlite_cur.execute("DELETE FROM Users")

        if users_rows:
            sqlite_cur.executemany(
                """
                INSERT OR REPLACE INTO Users
                (User_id, full_name, username, email_id, is_blocked, created_at, password_hash, role, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                users_rows
            )

        if disaster_rows:
            sqlite_cur.executemany(
                """
                INSERT OR REPLACE INTO Disasters
                (Disaster_id, verify_status, created_at, media, media_type, reporter_id, admin_id,
                 disaster_type, description, latitude, longitude, address_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                disaster_rows
            )

        sqlite_conn.commit()
        print(f"🔄 SQLite sync complete (users={len(users_rows)}, disasters={len(disaster_rows)})")
        return True
    except Exception as err:
        try:
            sqlite_conn.rollback()
        except Exception:
            pass
        print(f"⚠️ SQLite sync failed: {err}")
        return False
    finally:
        sqlite_sync_lock.release()


def sync_sqlite_to_mysql(force=False):
    """Mirror users + disasters from SQLite into MySQL."""
    global mysql_conn, mysql_cursor

    if not sqlite_conn:
        return False

    if not mysql_conn or not mysql_cursor:
        connect_mysql()

    if not mysql_conn or not mysql_cursor:
        return False

    acquired = sqlite_sync_lock.acquire(blocking=force)
    if not acquired:
        return False

    try:
        sqlite_cur = sqlite_conn.cursor()
        mysql_cur = mysql_conn.cursor()

        sqlite_cur.execute(
            """
            SELECT User_id, full_name, username, email_id, is_blocked, created_at, password_hash, role, phone
            FROM Users
            ORDER BY User_id
            """
        )
        users_rows = [tuple(_normalize_value_for_mysql(v) for v in row) for row in sqlite_cur.fetchall()]

        sqlite_cur.execute(
            """
            SELECT Disaster_id, verify_status, created_at, media, media_type, reporter_id, admin_id,
                   disaster_type, description, latitude, longitude, address_text
            FROM Disasters
            ORDER BY Disaster_id
            """
        )
        disaster_rows = [tuple(_normalize_value_for_mysql(v) for v in row) for row in sqlite_cur.fetchall()]

        mysql_cur.execute("SET FOREIGN_KEY_CHECKS=0")
        mysql_cur.execute("DELETE FROM Disasters")
        mysql_cur.execute("DELETE FROM Users")

        if users_rows:
            mysql_cur.executemany(
                """
                INSERT INTO Users
                (User_id, full_name, username, email_id, is_blocked, created_at, password_hash, role, phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                users_rows
            )

        if disaster_rows:
            mysql_cur.executemany(
                """
                INSERT INTO Disasters
                (Disaster_id, verify_status, created_at, media, media_type, reporter_id, admin_id,
                 disaster_type, description, latitude, longitude, address_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                disaster_rows
            )

        mysql_cur.execute("SET FOREIGN_KEY_CHECKS=1")
        mysql_conn.commit()
        print(f"🔄 MySQL reverse sync complete (users={len(users_rows)}, disasters={len(disaster_rows)})")
        return True
    except Exception as err:
        try:
            mysql_conn.rollback()
        except Exception:
            pass
        mysql_conn = None
        mysql_cursor = None
        print(f"⚠️ MySQL reverse sync failed: {err}")
        return False
    finally:
        sqlite_sync_lock.release()


def _sqlite_sync_loop():
    while True:
        try:
            if SQLITE_CONTINUOUS_SYNC_FROM_MYSQL and ACTIVE_DB_BACKEND == "mysql":
                sync_mysql_to_sqlite(force=False)
            elif MYSQL_REVERSE_SYNC_FROM_SQLITE and ACTIVE_DB_BACKEND == "sqlite":
                reverse_ok = sync_sqlite_to_mysql(force=False)
                if reverse_ok and DB_PRIMARY == "mysql":
                    select_active_database()
        except Exception as err:
            print(f"⚠️ SQLite sync loop error: {err}")
        time_module.sleep(SQLITE_SYNC_INTERVAL_SEC)


def start_sqlite_sync_worker():
    global sqlite_sync_thread_started
    if sqlite_sync_thread_started:
        return
    if not (SQLITE_CONTINUOUS_SYNC_FROM_MYSQL or MYSQL_REVERSE_SYNC_FROM_SQLITE):
        return
    sqlite_sync_thread_started = True
    threading.Thread(target=_sqlite_sync_loop, daemon=True, name='sqlite-sync-worker').start()
    print(f"✅ DB sync worker started (interval={SQLITE_SYNC_INTERVAL_SEC}s)")

# Initialize database on startup
if cursor:
    init_database()
    if SQLITE_BOOTSTRAP_FROM_MYSQL:
        bootstrap_sqlite_from_mysql_if_empty()
    if SQLITE_CONTINUOUS_SYNC_FROM_MYSQL and ACTIVE_DB_BACKEND == "mysql":
        sync_mysql_to_sqlite(force=True)
    elif MYSQL_REVERSE_SYNC_FROM_SQLITE and ACTIVE_DB_BACKEND == "sqlite":
        sync_sqlite_to_mysql(force=True)
    if SQLITE_CONTINUOUS_SYNC_FROM_MYSQL or MYSQL_REVERSE_SYNC_FROM_SQLITE:
        start_sqlite_sync_worker()
    select_active_database()

app.secret_key = os.getenv('SECRET_KEY')


def _check_mysql_health(reconnect=False):
    if not mysql_conn:
        return False, "not_connected"
    try:
        mysql_conn.ping(reconnect=reconnect, attempts=1, delay=0)
        return True, "ok"
    except Exception as err:
        return False, str(err)


def _check_sqlite_health():
    if not sqlite_conn:
        return False, "not_connected"
    try:
        sqlite_conn.execute("SELECT 1")
        return True, "ok"
    except Exception as err:
        return False, str(err)


@app.route('/health/db', methods=['GET'])
def db_health():
    global mysql_conn, mysql_cursor

    mysql_ok, mysql_detail = _check_mysql_health(reconnect=False)
    sqlite_ok, sqlite_detail = _check_sqlite_health()

    if ACTIVE_DB_BACKEND == "mysql" and (not mysql_ok) and sqlite_ok:
        mysql_conn = None
        mysql_cursor = None
        select_active_database()

    status_payload = {
        "success": True,
        "primary_db": DB_PRIMARY,
        "active_db": ACTIVE_DB_BACKEND,
        "databases": {
            "mysql": {
                "connected": mysql_ok,
                "detail": mysql_detail,
            },
            "sqlite": {
                "connected": sqlite_ok,
                "detail": sqlite_detail,
                "path": DB_PATH,
            }
        }
    }

    http_status = 200 if (mysql_ok or sqlite_ok) else 503
    return jsonify(status_payload), http_status


# this will be used in forecasting open meteor api

def _is_mysql_connection_error(err):
    text = str(err or '').lower()
    return any(token in text for token in [
        '2013',
        '2006',
        '2055',
        'lost connection',
        'server has gone away',
        'connection not available',
        'closed',
        'ssl connection error',
        'wrong version number'
    ])


def _ensure_read_backend_ready():
    global mysql_conn, mysql_cursor

    if not cursor:
        select_active_database()

    if ACTIVE_DB_BACKEND != "mysql":
        return

    mysql_ok, _ = _check_mysql_health(reconnect=False)
    if mysql_ok:
        return

    if sqlite_conn and sqlite_cursor:
        print("⚠️ MySQL unavailable for reads. Switching active backend to SQLITE.")
        mysql_conn = None
        mysql_cursor = None
        select_active_database()


def _recover_after_mysql_failure():
    global mysql_conn, mysql_cursor

    recovered = False

    try:
        if mysql_conn:
            mysql_conn.ping(reconnect=True, attempts=1, delay=0)
            mysql_cursor = mysql_conn.cursor()
            recovered = True
    except Exception:
        recovered = False

    if not recovered:
        connect_mysql()
        recovered = bool(mysql_conn and mysql_cursor)

    if not recovered:
        mysql_conn = None
        mysql_cursor = None

    select_active_database()
    return bool(cursor)

def execute_query(query, params=None):
    """Execute query using the active backend"""
    global cursor
    _ensure_read_backend_ready()
    if not cursor:
        return None

    def _run_query_once():
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    try:
        return _run_query_once()
    except Exception as e:
        if ACTIVE_DB_BACKEND == "mysql" and _is_mysql_connection_error(e):
            print(f"⚠️ MySQL query failed, attempting recovery: {e}")
            if _recover_after_mysql_failure():
                try:
                    return _run_query_once()
                except Exception as retry_err:
                    print(f"Query retry error: {retry_err}")
                    return None
        print(f"Query error: {e}")
        return None

def fetch_one(query, params=None):
    """Fetch one result"""
    result_cursor = execute_query(query, params)
    if result_cursor:
        return result_cursor.fetchone()
    return None

def fetch_all(query, params=None):
    """Fetch all results"""
    result_cursor = execute_query(query, params)
    if result_cursor:
        return result_cursor.fetchall()
    return []

def execute_update(query, params=None):
    """Execute update/insert/delete"""
    result_cursor = execute_query(query, params)
    if result_cursor and conn:
        conn.commit()
        if SQLITE_CONTINUOUS_SYNC_FROM_MYSQL and ACTIVE_DB_BACKEND == "mysql":
            sync_mysql_to_sqlite(force=False)
        elif MYSQL_REVERSE_SYNC_FROM_SQLITE and ACTIVE_DB_BACKEND == "sqlite":
            sync_sqlite_to_mysql(force=False)

def fetch_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    response = requests.get(url)
    return response.json()

def generate_radius_points(lat, lon, radius_km=100):
    # Degrees of latitude per km (approx 111)
    delta_lat = radius_km / 111
    # Degrees of longitude per km varies based on latitude
    delta_lon = radius_km / (111 * math.cos(math.radians(lat)))

    return [
        (lat, lon),
        (lat + delta_lat, lon),
        (lat - delta_lat, lon),
        (lat, lon + delta_lon),
        (lat, lon - delta_lon)
    ]


def haversine_distance_km(lat1, lon1, lat2, lon2):
    radius_earth_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_earth_km * c


def estimate_duration_text(distance_km, avg_speed_kmph=30):
    if distance_km <= 0:
        return 2, "2 min"

    minutes = max(2, int(round((distance_km / avg_speed_kmph) * 60)))
    if minutes >= 60:
        hours = minutes // 60
        rem_minutes = minutes % 60
        if rem_minutes == 0:
            return minutes, f"{hours} hr"
        return minutes, f"{hours} hr {rem_minutes} min"
    return minutes, f"{minutes} min"

# this will be used to get location of the user from the ip address using ip api

def get_location_by_ip():
    # In local development, '127.0.0.1' won't work. 
    # We use an external service to get the public IP or a test IP.
    try:
        # This API returns JSON with lat, lon, city, etc.
        response = requests.get('http://ip-api.com/json/')
        data = response.json()
        
        if data['status'] == 'success':
            return data['lat'], data['lon']
    except Exception as e:
        print(f"Error getting location: {e}")
    
    return None, None



# Load NGO contact database
def load_ngo_contacts():
    try:
        with open('ngos_contacts.json', 'r') as f:
            data = json.load(f)
            return {ngo['name']: ngo for ngo in data['ngo_contacts']}
    except FileNotFoundError:
        return {}


def normalize_org_name(name):
    value = str(name or '').strip().lower()
    cleaned = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in value)
    return ' '.join(cleaned.split())


def pick_first_value(*values, fallback='Not available'):
    for item in values:
        text = str(item or '').strip()
        if text and text.lower() not in ['not available', 'na', 'n/a', 'none', '-']:
            return text
    return fallback

  
oauth = OAuth(app) if OAuth is not None else None
google = None
if oauth is not None:
    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile' # This tells Google WHAT info to give us
        }
    )
else:
    print(f"⚠️ Google OAuth disabled: {AUTHLIB_IMPORT_ERROR}")


def get_google_redirect_uri():
    explicit_uri = str(os.getenv('GOOGLE_REDIRECT_URI', '') or '').strip()
    if explicit_uri:
        return explicit_uri
    return url_for('authorize', _external=True).replace('/oauth2callback', '/auth/callback').replace('/oauth2/callback', '/auth/callback')

@app.route("/") #the route made for the port 5000
def index():
    return redirect(url_for('mobile_home'))



@app.route("/login",methods=['GET','POST'])

 #route for the port 5000/login
# there are two http methods-> get and post 
# here we need to take the input in the login form from user so the method is POST 
# by default if not mentioned route takes GET method 
# GET method is used to fetch and show data to user


def login():
    # this method checks user credentials and redirects them appropriately
    msg = request.args.get('msg','')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        record = fetch_one("select * from users where username=%s and password_hash=%s", (username, password))
        if record:
            # populate session values
            session['username'] = username
            session['user_id'] = record[0]
            session['role'] = record[7]

            # block check comes first
            if record[4] == True:
                msg = 'Your account is blocked. Contact support.'
                session.clear()
                return render_template("login.html", msg=msg)

            # hard‑coded admin override email
            if record[3] == "ayaansaifi2005@gmail.com":
                session['role'] = 'ADMIN'

            # go to home which will respect role and route correctly
            return redirect(url_for('home'))
        else:
            msg = 'Wrong Credentials, Try Again.'

    return render_template("login.html", msg=msg)

# @app.route('/auth/callback')
# def authorize():
#     # 1. Get user info from Google
#     token = google.authorize_access_token()
#     user_info = token.get('userinfo')
    
#     email = user_info['email']
#     name = user_info['name']
    
#     # 2. Check if this email already exists in our database
#     # Note: Using %s because your helper function handles the conversion
#     query = "SELECT username, password_hash FROM users WHERE email_id = %s"
#     result = fetch_one(query, (email,))

#     if result:
#         # Scenario 1: Existing User
#         # result[0] is username, result[1] is password_hash
#         session['user'] = {
#             'email': email,
#             'name': name,
#             'username': result[0]
#         }
#     else:
#         # Scenario 2: New User (Signup)
#         # We fetch details from Google and insert them into our DB
#         insert_query = "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)"
#         # Since it's a Google login, we might leave password_hash as 'GOOGLE_AUTH'
#         execute_update(insert_query, (name, email, 'GOOGLE_AUTH'))
        
#         session['user'] = {
#             'email': email,
#             'name': name,
#             'username': name
#         }

#     return render_template("admin.html", user_info=session.get('user')) # Or wherever you want them to go



@app.route('/auth/callback')
@app.route('/oauth2/callback')
@app.route('/oauth2callback')
def authorize():
    if google is None:
        return redirect(url_for('login', msg='Google login is temporarily unavailable. Please use username/password.'))

    # 1. Get user info from Google
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    email = user_info['email']
    name = user_info['name']
    
    # 2. Check if this email already exists in our database
    # Note: Using %s because your helper function handles the conversion
    query = "SELECT user_id, username, phone, role, is_blocked, full_name, email_id FROM users WHERE email_id = %s"
    result = fetch_one(query, (email,))

    if result:
        # Scenario 1: Existing User
        user_id = result[0]
        username = result[1]
        phone = result[2]
        role = result[3]
        is_blocked = bool(result[4])

        session['user'] = {
            'email': email,
            'name': result[5] or name,
            'username': username,
            'phone': phone,
            'role': role,
            'user_id': user_id,
            'is_blocked': is_blocked
        }
        # mirror top‑level session fields for compatibility with other routes
        session['username'] = session['user']['username']
        session['user_id'] = session['user']['user_id']
        session['role'] = session['user']['role']
        session['is_blocked'] = session['user']['is_blocked']
        # special email override
        if email == "ayaansaifi2005@gmail.com":
            session['role'] = 'ADMIN'
            session['user']['role'] = 'ADMIN'
    else:
        # Scenario 2: New User (Signup)
        return render_template('signup.html', user_info={
            'name': name,
            'email_id': email
        })  # Redirect to a signup page where they can set a username and other details

    if session['user']['is_blocked']:
        msg = 'Your account is blocked. Contact support.'
        session.clear()
        return render_template('login.html', msg=msg)

    # always go to /home; that route will dispatch based on role
    return redirect(url_for('home'))

@app.route('/login/google')
def login_google():
    if google is None:
        return redirect(url_for('login', msg='Google login is temporarily unavailable. Please use username/password.'))

      
    # This creates the URL for our 'authorize' callback function
    redirect_uri = get_google_redirect_uri()
    # This sends the user to Google
    return google.authorize_redirect(redirect_uri)
    # return redirect(url_for('login', msg='Google login is not configured yet. Please login using username and password.'))


@app.route("/home") 
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'ADMIN':
        return render_template("admin.html", username=session.get('username'))
    return redirect(url_for('mobile_home'))


@app.route('/admin')
def admin_panel():
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return redirect(url_for('login'))
    return render_template("admin.html", username=session.get('username'))


@app.route('/admin/user-view')
def admin_user_view():
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return redirect(url_for('login'))
    return render_template("admin.html", username=session.get('username'))


@app.route('/mobile')
def mobile_landing():
    return redirect(url_for('mobile_home'))


@app.route('/mobile/home')
def mobile_home():
    is_logged_in = 'user_id' in session
    is_admin = is_logged_in and session.get('role') == 'ADMIN'
    profile = None
    profile_msg = (request.args.get('profile_msg') or '').strip()
    profile_msg_type = (request.args.get('profile_msg_type') or '').strip().lower()
    open_profile = (request.args.get('open_profile') or '').strip() == '1'

    if is_logged_in:
        user = fetch_one(
            "SELECT full_name, username, email_id, phone, role FROM users WHERE user_id=%s",
            (session.get('user_id'),)
        )
        if user:
            username_value = str(user[1]) if user[1] else ''
            if len(username_value) <= 2:
                masked_username = username_value[:1] + ('*' if len(username_value) == 2 else '')
            else:
                masked_username = username_value[0] + ('*' * (len(username_value) - 2)) + username_value[-1]

            profile = {
                'full_name': user[0],
                'name': user[0],
                'username': user[1],
                'email': user[2],
                'phone': user[3],
                'account_type': user[4],
                'masked_username': masked_username
            }

    return render_template(
        'home_mobile.html',
        username=session.get('username'),
        is_logged_in=is_logged_in,
        is_admin=is_admin,
        profile=profile,
        profile_msg=profile_msg,
        profile_msg_type=profile_msg_type,
        open_profile=open_profile
    )


@app.route('/mobile/profile/update', methods=['POST'])
def mobile_profile_update():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    username = (request.form.get('username') or '').strip()
    phone = (request.form.get('phone') or '').strip()

    if not username:
        return redirect(url_for(
            'mobile_home',
            open_profile='1',
            profile_msg='Username is required.',
            profile_msg_type='error'
        ))

    current_user = fetch_one(
        "SELECT user_id FROM users WHERE user_id=%s",
        (user_id,)
    )
    if not current_user:
        session.clear()
        return redirect(url_for('login'))

    existing = fetch_one(
        "SELECT user_id FROM users WHERE username=%s AND user_id <> %s",
        (username, user_id)
    )
    if existing:
        return redirect(url_for(
            'mobile_home',
            open_profile='1',
            profile_msg='Username already in use.',
            profile_msg_type='error'
        ))

    try:
        execute_update(
            "UPDATE users SET username=%s, phone=%s WHERE user_id=%s",
            (username, phone, user_id)
        )

        session['username'] = username
        if isinstance(session.get('user'), dict):
            session['user']['username'] = username
            session['user']['phone'] = phone

        return redirect(url_for(
            'mobile_home',
            open_profile='1',
            profile_msg='Profile updated successfully.',
            profile_msg_type='success'
        ))
    except Exception:
        return redirect(url_for(
            'mobile_home',
            open_profile='1',
            profile_msg='Unable to update profile right now.',
            profile_msg_type='error'
        ))


@app.route('/mobile/details')
def mobile_details():
    return render_template('details_mobile.html', username=session.get('username'))


@app.route('/mobile/alerts')
def mobile_alerts():
    return render_template('alerts_mobile.html', username=session.get('username'))


@app.route('/mobile/sos')
def mobile_sos():
    return render_template('sos_mobile.html', username=session.get('username'))


@app.route('/mobile/sos-basic')
def mobile_sos_basic():
    return render_template('sos_basic.html', username=session.get('username'))


def _mobile_sos_apk_path():
    return os.path.join(
        app.root_path,
        'native-sos-wrapper',
        'android',
        'app',
        'build',
        'outputs',
        'apk',
        'debug',
        'app-debug.apk'
    )


def _mobile_sos_apk_archive_dir():
    return os.path.join(app.root_path, 'apk_history')


def _mobile_sos_apk_checksum(apk_path):
    hasher = hashlib.sha256()
    with open(apk_path, 'rb') as apk_file:
        for chunk in iter(lambda: apk_file.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def _mobile_sos_archive_current_apk(apk_path):
    if not os.path.isfile(apk_path):
        return None

    try:
        current_checksum = _mobile_sos_apk_checksum(apk_path)
    except OSError:
        return None

    archive_dir = _mobile_sos_apk_archive_dir()
    try:
        os.makedirs(archive_dir, exist_ok=True)
    except OSError:
        return None

    try:
        for entry in os.listdir(archive_dir):
            if not entry.lower().endswith('.apk'):
                continue
            existing_path = os.path.join(archive_dir, entry)
            if not os.path.isfile(existing_path):
                continue
            try:
                if _mobile_sos_apk_checksum(existing_path) == current_checksum:
                    return current_checksum
            except OSError:
                continue
    except OSError:
        return current_checksum

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = f'projectz-sos-{stamp}-{current_checksum[:8]}.apk'
    archive_path = os.path.join(archive_dir, archive_name)
    try:
        shutil.copy2(apk_path, archive_path)
    except OSError:
        return current_checksum

    return current_checksum


def _mobile_sos_list_archived_apks(exclude_checksum=None):
    archive_dir = _mobile_sos_apk_archive_dir()
    if not os.path.isdir(archive_dir):
        return []

    versions = []
    try:
        apk_files = [name for name in os.listdir(archive_dir) if name.lower().endswith('.apk')]
    except OSError:
        return []

    for file_name in apk_files:
        file_path = os.path.join(archive_dir, file_name)
        if not os.path.isfile(file_path):
            continue

        try:
            checksum = _mobile_sos_apk_checksum(file_path)
        except OSError:
            checksum = None

        if exclude_checksum and checksum == exclude_checksum:
            continue

        try:
            size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        except OSError:
            size_mb = None

        try:
            updated_at = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
            updated_sort = os.path.getmtime(file_path)
        except OSError:
            updated_at = None
            updated_sort = 0

        versions.append({
            'file_name': file_name,
            'size_mb': size_mb,
            'updated_at': updated_at,
            'updated_sort': updated_sort,
            'download_url': url_for('mobile_sos_app_download_version', apk_filename=file_name)
        })

    versions.sort(key=lambda item: item['updated_sort'], reverse=True)
    return versions


def _mobile_sos_external_apk_url():
    value = (os.getenv('SOS_APP_EXTERNAL_APK_URL') or '').strip()
    return value or None


@app.route('/mobile/sos-app')
def mobile_sos_app_download_page():
    apk_path = _mobile_sos_apk_path()
    external_apk_url = _mobile_sos_external_apk_url()
    apk_exists = os.path.isfile(apk_path)
    latest_apk = None
    history_versions = []
    current_checksum = None
    if external_apk_url:
        apk_exists = True

    if apk_exists:
        if external_apk_url:
            latest_apk = {
                'title': 'Latest APK (External Host)',
                'size_mb': None,
                'updated_at': None,
                'download_url': external_apk_url,
                'source': 'external'
            }
        else:
            try:
                apk_size_mb = round(os.path.getsize(apk_path) / (1024 * 1024), 2)
            except OSError:
                apk_size_mb = None

            try:
                apk_updated_at = datetime.fromtimestamp(os.path.getmtime(apk_path)).strftime('%Y-%m-%d %H:%M')
            except OSError:
                apk_updated_at = None

            current_checksum = _mobile_sos_archive_current_apk(apk_path)
            latest_apk = {
                'title': 'Latest APK',
                'size_mb': apk_size_mb,
                'updated_at': apk_updated_at,
                'download_url': url_for('mobile_sos_app_download_apk'),
                'source': 'local'
            }

    history_versions = _mobile_sos_list_archived_apks(exclude_checksum=current_checksum)

    return render_template(
        'sos_app_download.html',
        username=session.get('username'),
        apk_exists=apk_exists,
        latest_apk=latest_apk,
        history_versions=history_versions,
        external_apk_url=external_apk_url,
        download_url=(external_apk_url or url_for('mobile_sos_app_download_apk'))
    )


@app.route('/mobile/sos-app/download')
def mobile_sos_app_download_apk():
    external_apk_url = _mobile_sos_external_apk_url()
    if external_apk_url:
        return redirect(external_apk_url)

    apk_path = _mobile_sos_apk_path()
    if not os.path.isfile(apk_path):
        abort(404)

    response = send_file(
        apk_path,
        mimetype='application/vnd.android.package-archive',
        as_attachment=True,
        download_name='projectz-sos.apk'
    )
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/mobile/sos-app/download/history/<path:apk_filename>')
def mobile_sos_app_download_version(apk_filename):
    safe_name = os.path.basename((apk_filename or '').strip())
    if not safe_name or safe_name != apk_filename or not safe_name.lower().endswith('.apk'):
        abort(404)

    file_path = os.path.join(_mobile_sos_apk_archive_dir(), safe_name)
    if not os.path.isfile(file_path):
        abort(404)

    response = send_file(
        file_path,
        mimetype='application/vnd.android.package-archive',
        as_attachment=True,
        download_name=safe_name
    )
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/mobile-sos-sw.js')
def mobile_sos_service_worker():
    sw_path = os.path.join(app.root_path, 'static', 'mobile-sos-sw.js')
    if not os.path.isfile(sw_path):
        abort(404)

    response = send_file(sw_path, mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Service-Worker-Allowed'] = '/mobile/'
    return response


@app.route('/mobile/manifest.json')
def mobile_sos_manifest():
    manifest_path = os.path.join(app.root_path, 'static', 'manifest-mobile-sos.json')
    if not os.path.isfile(manifest_path):
        abort(404)

    response = send_file(manifest_path, mimetype='application/manifest+json')
    response.headers['Cache-Control'] = 'no-cache'
    return response


def _ensure_sos_reporter_user_id():
    existing = fetch_one("SELECT user_id FROM users WHERE username=%s", ('offline_sos_bot',))
    if existing:
        return existing[0]

    execute_update(
        "INSERT INTO users (full_name, username, email_id, password_hash, role, phone) VALUES (%s, %s, %s, %s, %s, %s)",
        ('Offline SOS Bot', 'offline_sos_bot', 'offline_sos_bot@local.invalid', secrets.token_hex(16), 'USER', None)
    )
    created = fetch_one("SELECT user_id FROM users WHERE username=%s", ('offline_sos_bot',))
    if created:
        return created[0]
    return None


@app.route('/api/mobile/sos/payload', methods=['POST'])
def mobile_sos_payload():
    payload = request.get_json(silent=True) or {}

    disaster_type = str(payload.get('disaster_type') or 'Emergency').strip()[:100] or 'Emergency'
    description = str(payload.get('description') or '').strip()
    address_text = str(payload.get('address_text') or '').strip()
    latitude = payload.get('latitude')
    longitude = payload.get('longitude')

    if latitude is None or longitude is None:
        return jsonify({"success": False, "message": "latitude and longitude are required"}), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "invalid coordinates"}), 400

    reporter_id = session.get('user_id')
    if not reporter_id:
        reporter_id = _ensure_sos_reporter_user_id()
    if not reporter_id:
        return jsonify({"success": False, "message": "unable to allocate reporter"}), 500

    if not description:
        description = f"SOS request received via mobile app ({'offline-sync' if payload.get('queued_offline') else 'live'})"

    try:
        execute_update(
            """
            INSERT INTO Disasters
            (reporter_id, disaster_type, description, address_text, latitude, longitude, media_type, media, verify_status, admin_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (reporter_id, disaster_type, description, address_text, latitude, longitude, None, None, False, None)
        )
        return jsonify({"success": True, "message": "SOS payload accepted"})
    except Exception as err:
        return jsonify({"success": False, "message": str(err)}), 500


def _analysis_candidate_directories():
    external_module_root = '/Users/matrika/Downloads/ANALYSIS_MODULE'
    candidate_dirs = [
        os.path.join(external_module_root, 'DATA&GRAPHS'),
        os.path.join(external_module_root, 'DATA&GRAPHS1'),
        os.path.join(external_module_root, 'module2'),
        os.path.join(external_module_root, 'finalAI')
    ]

    normalized = []
    seen = set()
    for directory in candidate_dirs:
        real_dir = os.path.realpath(directory)
        if os.path.isdir(real_dir) and real_dir not in seen:
            seen.add(real_dir)
            normalized.append(real_dir)
    return normalized


def _analysis_encode_asset_id(file_path):
    encoded = base64.urlsafe_b64encode(file_path.encode('utf-8')).decode('ascii')
    return encoded.rstrip('=')


def _analysis_decode_asset_id(asset_id):
    try:
        padded = asset_id + ('=' * (-len(asset_id) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8')
        return decoded
    except Exception:
        return None


def _analysis_asset_title(filename):
    name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
    return ' '.join(word.capitalize() for word in name.split()) or filename


@app.route('/api/mobile/analysis/module-one')
def mobile_analysis_module_one_assets():
    allowed_extensions = {'.html', '.htm', '.png', '.jpg', '.jpeg', '.webp', '.svg'}
    excluded_filenames = {'emergency_priority_dashboard.html'}
    assets = []
    html_count = 0
    image_count = 0

    for directory in _analysis_candidate_directories():
        folder_name = os.path.basename(directory)
        for entry in sorted(os.listdir(directory)):
            full_path = os.path.join(directory, entry)
            if not os.path.isfile(full_path):
                continue

            if entry.strip().lower() in excluded_filenames:
                continue

            extension = os.path.splitext(entry)[1].lower()
            if extension not in allowed_extensions:
                continue

            asset_type = 'iframe' if extension in {'.html', '.htm'} else 'image'
            if asset_type == 'iframe':
                html_count += 1
            else:
                image_count += 1

            asset_id = _analysis_encode_asset_id(os.path.realpath(full_path))
            assets.append({
                'id': asset_id,
                'title': _analysis_asset_title(entry),
                'filename': entry,
                'type': asset_type,
                'folder': folder_name,
                'url': url_for('mobile_analysis_asset', asset_id=asset_id)
            })

    assets.sort(key=lambda item: (item['type'] != 'iframe', item['title'].lower()))
    message = 'Module One visualizations loaded.' if assets else 'No Module One visualizations found yet.'

    return jsonify({
        'count': len(assets),
        'html_count': html_count,
        'image_count': image_count,
        'directories': [os.path.basename(path) for path in _analysis_candidate_directories()],
        'assets': assets,
        'message': message
    })


@app.route('/mobile/analysis/asset/<path:asset_id>')
def mobile_analysis_asset(asset_id):
    decoded_path = _analysis_decode_asset_id(asset_id)
    if not decoded_path:
        abort(404)

    real_file_path = os.path.realpath(decoded_path)
    allowed_dirs = _analysis_candidate_directories()

    if not os.path.isfile(real_file_path):
        abort(404)

    if not any(os.path.commonpath([real_file_path, allowed_dir]) == allowed_dir for allowed_dir in allowed_dirs):
        abort(403)

    mime_type, _ = mimetypes.guess_type(real_file_path)
    return send_file(real_file_path, mimetype=mime_type)


@app.route('/mobile/analysis')
def mobile_analysis():
    return render_template('analysis_mobile.html', username=session.get('username'))


@app.route('/mobile/organization')
def mobile_organization():
    return render_template('organization_mobile.html', username=session.get('username'))


@app.route('/mobile/satellite')
def mobile_satellite():
    return render_template('satellite_mobile.html', username=session.get('username'))


@app.route('/mobile/admin')
def mobile_admin_panel():
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return redirect(url_for('login'))
    return render_template('admin_mobile.html', username=session.get('username'))


@app.route('/mobile/hill90')
def mobile_live_alerts_check():
    return render_template('live_alerts_check.html', username=session.get('username'))


@app.route('/mobile/live-alerts-check')
def mobile_live_alerts_check_legacy():
    return redirect(url_for('mobile_live_alerts_check'))


def _format_bytes(size_bytes):
    try:
        size = float(size_bytes)
    except (TypeError, ValueError):
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return "0 B"


def _parse_datetime_any(value):
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass

    for fmt in ['%a %b %d %H:%M:%S IST %Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _to_utc_iso(value):
    parsed = _parse_datetime_any(value)
    if not parsed:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_key_value_env(env_path):
    values = {}
    if not env_path or not os.path.isfile(env_path):
        return values

    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        return values
    return values


def _resolve_main_sqlite_path():
    if os.path.isabs(DB_PATH):
        return DB_PATH
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_dir, DB_PATH))


def _resolve_internal_api_sqlite_path():
    workdir = _internal_api_workdir()
    if not workdir:
        return None

    env_path = os.path.join(workdir, ".env")
    env_values = _read_key_value_env(env_path)

    database_url = str(env_values.get("DATABASE_URL", "")).strip()
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.replace("sqlite:///", "", 1).strip()
        if sqlite_path:
            if not os.path.isabs(sqlite_path):
                sqlite_path = os.path.abspath(os.path.join(workdir, sqlite_path))
            return sqlite_path

    db_path = str(env_values.get("DB_PATH", "database.db")).strip() or "database.db"
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(os.path.join(workdir, db_path))
    return db_path


def _file_stats(path):
    if not path:
        return {
            "path": None,
            "exists": False,
            "size_bytes": 0,
            "size_human": "0 B",
            "modified_at_utc": None
        }

    exists = os.path.isfile(path)
    size_bytes = os.path.getsize(path) if exists else 0
    modified_at = None
    if exists:
        modified_at = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "path": path,
        "exists": exists,
        "size_bytes": size_bytes,
        "size_human": _format_bytes(size_bytes),
        "modified_at_utc": modified_at
    }


def _sqlite_table_count(sqlite_path, table_name):
    if not sqlite_path or not os.path.isfile(sqlite_path):
        return None
    try:
        with sqlite3.connect(sqlite_path) as connection:
            cursor_obj = connection.cursor()
            cursor_obj.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor_obj.fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return None


def _latest_utc_from_values(values):
    latest_dt = None
    for value in values:
        parsed = _parse_datetime_any(value)
        if not parsed:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        if latest_dt is None or parsed > latest_dt:
            latest_dt = parsed
    if latest_dt is None:
        return None
    return latest_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@app.route('/api/mobile/hill90/diagnostics')
def mobile_hill90_diagnostics():
    internal_headers = _internal_api_auth_headers()
    internal_base_url = _internal_api_base_url()
    internal_healthy = _internal_api_is_healthy(timeout_seconds=2)

    source_runs = []
    source_runs_error = None
    latest_alert_item = None
    latest_alert_error = None

    if internal_healthy:
        try:
            response = requests.get(f"{internal_base_url}/api/sources/status", headers=internal_headers, timeout=8)
            response.raise_for_status()
            payload = response.json() if response.content else {}
            source_runs = payload.get("items", []) if isinstance(payload, dict) else []
        except Exception as exc:
            source_runs_error = str(exc)

        try:
            response = requests.get(_internal_api_alerts_url(), params={"limit": 1}, headers=internal_headers, timeout=8)
            response.raise_for_status()
            payload = response.json() if response.content else {}
            latest_items = payload.get("items", []) if isinstance(payload, dict) else []
            latest_alert_item = latest_items[0] if latest_items else None
        except Exception as exc:
            latest_alert_error = str(exc)
    else:
        source_runs_error = "internal_api_health_down"
        latest_alert_error = "internal_api_health_down"

    source_success_count = len([item for item in source_runs if str(item.get("last_status", "")).upper() == "SUCCESS"])
    source_last_success = _latest_utc_from_values([item.get("last_success_at") for item in source_runs])
    source_last_attempt = _latest_utc_from_values([item.get("last_attempt_at") for item in source_runs])

    latest_alert_updated = None
    latest_alert_source = None
    latest_alert_id = None
    if isinstance(latest_alert_item, dict):
        latest_alert_updated = _to_utc_iso(
            latest_alert_item.get("updated_at")
            or latest_alert_item.get("fetched_at")
            or latest_alert_item.get("effective_at")
            or latest_alert_item.get("issued_at")
        )
        latest_alert_payload = latest_alert_item.get("payload") if isinstance(latest_alert_item.get("payload"), dict) else {}
        latest_alert_source = (
            latest_alert_payload.get("alert_source")
            or latest_alert_payload.get("source_name")
            or latest_alert_item.get("source")
            or "N/A"
        )
        latest_alert_id = latest_alert_item.get("external_id") or latest_alert_item.get("id")

    main_sqlite_path = _resolve_main_sqlite_path()
    internal_sqlite_path = _resolve_internal_api_sqlite_path()
    fallback_file_path = os.getenv('SENSOR_ALERT_JSON', '/Users/matrika/Desktop/sensor/output/all_data.json')

    main_sqlite = _file_stats(main_sqlite_path)
    internal_sqlite = _file_stats(internal_sqlite_path)
    fallback_file = _file_stats(fallback_file_path)

    main_sqlite["rows"] = {
        "users": _sqlite_table_count(main_sqlite_path, "Users"),
        "disasters": _sqlite_table_count(main_sqlite_path, "Disasters"),
    }
    internal_sqlite["rows"] = {
        "alerts": _sqlite_table_count(internal_sqlite_path, "alerts"),
        "source_runs": _sqlite_table_count(internal_sqlite_path, "source_runs"),
    }

    total_sqlite_bytes = int(main_sqlite.get("size_bytes", 0)) + int(internal_sqlite.get("size_bytes", 0))

    fallback_generated_at = None
    if fallback_file.get("exists"):
        try:
            with open(fallback_file_path, "r", encoding="utf-8") as fallback_handle:
                fallback_payload = json.load(fallback_handle)
            fallback_generated_at = _to_utc_iso((fallback_payload.get("metadata") or {}).get("generated_at_utc"))
        except Exception:
            fallback_generated_at = None

    generated_hint_utc = latest_alert_updated or source_last_success or fallback_generated_at
    if internal_healthy:
        recommended_mode = "internal_api"
    elif fallback_file.get("exists"):
        recommended_mode = "file_fallback"
    else:
        recommended_mode = "degraded"

    return jsonify({
        "success": True,
        "server_time_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pipeline": {
            "internal_api_healthy": internal_healthy,
            "recommended_mode": recommended_mode,
            "last_sync_attempt_utc": _internal_api_last_sync_attempt_utc,
            "last_sync_success_utc": _internal_api_last_sync_success_utc,
            "sync_interval_seconds": INTERNAL_API_SYNC_MIN_INTERVAL_SECONDS,
        },
        "updates": {
            "source_last_success_utc": source_last_success,
            "source_last_attempt_utc": source_last_attempt,
            "latest_alert_updated_utc": latest_alert_updated,
            "latest_alert_source": latest_alert_source,
            "latest_alert_id": latest_alert_id,
            "generated_hint_utc": generated_hint_utc,
        },
        "sources": {
            "count": len(source_runs),
            "healthy_count": source_success_count,
            "failing_count": max(0, len(source_runs) - source_success_count),
            "items": source_runs,
            "status_error": source_runs_error,
            "latest_alert_error": latest_alert_error,
        },
        "storage": {
            "main_sqlite": main_sqlite,
            "internal_sqlite": internal_sqlite,
            "fallback_file": fallback_file,
            "total_sqlite_bytes": total_sqlite_bytes,
            "total_sqlite_human": _format_bytes(total_sqlite_bytes),
        },
        "internal_api": {
            "base_url": internal_base_url,
            "alerts_url": _internal_api_alerts_url(),
            "health_url": _internal_api_health_url(),
        },
    })


@app.route('/api/mobile/hill90/force-sync', methods=['POST'])
def mobile_hill90_force_sync():
    global _internal_api_last_sync_attempt_utc, _internal_api_last_sync_success_utc, _internal_api_last_sync_monotonic

    ensure_internal_api_running()
    if not _internal_api_is_healthy(timeout_seconds=3):
        return jsonify({
            "success": False,
            "message": "Internal API is not healthy"
        }), 502

    attempted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _internal_api_last_sync_attempt_utc = attempted_at

    try:
        response = requests.post(_internal_api_sync_url(), headers=_internal_api_auth_headers(), timeout=25)
        payload = response.json() if response.content else {}
        if response.status_code < 400:
            _internal_api_last_sync_success_utc = attempted_at
            _internal_api_last_sync_monotonic = time_module.monotonic()
            return jsonify({
                "success": True,
                "attempted_at_utc": attempted_at,
                "sync_response": payload
            }), 200

        return jsonify({
            "success": False,
            "attempted_at_utc": attempted_at,
            "message": f"Sync endpoint returned HTTP {response.status_code}",
            "sync_response": payload
        }), 502
    except Exception as exc:
        return jsonify({
            "success": False,
            "attempted_at_utc": attempted_at,
            "message": str(exc)
        }), 502


@app.route('/api/mobile/live-alerts')
def mobile_live_alerts():
    state_filter = (request.args.get('state') or '').strip().lower()
    coverage_param = request.args.get('coverage')
    coverage_filter = (coverage_param or '').strip().lower()
    if coverage_filter:
        if coverage_filter not in ['all', 'india', 'international']:
            coverage_filter = 'all'
    else:
        if state_filter in ['international', 'global', 'outside india']:
            coverage_filter = 'international'
        elif state_filter in ['', 'india', 'all']:
            coverage_filter = 'india'
        else:
            coverage_filter = 'all'

    state_query = state_filter
    if state_query in ['', 'india', 'all', 'international', 'global', 'outside india']:
        state_query = ''

    severity_filter = (request.args.get('severity') or '').strip().lower()
    type_filter = (request.args.get('disaster_type') or '').strip().lower()
    date_filter = (request.args.get('date') or '').strip()
    scope = (request.args.get('scope') or 'official').strip().lower()
    if scope not in ['official', 'expanded']:
        scope = 'official'
    source_policy = (request.args.get('source_policy') or os.getenv('MOBILE_ALERTS_SOURCE_POLICY', 'live_only')).strip().lower()
    if source_policy not in ['live_only', 'auto_fallback']:
        source_policy = 'live_only'
    max_items = request.args.get('limit', default=200, type=int)
    max_items = max(10, min(max_items, 2000))

    parsed_date = None
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        except ValueError:
            parsed_date = None

    def category_from_text(disaster_type_value, warning_message_value):
        blob = f"{disaster_type_value or ''} {warning_message_value or ''}".lower()

        if any(k in blob for k in ['cyclone', 'hurricane', 'storm surge', 'cyclonic']):
            return 'Cyclonic'
        if 'landslide' in blob:
            return 'Landslide'
        if 'flood' in blob:
            return 'Flood'
        if any(k in blob for k in ['rain', 'cloudburst']):
            return 'Rain'
        if any(k in blob for k in ['thunderstorm', 'lightning']):
            return 'Thunderstorm'
        if 'fire' in blob:
            return 'Fire'
        if any(k in blob for k in ['earthquake', 'seismic']):
            return 'Earthquake'
        if any(k in blob for k in ['heat wave', 'heatwave']):
            return 'Heat Wave'
        return 'Other'

    def parse_alert_date(value):
        if not value:
            return None
        as_text = str(value).strip()
        if not as_text:
            return None

        try:
            return datetime.fromisoformat(as_text.replace('Z', '+00:00')).date()
        except ValueError:
            pass

        for fmt in ['%a %b %d %H:%M:%S IST %Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                return datetime.strptime(as_text, fmt).date()
            except ValueError:
                continue
        return None

    india_area_tokens = [
        'india',
        'andaman and nicobar',
        'andhra pradesh',
        'arunachal pradesh',
        'assam',
        'bihar',
        'chandigarh',
        'chhattisgarh',
        'dadra and nagar haveli',
        'daman and diu',
        'goa',
        'gujarat',
        'haryana',
        'himachal pradesh',
        'jammu and kashmir',
        'jharkhand',
        'karnataka',
        'kerala',
        'ladakh',
        'lakshadweep',
        'madhya pradesh',
        'maharashtra',
        'manipur',
        'meghalaya',
        'mizoram',
        'nagaland',
        'odisha',
        'orissa',
        'punjab',
        'rajasthan',
        'sikkim',
        'tamil nadu',
        'telangana',
        'tripura',
        'uttar pradesh',
        'uttarakhand',
        'west bengal',
        'delhi',
        'new delhi',
        'puducherry',
        'pondicherry',
    ]
    international_area_tokens = [
        'afghanistan',
        'bangladesh',
        'bhutan',
        'china',
        'indonesia',
        'iran',
        'maldives',
        'myanmar',
        'nepal',
        'pakistan',
        'sri lanka',
        'tajikistan',
        'thailand',
        'tibet',
        'uzbekistan',
    ]

    def classify_alert_coverage(area_description, lat_value, lon_value):
        if isinstance(lat_value, (int, float)) and isinstance(lon_value, (int, float)):
            in_india_box = 6.0 <= float(lat_value) <= 38.5 and 68.0 <= float(lon_value) <= 98.8
            return 'india' if in_india_box else 'international'

        area_text = str(area_description or '').strip().lower()
        if area_text:
            if any(token in area_text for token in india_area_tokens):
                return 'india'
            if any(token in area_text for token in international_area_tokens):
                return 'international'

        return 'unknown'

    def passes_coverage_filter(area_description, lat_value, lon_value):
        if coverage_filter == 'all':
            return True
        coverage = classify_alert_coverage(area_description, lat_value, lon_value)
        if coverage_filter == 'international':
            return coverage == 'international'
        # For India mode, include unknown coverage rather than dropping potentially local alerts
        return coverage in ['india', 'unknown']

    def extract_lat_lon_from_centroid(centroid_value):
        if centroid_value is None:
            return None, None

        if isinstance(centroid_value, (list, tuple)) and len(centroid_value) >= 2:
            try:
                return float(centroid_value[1]), float(centroid_value[0])
            except (TypeError, ValueError):
                return None, None

        centroid_text = str(centroid_value).strip()
        if ',' not in centroid_text:
            return None, None
        parts = centroid_text.split(',')
        if len(parts) != 2:
            return None, None
        try:
            return float(parts[1].strip()), float(parts[0].strip())
        except (TypeError, ValueError):
            return None, None

    def fetch_direct_sachet_cap_alerts(max_records=3000):
        cap_url = os.getenv('SACHET_CAP_URL', 'https://sachet.ndma.gov.in/CapFeed').strip() or 'https://sachet.ndma.gov.in/CapFeed'
        response = requests.get(cap_url, timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        cap_alerts = []
        for alert_node in root.findall('.//{*}alert'):
            identifier = (alert_node.findtext('./{*}identifier') or '').strip()
            source = (alert_node.findtext('./{*}senderName') or alert_node.findtext('./{*}sender') or 'NDMA SACHET').strip()

            info = alert_node.find('./{*}info')
            if info is None:
                continue

            event = (info.findtext('./{*}event') or 'Alert').strip()
            severity = (info.findtext('./{*}severity') or 'WATCH').strip()
            start_time = (info.findtext('./{*}onset') or info.findtext('./{*}effective') or info.findtext('./{*}sent') or '').strip()
            end_time = (info.findtext('./{*}expires') or '').strip()
            warning_message = (info.findtext('./{*}description') or info.findtext('./{*}headline') or '').strip()

            area_descriptions = []
            centroid = ''

            for area_node in info.findall('./{*}area'):
                area_desc = (area_node.findtext('./{*}areaDesc') or '').strip()
                if area_desc:
                    area_descriptions.append(area_desc)

                circle = (area_node.findtext('./{*}circle') or '').strip()
                if not centroid and circle:
                    first = circle.split()[0]
                    if ',' in first:
                        circle_parts = first.split(',')
                        if len(circle_parts) >= 2:
                            try:
                                lat_value = float(circle_parts[0].strip())
                                lon_value = float(circle_parts[1].strip())
                                centroid = f"{lon_value},{lat_value}"
                            except (TypeError, ValueError):
                                centroid = ''

                polygon = (area_node.findtext('./{*}polygon') or '').strip()
                if not centroid and polygon:
                    first_pair = polygon.split()[0]
                    if ',' in first_pair:
                        poly_parts = first_pair.split(',')
                        if len(poly_parts) >= 2:
                            try:
                                lat_value = float(poly_parts[0].strip())
                                lon_value = float(poly_parts[1].strip())
                                centroid = f"{lon_value},{lat_value}"
                            except (TypeError, ValueError):
                                centroid = ''

            area_description = ', '.join(area_descriptions).strip()

            cap_alerts.append({
                'identifier': identifier,
                'disaster_type': event,
                'severity': severity,
                'area_description': area_description,
                'warning_message': warning_message,
                'effective_start_time': start_time,
                'effective_end_time': end_time,
                'alert_source': source,
                'centroid': centroid,
            })

            if len(cap_alerts) >= max_records:
                break

        return cap_alerts

    formatted = []
    generated_at = None
    source_mode = 'internal_api'

    internal_api_url = os.getenv('INTERNAL_ALERTS_API_URL', 'http://127.0.0.1:5100/api/alerts').strip()
    internal_api_key = os.getenv('INTERNAL_ALERTS_API_KEY', '').strip()
    internal_api_key_header = os.getenv('INTERNAL_ALERTS_API_KEY_HEADER', 'X-Internal-API-Key').strip() or 'X-Internal-API-Key'

    internal_items = []
    internal_error = None
    internal_request_ok = False

    internal_limit = min(5000, max(500, max_items * 4))

    try:
        sync_internal_api_if_needed()
        headers = {}
        if internal_api_key:
            headers[internal_api_key_header] = internal_api_key

        params = {'limit': internal_limit}
        if state_query:
            params['area'] = state_query
        if severity_filter and severity_filter != 'all':
            params['severity'] = severity_filter.upper()

        response = requests.get(internal_api_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        internal_payload = response.json() if response.content else {}
        internal_items = internal_payload.get('items', []) if isinstance(internal_payload, dict) else []
        generated_at = response.headers.get('Date')
        internal_request_ok = True
    except Exception as exc:
        internal_error = str(exc)
        source_mode = 'internal_unavailable'

    use_internal_source = internal_request_ok and not (source_policy == 'auto_fallback' and len(internal_items) == 0)

    if use_internal_source:
        for item in internal_items:
            if not isinstance(item, dict):
                continue

            payload_item = item.get('payload') if isinstance(item.get('payload'), dict) else {}
            lat, lon = extract_lat_lon_from_centroid(payload_item.get('centroid'))

            if lat is None or lon is None:
                try:
                    lat = float(payload_item.get('lat')) if payload_item.get('lat') is not None else None
                    lon = float(payload_item.get('lon')) if payload_item.get('lon') is not None else None
                except (TypeError, ValueError):
                    lat, lon = None, None

            area_description = str(item.get('area') or payload_item.get('area_description') or '')
            disaster_type = str(item.get('event_type') or payload_item.get('disaster_type') or 'Alert')
            warning_message = str(item.get('description') or item.get('headline') or payload_item.get('warning_message') or '')
            severity_value = str(item.get('severity') or payload_item.get('severity') or 'WATCH')
            # Prefer upstream CAP times over collector ingest timestamps.
            start_time_value = payload_item.get('effective_start_time') or item.get('effective_at') or item.get('issued_at')
            end_time_value = payload_item.get('effective_end_time') or item.get('expires_at')
            source_value = (
                payload_item.get('alert_source')
                or payload_item.get('source_name')
                or payload_item.get('source')
                or item.get('source_name')
                or item.get('source')
                or 'Live API'
            )
            derived_category = category_from_text(disaster_type, warning_message)

            if not passes_coverage_filter(area_description, lat, lon):
                continue

            if state_query and state_query not in area_description.lower():
                continue

            if severity_filter and severity_filter != 'all' and severity_filter != severity_value.lower():
                continue

            if type_filter and type_filter != 'all':
                normalized = type_filter.lower()
                searchable = f"{disaster_type} {warning_message}".lower()
                if normalized in ['cyclonic', 'landslide', 'flood', 'rain', 'thunderstorm', 'fire', 'earthquake', 'heat wave', 'other']:
                    if normalized != derived_category.lower():
                        continue
                elif normalized not in searchable:
                    continue

            if parsed_date is not None:
                start_date = parse_alert_date(start_time_value)
                if start_date != parsed_date:
                    continue

            formatted.append({
                'id': item.get('external_id') or item.get('id'),
                'type': disaster_type,
                'category': derived_category,
                'severity': severity_value,
                'severity_color': payload_item.get('severity_color', 'yellow'),
                'area': area_description,
                'message': warning_message,
                'source': source_value,
                'source_section': 'internal_api',
                'start_time': start_time_value,
                'end_time': end_time_value,
                'lat': lat,
                'lon': lon,
                'location_available': isinstance(lat, (int, float)) and isinstance(lon, (int, float))
            })

            if len(formatted) >= max_items:
                break
    else:
        direct_items = []
        direct_error = None

        try:
            direct_items = fetch_direct_sachet_cap_alerts(max_records=internal_limit)
        except Exception as exc:
            direct_error = str(exc)

        if direct_items:
            source_mode = 'main_app_direct'

            for payload_item in direct_items:
                if not isinstance(payload_item, dict):
                    continue

                lat, lon = extract_lat_lon_from_centroid(payload_item.get('centroid'))

                if lat is None or lon is None:
                    try:
                        lat = float(payload_item.get('lat')) if payload_item.get('lat') is not None else None
                        lon = float(payload_item.get('lon')) if payload_item.get('lon') is not None else None
                    except (TypeError, ValueError):
                        lat, lon = None, None

                area_description = str(payload_item.get('area_description') or '')
                disaster_type = str(payload_item.get('disaster_type') or 'Alert')
                warning_message = str(payload_item.get('warning_message') or '')
                severity_value = str(payload_item.get('severity') or 'WATCH')
                start_time_value = payload_item.get('effective_start_time')
                end_time_value = payload_item.get('effective_end_time')
                derived_category = category_from_text(disaster_type, warning_message)

                if not passes_coverage_filter(area_description, lat, lon):
                    continue

                if state_query and state_query not in area_description.lower():
                    continue

                if severity_filter and severity_filter != 'all' and severity_filter != severity_value.lower():
                    continue

                if type_filter and type_filter != 'all':
                    normalized = type_filter.lower()
                    searchable = f"{disaster_type} {warning_message}".lower()
                    if normalized in ['cyclonic', 'landslide', 'flood', 'rain', 'thunderstorm', 'fire', 'earthquake', 'heat wave', 'other']:
                        if normalized != derived_category.lower():
                            continue
                    elif normalized not in searchable:
                        continue

                if parsed_date is not None:
                    start_date = parse_alert_date(start_time_value)
                    if start_date != parsed_date:
                        continue

                formatted.append({
                    'id': payload_item.get('identifier'),
                    'type': disaster_type,
                    'category': derived_category,
                    'severity': severity_value,
                    'severity_color': payload_item.get('severity_color', 'yellow'),
                    'area': area_description,
                    'message': warning_message,
                    'source': payload_item.get('alert_source') or 'NDMA SACHET',
                    'source_section': 'main_app_direct',
                    'start_time': start_time_value,
                    'end_time': end_time_value,
                    'lat': lat,
                    'lon': lon,
                    'location_available': isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                })

                if len(formatted) >= max_items:
                    break

        if not formatted and source_policy == 'live_only':
            return jsonify({
                'success': False,
                'message': 'Unable to load live alerts right now',
                'source_mode': 'internal_unavailable',
                'source_policy': source_policy,
                'internal_error': internal_error,
                'direct_error': direct_error,
                'alerts': []
            }), 503

        if formatted:
            generated_at = generated_at or datetime.utcnow().isoformat() + 'Z'
            return jsonify({
                'success': True,
                'generated_at': generated_at,
                'source_mode': source_mode,
                'source_policy': source_policy,
                'scope': scope,
                'count': len(formatted),
                'alerts': formatted
            })

        if internal_request_ok and len(internal_items) == 0:
            source_mode = 'file_fallback'
            internal_error = 'Internal API returned 0 alerts; switched to fallback snapshot'
        else:
            source_mode = 'file_fallback'

        source_mode = 'file_fallback'
        data_file = os.getenv('SENSOR_ALERT_JSON', '/Users/matrika/Desktop/sensor/output/all_data.json')
        if not os.path.exists(data_file):
            return jsonify({
                'success': False,
                'message': 'Unable to load live alerts right now',
                'internal_error': internal_error,
                'source_policy': source_policy,
                'alerts': []
            }), 404

        try:
            with open(data_file, 'r', encoding='utf-8') as file:
                payload = json.load(file)
        except Exception as err:
            return jsonify({
                'success': False,
                'message': 'Unable to load live alerts right now',
                'internal_error': internal_error,
                'source_policy': source_policy,
                'alerts': []
            }), 500

        generated_at = payload.get('metadata', {}).get('generated_at_utc')
        raw_block = payload.get('raw', {})
        raw_alerts = raw_block.get('alerts', [])

        seen_fingerprints = set()

        def add_alert_candidate(candidate, section='alerts'):
            if not isinstance(candidate, dict):
                return

            candidate_record = dict(candidate)
            candidate_record['_source_section'] = section

            fingerprint = '|'.join([
                str(candidate_record.get('identifier', '')).strip(),
                str(candidate_record.get('disaster_type', '')).strip().lower(),
                str(candidate_record.get('effective_start_time', '')).strip(),
                str(candidate_record.get('area_description', '')).strip().lower(),
            ])
            if fingerprint in seen_fingerprints:
                return
            seen_fingerprints.add(fingerprint)
            raw_alerts.append(candidate_record)

        initial_alerts = list(raw_alerts)
        raw_alerts = []
        for item in initial_alerts:
            add_alert_candidate(item, section='alerts')

        if scope == 'expanded':
            nowcast_details = (raw_block.get('nowcast') or {}).get('nowcastDetails') or []
            for item in nowcast_details:
                if not isinstance(item, dict):
                    continue

                location_data = item.get('location') if isinstance(item.get('location'), dict) else {}
                nowcast_lat = location_data.get('lat', location_data.get('latitude'))
                nowcast_lon = location_data.get('lon', location_data.get('longitude'))

                if (nowcast_lat is None or nowcast_lon is None) and isinstance(location_data.get('coordinates'), (list, tuple)):
                    coords = location_data.get('coordinates')
                    if len(coords) >= 2:
                        try:
                            nowcast_lon = float(coords[0])
                            nowcast_lat = float(coords[1])
                        except (TypeError, ValueError):
                            nowcast_lon = None
                            nowcast_lat = None

                nowcast_centroid = ''
                try:
                    if nowcast_lat is not None and nowcast_lon is not None:
                        nowcast_centroid = f"{float(nowcast_lon)},{float(nowcast_lat)}"
                except (TypeError, ValueError):
                    nowcast_centroid = ''

                events_value = item.get('events')
                events_blob = ''
                if isinstance(events_value, list):
                    events_blob = ', '.join([str(entry.get('event') if isinstance(entry, dict) else entry) for entry in events_value])
                elif events_value is not None:
                    events_blob = str(events_value)

                display_type = item.get('event_category') or item.get('disaster_type') or 'Nowcast'
                first_event = (events_blob.split(',')[0].strip() if events_blob else '')
                if str(display_type).strip().lower() == 'rain' and first_event:
                    display_type = first_event

                add_alert_candidate({
                    'identifier': item.get('identifier') or f"nowcast-{item.get('effective_start_time', '')}-{item.get('area_description', '')}",
                    'disaster_type': display_type,
                    'severity': str(item.get('severity', 'WATCH')).upper(),
                    'area_description': item.get('area_description') or location_data.get('district') or location_data.get('state') or '',
                    'warning_message': events_blob,
                    'effective_start_time': item.get('effective_start_time') or item.get('entry_time'),
                    'effective_end_time': item.get('effective_end_time'),
                    'alert_source': item.get('source') or 'SACHET Nowcast',
                    'severity_color': item.get('severity_color', 'yellow'),
                    'centroid': nowcast_centroid,
                }, section='nowcast')

            earthquake_alerts = (raw_block.get('earthquakes') or {}).get('alerts') or []
            for item in earthquake_alerts:
                if not isinstance(item, dict):
                    continue

                eq_lat = item.get('latitude')
                eq_lon = item.get('longitude')
                eq_centroid = ''
                try:
                    if eq_lat is not None and eq_lon is not None:
                        eq_centroid = f"{float(eq_lon)},{float(eq_lat)}"
                except (TypeError, ValueError):
                    eq_centroid = ''

                add_alert_candidate({
                    'identifier': item.get('identifier') or f"eq-{item.get('effective_start_time', '')}-{item.get('latitude', '')}-{item.get('longitude', '')}",
                    'disaster_type': item.get('disaster_type') or 'Earthquake',
                    'severity': item.get('severity') or 'ALERT',
                    'area_description': item.get('direction') or item.get('location') or 'Earthquake Region',
                    'warning_message': item.get('warning_message') or '',
                    'effective_start_time': item.get('effective_start_time'),
                    'effective_end_time': item.get('effective_end_time'),
                    'alert_source': item.get('source') or 'SACHET Earthquake',
                    'severity_color': item.get('severity_color', 'orange'),
                    'centroid': eq_centroid,
                }, section='earthquakes')

            location_alerts = (raw_block.get('location_alerts') or {}).get('alerts') or []
            for item in location_alerts:
                add_alert_candidate(item, section='location_alerts')

            address_alerts = (raw_block.get('address_alerts') or {}).get('alerts') or []
            for item in address_alerts:
                add_alert_candidate(item, section='address_alerts')

        direct_merged = 0
        direct_merge_error = None
        if str(os.getenv('SACHET_DIRECT_MERGE', 'true')).strip().lower() in ['1', 'true', 'yes', 'on']:
            try:
                direct_cap_alerts = fetch_direct_sachet_cap_alerts(max_records=min(3000, max_items * 8))
                existing_ids = {str(a.get('identifier', '')).strip() for a in raw_alerts if str(a.get('identifier', '')).strip()}

                for alert in direct_cap_alerts:
                    aid = str(alert.get('identifier', '')).strip()
                    if aid and aid in existing_ids:
                        continue
                    if aid:
                        existing_ids.add(aid)
                    raw_alerts.append(alert)
                    direct_merged += 1
            except Exception as exc:
                direct_merge_error = str(exc)

        for alert in raw_alerts:
            lat, lon = extract_lat_lon_from_centroid(alert.get('centroid'))
            area_description = str(alert.get('area_description', ''))
            disaster_type = str(alert.get('disaster_type', 'Alert'))
            warning_message = str(alert.get('warning_message', ''))
            severity_value = str(alert.get('severity', 'WATCH'))
            start_time_value = alert.get('effective_start_time')
            derived_category = category_from_text(disaster_type, warning_message)

            if not passes_coverage_filter(area_description, lat, lon):
                continue

            if state_query and state_query not in area_description.lower():
                continue

            if severity_filter and severity_filter != 'all' and severity_filter != severity_value.lower():
                continue

            if type_filter and type_filter != 'all':
                normalized = type_filter.lower()
                searchable = f"{disaster_type} {warning_message}".lower()
                if normalized in ['cyclonic', 'landslide', 'flood', 'rain', 'thunderstorm', 'fire', 'earthquake', 'heat wave', 'other']:
                    if normalized != derived_category.lower():
                        continue
                elif normalized not in searchable:
                    continue

            if parsed_date is not None:
                start_date = parse_alert_date(start_time_value)
                if start_date != parsed_date:
                    continue

            formatted.append({
                'id': alert.get('identifier'),
                'type': disaster_type,
                'category': derived_category,
                'severity': severity_value,
                'severity_color': alert.get('severity_color', 'yellow'),
                'area': area_description,
                'message': warning_message,
                'source': alert.get('alert_source', 'NDMA SACHET'),
                'source_section': alert.get('_source_section', 'alerts'),
                'start_time': start_time_value,
                'end_time': alert.get('effective_end_time'),
                'lat': lat,
                'lon': lon,
                'location_available': isinstance(lat, (int, float)) and isinstance(lon, (int, float))
            })

            if len(formatted) >= max_items:
                break

    mappable_count = len([a for a in formatted if a.get('location_available')])

    response_payload = {
        'success': True,
        'count': len(formatted),
        'mappable_count': mappable_count,
        'source_mode': source_mode,
        'source_policy': source_policy,
        'data_scope': scope,
        'state_filter': state_filter or 'india',
        'coverage_filter': coverage_filter,
        'severity_filter': severity_filter or 'all',
        'type_filter': type_filter or 'all',
        'date_filter': date_filter or '',
        'generated_at': generated_at,
        'alerts': formatted
    }

    if source_mode == 'file_fallback':
        response_payload['direct_sachet_merge_enabled'] = str(os.getenv('SACHET_DIRECT_MERGE', 'true')).strip().lower() in ['1', 'true', 'yes', 'on']
        response_payload['direct_sachet_merged'] = direct_merged if 'direct_merged' in locals() else 0
        response_payload['direct_sachet_error'] = direct_merge_error if 'direct_merge_error' in locals() else None
        response_payload['raw_pool_counts'] = {
            'alerts': len((raw_block.get('alerts') if 'raw_block' in locals() else []) or []),
            'nowcast_details': len((raw_block.get('nowcast', {}).get('nowcastDetails') if 'raw_block' in locals() else []) or []),
            'earthquake_alerts': len((raw_block.get('earthquakes', {}).get('alerts') if 'raw_block' in locals() else []) or []),
            'location_alerts': len((raw_block.get('location_alerts', {}).get('alerts') if 'raw_block' in locals() else []) or []),
            'address_alerts': len((raw_block.get('address_alerts', {}).get('alerts') if 'raw_block' in locals() else []) or []),
        }

    return jsonify(response_payload)


@app.route("/logout")
def logout():
    # clear everything from session; safer than trying to reset individual keys
    session.clear()
    return redirect(url_for('login'))



@app.route("/signup", methods=['GET', 'POST'])
def signup():
    msg = ''
    user_info = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form.get('name')
        role = request.form.get('role', 'USER').upper()  # Convert to uppercase
        phone = request.form.get('phone')
        user_info = {
            'name': name,
            'username': username,
            'email_id': email,
            'phone': phone,
            'password': password,
            'role': role,
        }
        
        # sanitize role input
        if role not in ('ADMIN', 'USER'):
            role = 'USER'

        if len(password) < 8:
            msg = "Password must be at least 8 characters."
            return render_template("signup.html", msg=msg, user_info=user_info)

        record = fetch_one("SELECT * FROM users WHERE username = %s OR email_id = %s", (username, email))

        if record:
            if record[4]:  # is_blocked index
                msg = "Your account is blocked. Contact support."
            else:
                msg = "User already exists. Try again."
        else:
            try:
                # explicitly list columns to avoid ordering bugs
                execute_update(
                    "INSERT INTO users (full_name, username, email_id, password_hash, role, phone)"
                    " VALUES (%s, %s, %s, %s, %s, %s)",
                    (name, username, email, password, role, phone)
                )
                return redirect(url_for('login'))
            except Exception as err:
                msg = f"Signup failed: {err}"

    return render_template("signup.html", msg=msg, user_info=user_info)


@app.route('/weather-grid', methods=['GET'])
def get_weather_grid():
    return redirect(url_for('mobile_satellite'))

    
   
    lat, lon = get_location_by_ip()
    
    if lat and lon:
       
        points = generate_radius_points(lat, lon)
        msg=[]
        results = []
        for p_lat, p_lon in points:
            weather_data = fetch_weather(p_lat, p_lon)
            # Extract only temperature, windspeed, and precipitation from Open-Meteo API
            current = weather_data.get('current_weather', {})
            results.append({
                "coords": [p_lat, p_lon],                
                "temperature": current.get('temperature'),
                "windspeed": current.get('windspeed'),
                "precipitation": current.get('precipitation', 0)
            })
        # results[0]['temperature']=80 test case for heat wave alert
        if results[0]['temperature']>40:
            msg.append("Heat wave alert.")
        if results[0]['windspeed']>20:
            msg.append("Storm alert.")
        if results[0]['precipitation']>10:
            msg.append("Flood alert.") 
            
        
        return render_template("weather.html", temperature=results[0]['temperature'], windspeed=results[0]['windspeed'], precipitation=results[0]['precipitation'], grid_data=results,msg=msg)
    else:
        return render_template("weather.html", msg="Could not detect location.")

@app.route('/api/get-ngos')
def get_nearby_ngos(): 
    return redirect(url_for('mobile_organization'))

@app.route('/api/live-ngos')
def live_ngos():
    # Load contact database
    ngo_contacts_db = load_ngo_contacts()
    normalized_contacts = {
        normalize_org_name(name): details for name, details in ngo_contacts_db.items()
    }
    
    # 1. Grab coordinates from the frontend request
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = 50000  # 50km search radius

    if lat is None or lon is None:
        return jsonify({"error": "Missing coordinates"}), 400

    # 2. Formulate the Overpass API query
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = (
        f"[out:json][timeout:25];"
        f"("
        f"node[\"office\"=\"ngo\"](around:{radius},{lat},{lon});"
        f"node[\"office\"=\"charity\"](around:{radius},{lat},{lon});"
        f"node[\"amenity\"=\"social_facility\"](around:{radius},{lat},{lon});"
        f"way[\"office\"=\"ngo\"](around:{radius},{lat},{lon});"
        f"way[\"office\"=\"charity\"](around:{radius},{lat},{lon});"
        f"way[\"amenity\"=\"social_facility\"](around:{radius},{lat},{lon});"
        f"relation[\"office\"=\"ngo\"](around:{radius},{lat},{lon});"
        f"relation[\"office\"=\"charity\"](around:{radius},{lat},{lon});"
        f"relation[\"amenity\"=\"social_facility\"](around:{radius},{lat},{lon});"
        f");"
        f"out tags center;"
    )

    try:
        # 3. Fetch data from OpenStreetMap
        response = requests.post(overpass_url, data={'data': query}, timeout=25)
        data = response.json()

        # 4. Clean up the messy OSM data and merge with contact info
        ngos = []
        seen = set()
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            ngo_name = tags.get('name', 'Unnamed Relief Facility')
            element_lat = element.get('lat')
            element_lon = element.get('lon')

            if element_lat is None or element_lon is None:
                center = element.get('center') or {}
                element_lat = center.get('lat')
                element_lon = center.get('lon')

            if element_lat is None or element_lon is None:
                continue

            normalized_name = normalize_org_name(ngo_name)

            # Try to find contact info in our database with exact + normalized matching
            contact_info = ngo_contacts_db.get(ngo_name)
            if not contact_info:
                contact_info = normalized_contacts.get(normalized_name)
            if not contact_info and normalized_name:
                for known_name, known_contact in normalized_contacts.items():
                    if normalized_name in known_name or known_name in normalized_name:
                        contact_info = known_contact
                        break
            contact_info = contact_info or {}

            phone_value = pick_first_value(
                tags.get('phone'),
                tags.get('contact:phone'),
                contact_info.get('phone')
            )
            email_value = pick_first_value(
                tags.get('email'),
                tags.get('contact:email'),
                contact_info.get('email')
            )
            website_value = pick_first_value(
                tags.get('website'),
                tags.get('contact:website'),
                tags.get('url'),
                contact_info.get('website')
            )

            address_value = pick_first_value(
                tags.get('addr:full'),
                tags.get('addr:street'),
                tags.get('addr:city'),
                tags.get('is_in:city'),
                tags.get('addr:state')
            )

            area_coverage = contact_info.get('areas') if isinstance(contact_info.get('areas'), list) else []

            dedupe_key = (
                normalized_name,
                round(float(element_lat), 4),
                round(float(element_lon), 4)
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            
            ngo_entry = {
                "name": ngo_name,
                "type": tags.get('office', tags.get('amenity', 'NGO')),
                "lat": element_lat,
                "lon": element_lon,
                "phone": phone_value,
                "email": email_value,
                "website": website_value,
                "address": address_value,
                "areas": area_coverage
            }

            distance_km = haversine_distance_km(lat, lon, ngo_entry['lat'], ngo_entry['lon'])
            eta_minutes, eta_text = estimate_duration_text(distance_km)
            ngo_entry['distance_km'] = round(distance_km, 2)
            ngo_entry['estimated_duration_min'] = eta_minutes
            ngo_entry['estimated_duration'] = eta_text
            ngos.append(ngo_entry)
        
        # If no NGOs found from OSM, return NGOs from our contact database
        if not ngos:
            for name, ngo_info in ngo_contacts_db.items():
                # Add dummy coordinates if not found in OSM
                ngos.append({
                    "name": name,
                    "type": ngo_info.get('type', 'NGO'),
                    "lat": lat,  # Use user's location
                    "lon": lon,
                    "phone": ngo_info.get('phone', 'Not available'),
                    "email": ngo_info.get('email', 'Not available'),
                    "website": ngo_info.get('website', 'Not available'),
                    "address": ngo_info.get('areas', ['Nearby support'])[0] if isinstance(ngo_info.get('areas'), list) and ngo_info.get('areas') else 'Nearby support',
                    "areas": ngo_info.get('areas', []) if isinstance(ngo_info.get('areas'), list) else [],
                    "distance_km": 0,
                    "estimated_duration_min": 2,
                    "estimated_duration": "2 min"
                })

        ngos.sort(key=lambda item: item.get('distance_km', 999999))
        
        return jsonify(ngos)

    except Exception as e:
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

@app.route('/api/contact-request', methods=['POST'])
def contact_request():
    """Handle NGO contact inquiries"""
    try:
        inquiry_data = request.json
        
        # Save inquiry to a file
        inquiries_file = 'ngo_inquiries.json'
        
        # Load existing inquiries or create new list
        try:
            with open(inquiries_file, 'r') as f:
                inquiries = json.load(f)
        except FileNotFoundError:
            inquiries = []
        
        # Add new inquiry
        inquiries.append(inquiry_data)
        
        # Save back to file
        with open(inquiries_file, 'w') as f:
            json.dump(inquiries, f, indent=2)
        
        # You could also send email here or integrate with WhatsApp API
        # For now, just save it
        
        return jsonify({
            "success": True,
            "message": "Your inquiry has been recorded. The NGO will contact you soon."
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500

@app.route('/get-all-users', methods=['GET'])
def get_all_users():
    """Get all users for admin dashboard"""
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        users = fetch_all("SELECT user_id, full_name, username, email_id, phone, role, is_blocked, created_at FROM users where role='USER'")
        
        user_list = []
        for user in users:
            user_list.append({
                "user_id": user[0],
                "name": user[1],
                "username": user[2],
                "email": user[3],
                "phone": user[4],
                "role": user[5],
                "is_blocked": bool(user[6]),
                "created_at": str(user[7])
            })
        
        return jsonify({"success": True, "users": user_list})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# @app.route('/block-user', methods=['POST'])
# def block_user():
#     """Block or unblock a user"""
#     if 'user_id' not in session or session.get('role') != 'ADMIN':
#         return jsonify({"success": False, "message": "Unauthorized"}), 401
    
#     try:
#         data = request.json
#         user_id = data.get('user_id')
        
#         # Get current status
#         result = fetch_one("SELECT is_blocked FROM users WHERE user_id = %s", (user_id,))
        
#         if not result:
#             return jsonify({"success": False, "message": "User not found"}), 404
        
#         # Toggle the blocked status
#         new_status = not result[0]
#         execute_update("UPDATE users SET is_blocked = %s WHERE user_id = %s", (new_status, user_id))
        
#         return jsonify({"success": True, "message": "User status updated successfully"})
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500

# @app.route('/get-all-incidents', methods=['GET'])
# def get_all_incidents():
#     """Get all reported disaster incidents for admin"""
#     if 'user_id' not in session or session.get('role') != 'ADMIN':
#         return jsonify({"success": False, "message": "Unauthorized"}), 401
    
#     try:
#         incidents = fetch_all("""
#             SELECT d.Disaster_id, d.reporter_id, u.username, d.disaster_type, d.description,
#                    d.address_text, d.latitude, d.longitude, d.verify_status, d.media_type, 
#                    d.created_at
#             FROM Disasters d
#             JOIN Users u ON d.reporter_id = u.user_id
#             ORDER BY d.created_at DESC
#         """)
        
#         incident_list = []
#         for incident in incidents:
#             incident_list.append({
#                 "incident_id": incident[0],
#                 "user_id": incident[1],
#                 "username": incident[2],
#                 "incident_type": incident[3],
#                 "description": incident[4],
#                 "location": incident[5],
#                 "latitude": float(incident[6]) if incident[6] else None,
#                 "longitude": float(incident[7]) if incident[7] else None,
#                 "is_verified": bool(incident[8]),
#                 "media_type": incident[9],
#                 "created_at": str(incident[10])
#             })
        
#         return jsonify({"success": True, "incidents": incident_list})
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500

# @app.route('/verify-incident', methods=['POST'])
# def verify_incident():
#     """Verify a disaster incident"""
#     if 'user_id' not in session or session.get('role') != 'ADMIN':
#         return jsonify({"success": False, "message": "Unauthorized"}), 401
    
#     try:
#         data = request.json
#         incident_id = data.get('incident_id')
        
#         result = fetch_one("SELECT verify_status FROM Disasters WHERE Disaster_id = %s", (incident_id,))
        
#         if not result:
#             return jsonify({"success": False, "message": "Incident not found"}), 404
        
#         # Toggle the verified status and set admin_id
#         new_status = not result[0]
#         execute_update("UPDATE Disasters SET verify_status = %s, admin_id = %s WHERE Disaster_id = %s", 
#                       (new_status, session.get('user_id'), incident_id))
        
#         return jsonify({"success": True, "message": "Incident status updated successfully"})
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500

# @app.route('/delete-incident', methods=['POST'])
# def delete_incident():
#     """Delete a disaster incident"""
#     if 'user_id' not in session or session.get('role') != 'ADMIN':
#         return jsonify({"success": False, "message": "Unauthorized"}), 401
    
#     try:
#         data = request.json
#         incident_id = data.get('incident_id')
        
#         execute_update("DELETE FROM Disasters WHERE Disaster_id = %s", (incident_id,))
        
#         return jsonify({"success": True, "message": "Incident deleted successfully"})
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500

# @app.route('/report-disaster', methods=['GET', 'POST'])
# def report_disaster():
#     """Report a new disaster incident"""
#     user_info = session.get('user_info')
#     user_id = request.args.get('user_id')
#     if request.method == 'GET':
#         return render_template('report_disaster.html', username=session.get('username') if 'user_id' in session else None, user_info=user_info)
    
#     # POST request - handle disaster reporting (requires authentication)
#     if 'user_id' not in session:
#         return render_template('report_disaster.html', msg='You must be logged in to submit a disaster report.', msg_type='error')
    
#     try:
#         disaster_type = request.form.get('disaster_type')
#         description = request.form.get('description')
#         address_text = request.form.get('address_text')
#         latitude = request.form.get('latitude', type=float)
#         longitude = request.form.get('longitude', type=float)
#         media_type = request.form.get('media_type')  # 'image' or 'video'
        
#         media_file = request.files.get('media')
#         media_blob = None
        
#         if media_file:
#             media_blob = media_file.read()
        
#         # If admin, auto-verify. If regular user, unverified by default
#         is_admin = session.get('role') == 'ADMIN'
#         verify_status = True if is_admin else False
#         admin_id = session.get('user_id') if is_admin else None
        
#         execute_update("""
#             INSERT INTO Disasters 
#             (reporter_id, disaster_type, description, address_text, latitude, longitude, media_type, media, verify_status, admin_id)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """, (session.get('user_id'), disaster_type, description, address_text, latitude, longitude, media_type, media_blob, verify_status, admin_id))
        
#         msg = "Your disaster report has been verified automatically!" if is_admin else "Disaster reported successfully. Thank you for your report! It will be verified by an admin soon."
#         return render_template('report_disaster.html', username=session.get('username'), msg=msg, msg_type='success')
#     except Exception as e:
#         return render_template('report_disaster.html', username=session.get('username'), msg=str(e), msg_type='error')


# @app.route('/get-all-users', methods=['GET'])
# def get_all_users():
#     """Get all users for admin dashboard"""
#     if 'user_id' not in session or session.get('role') != 'ADMIN':
#         return jsonify({"success": False, "message": "Unauthorized"}), 401
    
#     try:
#         cursor.execute("SELECT user_id, full_name, username, email_id, phone, role, is_blocked, created_at FROM users where role='USER'")
#         users = cursor.fetchall()
        
#         user_list = []
#         for user in users:
#             user_list.append({
#                 "user_id": user[0],
#                 "name": user[1],
#                 "username": user[2],
#                 "email": user[3],
#                 "phone": user[4],
#                 "role": user[5],
#                 "is_blocked": bool(user[6]),
#                 "created_at": str(user[7])
#             })
        
#         return jsonify({"success": True, "users": user_list})
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500

@app.route('/block-user', methods=['POST'])
def block_user():
    """Block or unblock a user"""
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        user_id = data.get('user_id')
        
        # Get current status
        result = fetch_one("SELECT is_blocked FROM users WHERE user_id = %s", (user_id,))
        
        if not result:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Toggle the blocked status
        new_status = not result[0]
        execute_update("UPDATE users SET is_blocked = %s WHERE user_id = %s", (new_status, user_id))
        
        return jsonify({"success": True, "message": "User status updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/get-all-incidents', methods=['GET'])
def get_all_incidents():
    """Get all reported disaster incidents for admin"""
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        incidents = fetch_all("""
            SELECT d.Disaster_id, d.reporter_id, COALESCE(u.username, 'Unknown') as username, d.disaster_type, d.description,
                   d.address_text, d.latitude, d.longitude, d.verify_status, d.media_type, 
                   d.created_at
            FROM Disasters d
            LEFT JOIN Users u ON d.reporter_id = u.User_id
            ORDER BY d.created_at DESC
        """)
        
        incident_list = []
        for incident in incidents:
            incident_list.append({
                "incident_id": incident[0],
                "user_id": incident[1],
                "username": incident[2],
                "incident_type": incident[3],
                "description": incident[4],
                "location": incident[5],
                "latitude": float(incident[6]) if incident[6] else None,
                "longitude": float(incident[7]) if incident[7] else None,
                "is_verified": bool(incident[8]),
                "media_type": incident[9],
                "created_at": str(incident[10])
            })
        
        return jsonify({"success": True, "incidents": incident_list})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/verify-incident', methods=['POST'])
def verify_incident():
    """Verify a disaster incident"""
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        incident_id = data.get('incident_id')
        
        result = fetch_one("SELECT verify_status FROM Disasters WHERE Disaster_id = %s", (incident_id,))
        
        if not result:
            return jsonify({"success": False, "message": "Incident not found"}), 404
        
        # Toggle the verified status and set admin_id
        new_status = not result[0]
        execute_update("UPDATE Disasters SET verify_status = %s, admin_id = %s WHERE Disaster_id = %s", 
                      (new_status, session.get('user_id'), incident_id))
        
        return jsonify({"success": True, "message": "Incident status updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete-incident', methods=['POST'])
def delete_incident():
    """Delete a disaster incident"""
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        incident_id = data.get('incident_id')
        
        execute_update("DELETE FROM Disasters WHERE Disaster_id = %s", (incident_id,))
        
        return jsonify({"success": True, "message": "Incident deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/report-disaster', methods=['GET', 'POST'])
def report_disaster():
    """Report a new disaster incident"""
    
    if request.method == 'GET':
        return render_template(
            'report_disaster.html',
            username=session.get('username') if 'user_id' in session else None
        )
    
    # POST request - handle disaster reporting (requires authentication)
    if 'user_id' not in session:
        return render_template('report_disaster.html', msg='You must be logged in to submit a disaster report.', msg_type='error')
    
    try:
        disaster_type = request.form.get('disaster_type')
        description = request.form.get('description')
        address_text = request.form.get('address_text')
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        media_type = request.form.get('media_type')  # 'image' or 'video'
        
        media_file = request.files.get('media')
        media_blob = None
        
        if media_file:
            media_blob = media_file.read()
        
        # If admin, auto-verify. If regular user, unverified by default
        is_admin = session.get('role') == 'ADMIN'
        verify_status = True if is_admin else False
        admin_id = session.get('user_id') if is_admin else None
        
        execute_update("""
            INSERT INTO Disasters 
            (reporter_id, disaster_type, description, address_text, latitude, longitude, media_type, media, verify_status, admin_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session.get('user_id'), disaster_type, description, address_text, latitude, longitude, media_type, media_blob, verify_status, admin_id))
        
        msg = "Your disaster report has been verified automatically!" if is_admin else "Disaster reported successfully. Thank you for your report! It will be verified by an admin soon."
        return render_template('report_disaster.html', username=session.get('username'), msg=msg, msg_type='success')
    except Exception as e:
        return render_template('report_disaster.html', username=session.get('username'), msg=str(e), msg_type='error')
    

if(__name__=="__main__"):
    print("\n[INFO] Checking and starting internal API if needed...")
    if ensure_internal_api_running():
        print("[INFO] Internal API is running.")
    else:
        print("[ERROR] Internal API could not be started. Some features may not work.")
    sync_internal_api_if_needed(force=True)
    print("[INFO] Starting main Flask app...")
    app.run(debug=False, use_reloader=False, port=int(os.getenv('PORT', '8001')))
