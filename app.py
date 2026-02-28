from flask import Flask, url_for, render_template, redirect, request,session, jsonify
from dotenv import load_dotenv
import mysql.connector
import os
import json
import math
import secrets
import requests # api will be called using this libraray
import bcrypt


# Load environment variables from .env file
load_dotenv()



db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name=os.getenv("DB_NAME")

try:
    conn = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cursor = conn.cursor()
   
except mysql.connector.Error as err:
     print("❌ Connection failed:", err)

app=Flask(__name__) #create name of Flask app which is name here

# Initialize database tables
def init_database():
    """Create Disasters table with correct schema"""
    try:
        # First, drop the table if it exists with wrong constraints
       
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
        cursor.execute(create_disasters_table)
        conn.commit()
        print("✅ Disasters table created successfully with correct schema")
    except mysql.connector.Error as err:
        print(f"❌ Error creating Disasters table: {err}")

# Initialize database on startup
init_database()

app.secret_key = os.getenv('SECRET_KEY')


# this will be used in forecasting open meteor api

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
   # this method checks user credentials and redirects them to home or login
 msg='' 
 if request.method=='POST':
      username=request.form['username']
      password=request.form['password']
      
    #   # When a user signs up:
    #   password = password.encode('utf-8')
    #   hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    #   for encryption

      cursor.execute("select * from users where username=%s and password_hash=%s",(username,password))
      record=cursor.fetchone()
      if(record):
         session['logged_in']=True
         session['username']=username
        #  or session['username']=record[1]
         session['user_id']=record[0]
         session['role']=record[8]  # Store role from database (index 8)
         if(record[4]==True):
            msg='Your account is blocked. Contact support.'
            session.clear()

         return redirect(url_for('home'))
      else:
       msg='Wrong Credentials, Try Again.'

 return render_template("login.html",msg=msg)


@app.route("/home") 
def home():
   if 'user_id' not in session:
      return redirect(url_for('login'))
   if session.get('role') == 'ADMIN':  
      return render_template("admin.html",username=session.get('username'))
   return render_template("index.html",username=session.get('username'))


@app.route("/logout")
def logout():
 session.pop('logged_in',None)
 session.pop('user_id',None)
 session.pop('username',None)
 session.pop('role',None)
 return redirect(url_for('index'))

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name=request.form['name']
        role=request.form.get('role', 'USER').upper()  # Convert to uppercase
        phone=request.form.get('phone') 
        

        # User_id int auto_increment primary key,
        # Username varchar(30) unique not null,
        # email_id varchar(30) unique not null,
        # phone VARCHAR(10) NOT NULL,
        # is_blocked BOOLEAN DEFAULT FALSE,
        # created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        # password_hash VARCHAR(255) NOT NULL,
        # role ENUM('ADMIN', 'USER') DEFAULT 'USER',

        if len(password) < 8:
            msg = "Password must be at least 8 characters."
            return render_template("signup.html", msg=msg)

        cursor.execute("SELECT * FROM users WHERE username = %s OR email_id = %s", (username, email))
        record = cursor.fetchone()

        if record:
            if record[4]:  # Assuming is_blocked is the 5th column (index 4)
                msg = "Your account is blocked. Contact support."
            else:    
                msg = "User already exists. Try again."
        else:
            try:
                cursor.execute("INSERT INTO users VALUES (DEFAULT,%s,%s,%s,%s,DEFAULT,DEFAULT,%s,%s)", (name,username, email,phone, password,role))
                conn.commit()
                return redirect(url_for('login'))
            except mysql.connector.Error as err:
                msg = f"Signup failed: {err}"

    return render_template("signup.html", msg=msg)


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
    
    # 1. Grab coordinates from the frontend request
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = 50000  # 50km search radius

    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    # 2. Formulate the Overpass API query
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
        # 3. Fetch data from OpenStreetMap
        response = requests.post(overpass_url, data={'data': query})
        data = response.json()

        # 4. Clean up the messy OSM data and merge with contact info
        ngos = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            ngo_name = tags.get('name', 'Unnamed Relief Facility')
            
            # Try to find contact info in our database
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
                    "website": ngo_info.get('website', 'Not available')
                })
        
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
        cursor.execute("SELECT user_id, full_name, username, email_id, phone, role, is_blocked, created_at FROM users where role='USER'")
        users = cursor.fetchall()
        
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
  app.run(debug=True,port='8000')