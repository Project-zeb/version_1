from flask import Flask, url_for, render_template, redirect, request, session, jsonify
from dotenv import load_dotenv
import mysql.connector
import os
import json
import math
import requests

# Load environment variables from .env file
load_dotenv()

db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

try:
    conn = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cursor = conn.cursor()
except mysql.connector.Error as err:
    print("Database connection failed:", err)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


def fetch_weather(lat, lon):
    """Fetch current weather data from Open-Meteo API."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    response = requests.get(url)
    return response.json()


def generate_radius_points(lat, lon, radius_km=100):
    """Generate grid points around user location for weather monitoring."""
    delta_lat = radius_km / 111
    delta_lon = radius_km / (111 * math.cos(math.radians(lat)))

    return [
        (lat, lon),
        (lat + delta_lat, lon),
        (lat - delta_lat, lon),
        (lat, lon + delta_lon),
        (lat, lon - delta_lon)
    ]


def get_location_by_ip():
    """Get user location coordinates from IP address using IP-API service."""
    try:
        response = requests.get('http://ip-api.com/json/')
        data = response.json()
        
        if data['status'] == 'success':
            return data['lat'], data['lon']
    except Exception as e:
        print(f"Error getting location: {e}")
    
    return None, None


def load_ngo_contacts():
    """Load NGO contact information from database file."""
    try:
        with open('ngos_contacts.json', 'r') as f:
            data = json.load(f)
            return {ngo['name']: ngo for ngo in data['ngo_contacts']}
    except FileNotFoundError:
        return {}


@app.route("/")
def index():
    """Display landing page."""
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    """Handle user login authentication."""
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        record = cursor.fetchone()
        if record:
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = record[0]
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username or password. Please try again.'
    
    return render_template("login.html", msg=msg)


@app.route("/home")
def home():
    """Display user dashboard after authentication."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", username=session.get('username'))


@app.route("/logout")
def logout():
    """Clear session and log out user."""
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    return render_template("index.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    """Handle user registration and account creation."""
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        if len(password) < 8:
            msg = "Password must be at least 8 characters."
            return render_template("signup.html", msg=msg)

        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        record = cursor.fetchone()

        if record:
            msg = "User already exists. Try again."
        else:
            try:
                cursor.execute("INSERT INTO users VALUES (DEFAULT, %s, %s, %s, %s, DEFAULT)", (username, email, password, name))
                conn.commit()
                return redirect(url_for('login'))
            except mysql.connector.Error as err:
                msg = f"Signup failed: {err}"

    return render_template("signup.html", msg=msg)


@app.route('/weather-grid', methods=['GET'])
def get_weather_grid():
    """Fetch real-time weather data and generate alerts based on conditions."""
    lat, lon = get_location_by_ip()
    
    if lat and lon:
        points = generate_radius_points(lat, lon)
        alerts = []
        results = []
        for p_lat, p_lon in points:
            weather_data = fetch_weather(p_lat, p_lon)
            current = weather_data.get('current_weather', {})
            results.append({
                "coords": [p_lat, p_lon],                
                "temperature": current.get('temperature'),
                "windspeed": current.get('windspeed'),
                "precipitation": current.get('precipitation', 0)
            })
        
        if results[0]['temperature'] > 40:
            alerts.append("Heat wave alert.")
        if results[0]['windspeed'] > 20:
            alerts.append("Storm alert.")
        if results[0]['precipitation'] > 10:
            alerts.append("Flood alert.")
        
        return render_template("weather.html", temperature=results[0]['temperature'], windspeed=results[0]['windspeed'], precipitation=results[0]['precipitation'], grid_data=results, msg=alerts)
    else:
        return render_template("weather.html", msg="Could not detect location.")


@app.route('/api/get-ngos')
def get_nearby_ngos():
    """Display interactive map for finding nearby relief organizations."""
    return render_template("map.html")


@app.route('/api/live-ngos')
def live_ngos():
    """Fetch nearby NGOs and relief organizations from OpenStreetMap and contact database."""
    ngo_contacts_db = load_ngo_contacts()
    
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = 50000

    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["office"="ngo"](around:{radius},{lat},{lon});
      node["office"="charity"](around:{radius},{lat},{lon});
      node["amenity"="social_facility"](around:{radius},{lat},{lon});
    );
    out body;
    """

    try:
        response = requests.post(overpass_url, data={'data': query})
        data = response.json()

        ngos = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            ngo_name = tags.get('name', 'Unnamed Relief Facility')
            contact_info = ngo_contacts_db.get(ngo_name, {})
            
            ngo_entry = {
                "name": ngo_name,
                "type": tags.get('office', tags.get('amenity', 'NGO')),
                "lat": element['lat'],
                "lon": element['lon'],
                "phone": contact_info.get('phone', 'Not available'),
                "email": contact_info.get('email', 'Not available'),
                "website": contact_info.get('website', 'Not available')
            }
            ngos.append(ngo_entry)
        
        if not ngos:
            for name, ngo_info in ngo_contacts_db.items():
                ngos.append({
                    "name": name,
                    "type": ngo_info.get('type', 'NGO'),
                    "lat": lat,
                    "lon": lon,
                    "phone": ngo_info.get('phone', 'Not available'),
                    "email": ngo_info.get('email', 'Not available'),
                    "website": ngo_info.get('website', 'Not available')
                })
        
        return jsonify(ngos)

    except Exception as e:
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500


@app.route('/api/contact-request', methods=['POST'])
def contact_request():
    """Handle NGO contact inquiries and save to database file."""
    try:
        inquiry_data = request.json
        inquiries_file = 'ngo_inquiries.json'
        
        try:
            with open(inquiries_file, 'r') as f:
                inquiries = json.load(f)
        except FileNotFoundError:
            inquiries = []
        
        inquiries.append(inquiry_data)
        
        with open(inquiries_file, 'w') as f:
            json.dump(inquiries, f, indent=2)
        
        return jsonify({
            "success": True,
            "message": "Your inquiry has been recorded. The NGO will contact you soon."
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=8000)
