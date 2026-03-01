# Save India v1.2

A comprehensive disaster reporting and emergency response coordination platform designed to help users report natural disasters and connect with relief organizations in real-time.

## Features

### User Features
- User registration and authentication with secure password storage
- Disaster reporting with media upload capability (images and videos)
- Real-time geolocation-based reporting
- Weather monitoring across multiple points with alerts for heat waves, storms, and floods
- Find and contact nearby NGOs and relief organizations
- Report verification tracking

### Admin Features
- User management dashboard with blocking/unblocking capabilities
- Incident verification and management
- View all reported disasters with details
- Monitor user activities and reports
- Delete and modify incident records

### Technical Features
- Real-time weather data from Open-Meteo API
- NGO location discovery via OpenStreetMap Overpass API
- Geolocation detection from IP addresses
- Contact information database for emergency services
- MySQL database with relational schema
- Media storage for disaster documentation

## Prerequisites

Before running this application, ensure you have installed:
- Python 3.8 or higher
- MySQL Server
- pip (Python package manager)

## Installation

### Step 1: Clone or Download Repository
Clone the repository to your local machine:
```bash
git clone <repository-url>
cd version_1
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
```

Activate the virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Database

Create a new MySQL database:
```bash
mysql -u root -p
CREATE DATABASE Save_India;
EXIT;
```

### Step 5: Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit the `.env` file with your database credentials:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=Save_India
SECRET_KEY=your_secret_key_here
```

Generate a secure secret key for Flask:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 6: Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:8000`

## Database Schema

The application creates the following tables automatically:

### Users Table
- User authentication and profile management
- Role-based access control (USER/ADMIN)
- Account blocking capability
- Phone number and email storage

### Disasters Table
- Disaster report storage
- Media attachments (images/videos)
- Geographic coordinates
- Verification status tracking
- Reporter and admin information

## Default Test Credentials

When the application runs, you can use existing user accounts from your MySQL database. For testing, create a test account via the signup page.

Example for development:
- Username: testuser
- Password: password123 (must be at least 8 characters)

## API Endpoints

### Authentication
- `GET /` - Home page
- `POST /login` - User login
- `POST /signup` - User registration
- `GET /logout` - User logout

### Disaster Reporting
- `GET /report-disaster` - Disaster report form
- `POST /report-disaster` - Submit disaster report

### Weather
- `GET /weather-grid` - Real-time weather information and alerts

### NGO Services
- `GET /api/get-ngos` - NGO map interface
- `GET /api/live-ngos` - Fetch nearby NGOs via API
- `POST /api/contact-request` - Submit contact inquiry to NGO

### Admin Dashboard
- `GET /home` - Admin dashboard (ADMIN role only)
- `GET /get-all-users` - List all users
- `POST /block-user` - Block/unblock user account
- `GET /get-all-incidents` - View all disaster reports
- `POST /verify-incident` - Verify disaster incident
- `POST /delete-incident` - Delete incident record

## File Structure

```
version_1/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── ngos_contacts.json        # NGO contact database
├── README.md                 # This file
├── LICENSE                   # License information
├── static/                   # Static files
│   ├── style.css            # Main styles
│   └── script.js            # Frontend JavaScript
└── templates/               # HTML templates
    ├── index.html           # Main page
    ├── login.html           # Login page
    ├── signup.html          # Registration page
    ├── admin.html           # Admin dashboard
    ├── home.html            # User home
    ├── report_disaster.html # Disaster report form
    ├── weather.html         # Weather display
    ├── map.html             # NGO locator map
    └── index2.html          # Alternative index
```

## External APIs Used

1. **Open-Meteo Weather API** - Real-time weather data
   - Endpoint: `https://api.open-meteo.com/v1/forecast`
   - No authentication required

2. **IP-API** - Geolocation from IP address
   - Endpoint: `http://ip-api.com/json/`
   - No authentication required

3. **OpenStreetMap Overpass API** - NGO location data
   - Endpoint: `http://overpass-api.de/api/interpreter`
   - No authentication required

## Security Considerations

- Passwords are stored in the database (use bcrypt hashing in production)
- Environment variables should never be committed to version control
- .env file must be added to .gitignore
- Admin credentials should only be given to trusted personnel
- Media uploads should have size and type validation in production
- Use HTTPS in production environment

## Troubleshooting

### Database Connection Error
- Verify MySQL server is running
- Check database credentials in .env file
- Ensure Save_India database exists

### Port Already in Use
- Application runs on port 8000 by default
- Change port in app.py: `app.run(debug=True, port='8000')`

### Missing Dependencies
- Ensure virtual environment is activated
- Run: `pip install -r requirements.txt`

### Geolocation Not Working
- Check internet connectivity
- IP-API may have rate limiting from some networks

## Version Information

Version: 1.2
Status: Development history tracking
Latest Version: See main branch for latest stable release

This version is maintained for development history and reference. For production deployment and latest features, switch to the main branch.

## Contributing

For contribution guidelines, refer to the project's main branch documentation.

## Support

For issues or questions about this version, check the commit history in the git log for context and changes made during development.

## License

See LICENSE file for details.

---

Last Updated: March 2026
Version: 1.2