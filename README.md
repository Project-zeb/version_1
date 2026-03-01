# Emergency Relief & Disaster Management Platform

A web-based platform designed to connect people affected by natural disasters with nearby relief organizations and NGOs. The application provides real-time weather monitoring, emergency alerts, and location-based NGO discovery.

## Version 1.1 Features

### Core Functionality
- **User Authentication**: Secure signup and login system with password validation (minimum 8 characters)
- **Real-time Weather Monitoring**: Live weather data with a 5-point radius grid to monitor conditions across a wider area
- **Intelligent Alert System**: Automatic triggers for heat waves (exceeding 40 degrees Celsius), storms (exceeding 20 km/h winds), and flood risk (exceeding 10mm precipitation)
- **NGO Location Mapping**: Interactive map showing nearby relief organizations within 50km radius
- **Contact Integration**: Pre-loaded database of verified NGOs and relief organizations with contact information
- **Inquiry System**: Users can submit contact requests to NGOs directly through the platform

### Technical Stack
- **Backend**: Flask (Python web framework)
- **Database**: MySQL for user data and contact management
- **APIs Used**: 
  - Open-Meteo API for weather data (free, no authentication required)
  - IP-API for geolocation services
  - OpenStreetMap Overpass API for NGO location data
- **Frontend**: HTML5, CSS3, JavaScript

## Prerequisites

Before starting, ensure you have:
- Python 3.8 or higher installed
- MySQL Server 5.7 or higher running
- Git installed on your system
- Pip (Python package manager)

## Installation & Setup Guide

### Step 1: Clone the Repository

```bash
git clone <replace-with-your-repository-url>
cd version_1
```

### Step 2: Setup Python Virtual Environment

Create an isolated Python environment:

```bash
python -m venv venv
```

Activate it based on your operating system:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

### Step 3: Install Required Dependencies

```bash
pip install -r requirements.txt
```

This installs all packages listed in requirements.txt including Flask, MySQL connector, and API clients.

### Step 4: Create and Configure Database

Start MySQL and create the database:

```sql
CREATE DATABASE expense_tracker_dbms;
USE expense_tracker_dbms;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Step 5: Setup Environment Configuration

1. Copy the example configuration file to .env:
```bash
copy .env.example .env
```

2. Open `.env` in your text editor and fill in your actual values:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_secure_password
DB_NAME=expense_tracker_dbms
SECRET_KEY=your_secure_secret_key_here
FLASK_ENV=development
```

**Important Security Guidelines:**
- Never share your `.env` file or commit it to git
- Use a strong SECRET_KEY (minimum 16 characters, mix of letters and numbers)
- Change database passwords from defaults
- Keep all credentials private and secure

### Step 6: Run the Application

Start the Flask development server:

```bash
python app.py
```

Open your browser and navigate to: `http://localhost:8000`

## Project Directory Structure

```
project-directory/
├── app.py                    # Main Flask application file
├── requirements.txt          # Python package dependencies
├── ngos_contacts.json       # Pre-loaded NGO database
├── .env                     # Configuration (git ignored - create from .env.example)
├── .env.example             # Template for environment setup
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── README.md               # This documentation
├── templates/              # HTML templates directory
│   ├── index.html          # Landing/home page
│   ├── login.html          # User login page
│   ├── signup.html         # User registration page
│   ├── weather.html        # Weather monitoring dashboard
│   ├── map.html            # NGO location interactive map
│   └── home.html           # User dashboard
└── static/                 # Static files (CSS, JS, images)
    ├── style.css           # Application styling
    ├── script.js           # Client-side JavaScript
    └── disaster image.jpg  # UI images
```

## How to Use the Application

### Creating an Account

1. Click Sign Up on the landing page
2. Enter your full name, email address, and create a password
3. Password must be at least 8 characters for security
4. Click Register to create your account
5. Log in with your new credentials

### Monitoring Weather and Alerts

1. After logging in, access the weather dashboard
2. The system automatically detects your location based on IP address
3. Real-time weather is displayed for your area and surrounding regions
4. Active alerts appear for:
   - Heat waves when temperature exceeds 40 degrees Celsius
   - Storms when wind speed exceeds 20 km/h
   - Flood risk when precipitation exceeds 10mm

### Finding Relief Organizations

1. Navigate to the NGO map view
2. The map displays relief organizations within 50km of your location
3. Click on any organization for:
   - Contact phone number
   - Email address
   - Website link
   - Organization type and name
4. Submit an inquiry to connect with the organization

### Submitting Inquiries

1. Select an NGO from the map
2. Fill in your contact information
3. Describe your need or question
4. Submit the form
5. The NGO will be notified and contact you

## API Endpoints Reference

### Authentication Routes
- `GET /` - Public landing page
- `GET /login` - Login form
- `POST /login` - Process login credentials
- `GET /signup` - Registration form
- `POST /signup` - Create new user account
- `GET /logout` - Clear session and logout

### Feature Routes
- `GET /home` - User dashboard (requires authentication)
- `GET /weather-grid` - Real-time weather data and alerts
- `GET /api/get-ngos` - NGO map interface
- `GET /api/live-ngos` - JSON API for nearby NGOs (requires lat/lon parameters)
- `POST /api/contact-request` - Submit inquiry to NGO

## Data Security & Privacy

### Data Collection
This application collects:
- User account information (name, email, username)
- Location data (derived from IP address during session)
- User inquiries and contact requests

### Data Protection
- Passwords are stored in the MySQL database
- User sessions use secure Flask session management
- Location data is temporary and not permanently stored
- Recommendations for production deployment:
  - Hash passwords using werkzeug.security
  - Enable HTTPS with SSL/TLS certificates
  - Implement input validation and sanitization
  - Use parameterized SQL queries to prevent injection

### Production Security Checklist
- Change all default credentials
- Enable HTTPS with SSL/TLS certificates
- Set FLASK_ENV=production
- Configure CORS appropriately
- Implement rate limiting on API endpoints
- Enable logging and monitoring
- Regular database backups
- Keep dependencies updated

## Running on Different Environments

### Development Environment

```bash
python app.py
```

The application runs with debug mode enabled at `http://localhost:8000`

### Production Deployment

For production use, install and use Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Then configure:
- Reverse proxy (Nginx or Apache)
- SSL/TLS certificates
- Proper firewall rules
- Environment variables for production database

## Troubleshooting Common Issues

### Issue: Connection failed error at startup

**Cause**: MySQL database is not running or credentials are incorrect

**Solution**:
1. Verify MySQL service is running
2. Check `.env` file has correct DB_HOST, DB_USER, and DB_PASSWORD
3. Ensure the database exists with correct name

### Issue: ModuleNotFoundError when starting application

**Cause**: Python dependencies are not installed

**Solution**:
```bash
# Activate virtual environment first
pip install -r requirements.txt
```

### Issue: Port 8000 already in use

**Cause**: Another process is using port 8000

**Solution**: Either stop the other process or change port in app.py:
```python
if(__name__=="__main__"):
  app.run(debug=True, port=5000)  # Change 8000 to 5000 or another port
```

### Issue: Geolocation not working

**Cause**: No internet connection or IP-API service unavailable

**Solution**:
1. Check your internet connection
2. Try again in a few minutes
3. Manually test with curl: `curl http://ip-api.com/json/`

### Issue: Weather data not appearing

**Cause**: Open-Meteo API might be unavailable temporarily

**Solution**: Clear browser cache and refresh the page

## Version Information

This is Version 1.1 of the Emergency Relief & Disaster Management Platform.

**Important Note**: This version (1.1) is maintained in the versions_history branch for development tracking purposes. It is not the latest production version.

**To access the latest stable version**: Switch to the main branch for production-ready code with the most recent features.

```bash
# Switch to main branch for latest version
git checkout main
```

## Future Roadmap

### Coming in Later Versions
- Real-time push notifications for critical alerts
- Multi-language interface support
- Progressive Web App (PWA) for offline capability
- User profile customization and preferences
- NGO verification and rating system
- Advanced analytics and disaster tracking
- SMS and WhatsApp notifications
- Community crowdsourced information

## Contributing

To contribute improvements to this project:

1. Create a new feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and test thoroughly

3. Commit with clear messages:
```bash
git add .
git commit -m "Description of changes"
```

4. Push to your branch:
```bash
git push origin feature/your-feature-name
```

5. Submit a pull request for review

### Coding Guidelines
- Follow the existing code style and conventions
- Add descriptive comments for complex logic
- Test changes before committing
- Update README for new features
- Never commit sensitive credentials or secrets

## Support & Issues

If you encounter problems or have questions:

1. Check the Troubleshooting section above
2. Review error messages in the console
3. Verify all dependencies are installed correctly
4. Ensure database configuration is accurate
5. Check internet connectivity for external APIs

## License

This project is released under the MIT License. You are free to use, modify, and distribute this software. See the LICENSE file for complete terms.

---

**Version**: 1.1  
**Last Updated**: March 2026  
**Status**: Ready for version control and development tracking  
**Repository Branch**: versions_history/v1.1  
**Latest Production Branch**: main
