from flask import Flask, url_for, render_template, redirect, request,session, jsonify
from dotenv import load_dotenv
import mysql.connector
import os
import math
import secrets
import requests # api will be called using this libraray


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
      
      cursor.execute("select * from users where username=%s and password=%s",(username,password))
      record=cursor.fetchone()
      if(record):
         session['logged_in']=True
         session['username']=username
        #  or session['username']=record[1]
         session['user_id']=record[0]
         return redirect(url_for('home'))
      else:
       msg='Wrong Credentials, Try Again.'

 return render_template("login.html",msg=msg)


@app.route("/home") 
def home():
   if 'user_id' not in session:
      return redirect(url_for('login'))
      
   return render_template("index.html",username=session.get('username'))


@app.route("/logout")
def logout():
 session.pop('logged_in',None)
 session.pop('user_id',None)
 session.pop('username',None)
 return render_template("index.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name=request.form['name']
        if len(password) < 8:
            msg = "Password must be at least 8 characters."
            return render_template("signup.html", msg=msg)

        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        record = cursor.fetchone()

        if record:
            msg = "User already exists. Try again."
        else:
            try:
                cursor.execute("INSERT INTO users VALUES (DEFAULT, %s, %s, %s,%s,DEFAULT)", (username, email, password,name))
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

        # 4. Clean up the messy OSM data into a simple list
        ngos = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            ngos.append({
                "name": tags.get('name', 'Unnamed Relief Facility'),
                "type": tags.get('office', tags.get('amenity', 'NGO')),
                "lat": element['lat'],
                "lon": element['lon']
            })
        
        return jsonify(ngos)

    except Exception as e:
        return jsonify({"error": "Failed to fetch data"}), 500    
    
if(__name__=="__main__"):
  app.run(debug=True,port='8000')