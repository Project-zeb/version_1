from flask import Flask, url_for, render_template, redirect, request,session, jsonify, send_file, abort
from dotenv import load_dotenv
import os
import json
import math
import secrets
import base64
import mimetypes
import requests # api will be called using this libraray
import sqlite3
from datetime import datetime
import xml.etree.ElementTree as ET
from authlib.integrations.flask_client import OAuth
# import bcrypt


# Load environment variables from .env file


load_dotenv()

# Database config
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
DB_PATH = os.getenv("SQLITE_DB_PATH", "app.db")
DB_PRIMARY = str(os.getenv("PRIMARY_DB", "mysql") or "mysql").strip().lower()
if DB_PRIMARY not in ["mysql", "sqlite"]:
    DB_PRIMARY = "mysql"

USE_SQLITE = False
ACTIVE_DB_BACKEND = None
conn = None
cursor = None
mysql_conn = None
mysql_cursor = None
sqlite_conn = None
sqlite_cursor = None


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
        print("[WARNING] MySQL connector not available")
        return

    if not db_host or not db_user or not db_name:
        print("[WARNING] MySQL config incomplete. Set DB_HOST, DB_USER and DB_NAME to enable MySQL.")
        return

    try:
        mysql_conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        mysql_cursor = mysql_conn.cursor()
        print("[INFO] MySQL connected")
    except Exception as err:
        mysql_conn = None
        mysql_cursor = None
        print(f"[ERROR] MySQL connection failed: {err}")


def connect_sqlite():
    global sqlite_conn, sqlite_cursor

    try:
        sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        print(f"[INFO] SQLite connected ({DB_PATH})")
    except Exception as err:
        sqlite_conn = None
        sqlite_cursor = None
        print(f"[ERROR] SQLite connection failed: {err}")


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
        print("[ERROR] No database connection available")
        return

    conn = DatabaseConnectionProxy(selected_conn, selected_backend)
    cursor = DatabaseCursorProxy(selected_cursor, selected_backend)
    USE_SQLITE = selected_backend == "sqlite"
    ACTIVE_DB_BACKEND = selected_backend
    print(f"[INFO] Active database: {selected_backend.upper()} (PRIMARY_DB={DB_PRIMARY})")


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
            print(f"[INFO] Tables initialized ({backend_name.upper()})")
            initialized_any = True
        except Exception as err:
            print(f"[ERROR] Error initializing {backend_name.upper()} tables: {err}")

    if not initialized_any:
        print("[ERROR] Database connection not available")

# Initialize database on startup
if cursor:
    init_database()

app.secret_key = os.getenv('SECRET_KEY')


def _check_mysql_health():
    if not mysql_conn:
        return False, "not_connected"
    try:
        mysql_conn.ping(reconnect=True, attempts=1, delay=0)
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
    mysql_ok, mysql_detail = _check_mysql_health()
    sqlite_ok, sqlite_detail = _check_sqlite_health()

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

def execute_query(query, params=None):
    """Execute query using the active backend"""
    global cursor
    if not cursor:
        return None
    try:
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    except Exception as e:
        print(f"Query error: {e}")
        return None

def fetch_one(query, params=None):
    """Fetch one result"""
    execute_query(query, params)
    if cursor:
        return cursor.fetchone()
    return None

def fetch_all(query, params=None):
    """Fetch all results"""
    execute_query(query, params)
    if cursor:
        return cursor.fetchall()
    return []

def execute_update(query, params=None):
    """Execute update/insert/delete"""
    execute_query(query, params)
    if conn:
        conn.commit()

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

  
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', '637634127454-q7jv79fgcfklh5l0s8o9821d21bvdo37.apps.googleusercontent.com'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', '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'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile' # This tells Google WHAT info to give us
    }
)    


def get_google_redirect_uri():
    explicit_uri = str(os.getenv('GOOGLE_REDIRECT_URI', '') or '').strip()
    if explicit_uri:
        return explicit_uri
    return url_for('authorize', _external=True).replace('/oauth2callback', '/auth/callback').replace('/oauth2/callback', '/auth/callback')

@app.route("/") #the route made for the port 5000
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template("index.html")



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
    # 1. Get user info from Google
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    email = user_info['email']
    name = user_info['name']
    
    # 2. Check if this email already exists in our database
    # Note: Using %s because your helper function handles the conversion
    query = "SELECT * FROM users WHERE email_id = %s"
    result = fetch_one(query, (email,))

    if result:
        # Scenario 1: Existing User
        session['user'] = {
            'email': email,
            'name': name,
            'username': result[2],  # username column
            'phone': result[4],     # phone column
            # role column is index 7, not 8
            'role': result[7],
            'user_id': result[0],
            'is_blocked': result[5]
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
        return render_template("admin.html",username=session.get('username'))
    return render_template("index.html",username=session.get('username'))


@app.route('/admin/user-view')
def admin_user_view():
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return redirect(url_for('login'))
    return render_template("index.html", username=session.get('username'))


@app.route('/mobile')
def mobile_landing():
    return redirect(url_for('mobile_home'))


@app.route('/mobile/home')
def mobile_home():
    is_logged_in = 'user_id' in session
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


@app.route('/mobile/live-alerts-check')
def mobile_live_alerts_check():
    return render_template('live_alerts_check.html', username=session.get('username'))


@app.route('/api/mobile/live-alerts')
def mobile_live_alerts():
    state_filter = (request.args.get('state') or '').strip().lower()
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

    try:
        internal_limit = min(5000, max(500, max_items * 4))
        headers = {}
        if internal_api_key:
            headers[internal_api_key_header] = internal_api_key

        params = {'limit': internal_limit}
        if state_filter and state_filter != 'india':
            params['area'] = state_filter
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
            start_time_value = item.get('effective_at') or item.get('issued_at') or payload_item.get('effective_start_time')
            end_time_value = item.get('expires_at') or payload_item.get('effective_end_time')
            derived_category = category_from_text(disaster_type, warning_message)

            if state_filter and state_filter != 'india' and state_filter not in area_description.lower():
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
                'source': item.get('source') or payload_item.get('alert_source') or 'Internal API',
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
        if source_policy == 'live_only':
            return jsonify({
                'success': False,
                'message': 'Live alerts API unavailable (always live mode)',
                'source_mode': 'internal_unavailable',
                'source_policy': source_policy,
                'internal_error': internal_error,
                'alerts': []
            }), 503

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
                'message': 'Internal API unavailable and fallback live alert data file not found',
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
                'message': f'Internal API unavailable and fallback data load failed: {err}',
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

            if state_filter and state_filter != 'india' and state_filter not in area_description.lower():
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
    return render_template("map.html")   

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
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Toggle the blocked status
        new_status = not result[0]
        cursor.execute("UPDATE users SET is_blocked = %s WHERE user_id = %s", (new_status, user_id))
        conn.commit()
        
        return jsonify({"success": True, "message": "User status updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/get-all-incidents', methods=['GET'])
def get_all_incidents():
    """Get all reported disaster incidents for admin"""
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        cursor.execute("""
            SELECT d.Disaster_id, d.reporter_id, u.username, d.disaster_type, d.description,
                   d.address_text, d.latitude, d.longitude, d.verify_status, d.media_type, 
                   d.created_at
            FROM Disasters d
            JOIN Users u ON d.reporter_id = u.User_id
            ORDER BY d.created_at DESC
        """)
        incidents = cursor.fetchall()
        
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
        
        cursor.execute("SELECT verify_status FROM Disasters WHERE Disaster_id = %s", (incident_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"success": False, "message": "Incident not found"}), 404
        
        # Toggle the verified status and set admin_id
        new_status = not result[0]
        cursor.execute("UPDATE Disasters SET verify_status = %s, admin_id = %s WHERE Disaster_id = %s", 
                      (new_status, session.get('user_id'), incident_id))
        conn.commit()
        
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
        
        cursor.execute("DELETE FROM Disasters WHERE Disaster_id = %s", (incident_id,))
        conn.commit()
        
        return jsonify({"success": True, "message": "Incident deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/report-disaster', methods=['GET', 'POST'])
def report_disaster():
    """Report a new disaster incident"""
    
    if request.method == 'GET':
        return render_template('report_disaster.html', username=session.get('username') if 'user_id' in session else None)
    
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
        
        cursor.execute("""
            INSERT INTO Disasters 
            (reporter_id, disaster_type, description, address_text, latitude, longitude, media_type, media, verify_status, admin_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session.get('user_id'), disaster_type, description, address_text, latitude, longitude, media_type, media_blob, verify_status, admin_id))
        
        conn.commit()
        
        msg = "Your disaster report has been verified automatically!" if is_admin else "Disaster reported successfully. Thank you for your report! It will be verified by an admin soon."
        return render_template('report_disaster.html', username=session.get('username'), msg=msg, msg_type='success')
    except Exception as e:
        return render_template('report_disaster.html', username=session.get('username'), msg=str(e), msg_type='error')
    

if(__name__=="__main__"):
    app.run(debug=True, port=int(os.getenv('PORT', '8001')))