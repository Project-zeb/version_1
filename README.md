# Save India - Version 1.0

**[SECURE] This is Version 1.0 - A historical release on branch `Ayaan-v1.0`**

A Flask-based disaster management application with weather alerts and user authentication. This version serves as the foundational release with core features.

> **[NOTE] For the latest features and improvements, please refer to **Version 2.0** which is available on the `main` branch.

---

## Features (v1.0)

### Core Authentication
[FEATURE] User registration with email validation
[FEATURE] Secure login with session management
[FEATURE] Password validation (minimum 8 characters)
[FEATURE] Session-based user authentication
[FEATURE] Logout functionality with session cleanup

### Weather & Location Features
[FEATURE] IP-based automatic location detection
[FEATURE] Real-time weather data via Open-Meteo API
[FEATURE] Weather grid generation (5-point radius analysis)
[FEATURE] Smart disaster alerts:
  - Heat wave alerts (temperature > 40°C)
  - Storm alerts (wind speed > 20 km/h)
  - Flood alerts (precipitation > 10mm)

### User Interface
[FEATURE] Clean, responsive web interface with Tailwind CSS
[FEATURE] Dedicated login/signup pages
[FEATURE] Dashboard with personalized greeting
[FEATURE] Weather information display
[FEATURE] Real-time alert notifications

---

## Installation & Setup

### Prerequisites
- **Python 3.8+** (3.9+ recommended)
- **MySQL Server 5.7+** or **MariaDB 10.3+**
- **pip** (Python package manager)
- **Git** (for version control)

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/Project-Zeb.git
cd Project-Zeb/versions_history/v1.0/version_1
```

### Step 2: Set Up Python Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up MySQL Database

#### Option A: Using Command Line (MySQL CLI)
```bash
# Log in to MySQL
mysql -u root -p

# Run the setup script
source database_setup.sql;

# Verify table creation
USE save_india_db;
SHOW TABLES;
SELECT * FROM users;
```

#### Option B: Using MySQL Workbench
1. Open MySQL Workbench
2. Open File → Open SQL Script → Select `database_setup.sql`
3. Execute the script (press Ctrl+Shift+Enter)
4. Verify database creation in the Schema tab

#### Option C: Using phpMyAdmin (Localhost)
1. Open `http://localhost/phpmyadmin`
2. Click "Import" tab
3. Choose `database_setup.sql` file
4. Click "Go" to execute

### Step 5: Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Open `.env` file and fill in your values:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=save_india_db
SECRET_KEY=your_secret_key_here
```

**Generate a strong SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 6: Run the Application
```bash
python app.py
```

The application will start on `http://localhost:8000`

---

## Database Schema (SQL)

### Users Table (`users`)
```sql
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, auto-incrementing |
| `username` | VARCHAR(50) | Unique username |
| `email` | VARCHAR(100) | Unique email address |
| `password` | VARCHAR(255) | Password (stored as plaintext in v1.0 - see security notes) |
| `name` | VARCHAR(100) | User's full name |
| `created_at` | TIMESTAMP | Account creation timestamp |

---

## API Endpoints

### Authentication Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Landing page |
| `/signup` | GET, POST | User registration |
| `/login` | GET, POST | User login |
| `/logout` | GET | Logout and clear session |
| `/home` | GET | Dashboard (protected) |

### Weather Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/weather-grid` | GET | Weather data with alerts (protected) |

---

## Security Features & Notes

[IMPLEMENTED] Security Features:
- SQL parameterized queries (prevents SQL injection)
- Session-based authentication
- Password length validation (minimum 8 characters)
- Environment variable usage for sensitive data
- `.gitignore` protection for `.env` file

[WARNING] Known Security Issues (Fixed in v2.0):
- Passwords stored as plaintext (should use bcrypt/hashing)
- No CSRF protection on forms
- No rate limiting on login attempts
- No API response validation
- No session timeout

**Recommendations for Production:**
1. [ALERT] **DO NOT** use this version in production without fixing password storage
2. Implement bcrypt for password hashing
3. Add CSRF tokens to all forms
4. Set up rate limiting (e.g., using Flask-Limiter)
5. Enable HTTPS/SSL certificates
6. Use environment-specific configurations
7. Set up comprehensive error logging
8. Implement database backups

---

## Dependencies

See [requirements.txt](requirements.txt) for complete dependency list:

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.1.3 | Web framework |
| mysql-connector-python | 9.6.0 | MySQL database driver |
| python-dotenv | 1.2.1 | Environment variable management |
| requests | 2.32.5 | HTTP requests (weather API) |
| Werkzeug | 3.1.6 | WSGI toolkit (Flask dependency) |
| Jinja2 | 3.1.6 | Template engine |

---

## Project Structure

```
version_1/
app.py                      # Main Flask application
database_setup.sql          # Database initialization script
requirements.txt            # Python dependencies
.env.example               # Environment template
.gitignore                 # Git ignore rules
README.md                  # This file
LICENSE                    # MIT License
DEPLOYMENT_CHECKLIST.md    # Pre-deployment checklist

templates/
  index.html             # Landing page
  login.html             # Login page
  signup.html            # Registration page
  home.html              # Dashboard
  weather.html           # Weather display
```

---

## Version History & Git Commits

### Version 1.0 Release Information
- **Branch:** `ayaan-v1.0`
- **Release Date:** March 2026
- **Status:** Historical Release / Legacy
- **Latest Active Version:** 2.0 (main branch)

### Key Commits in v1.0

1. **Initial Project Setup**
   - Flask application scaffold
   - Database connectivity
   - Basic authentication

2. **Authentication Implementation**
   - User registration and login
   - Session management
   - Password validation

3. **Weather Features**
   - Weather API integration (Open-Meteo)
   - Location detection via IP
   - Alert system implementation

4. **UI/UX**
   - HTML templates with Tailwind CSS
   - Responsive design
   - Dashboard and forms

5. **Security & Cleanup**
   - Removed hardcoded credentials
   - Added `.gitignore`
   - Code formatting and documentation
   - Production-ready settings (debug=False)

6. **Database Setup**
   - SQL initialization script
   - Table schema creation
   - Indexes for performance

### View Full Commit History
```bash
git log --oneline --all
git log --decorate --graph --oneline
```

---

## Testing the Application

### 1. Test User Registration
```
1. Navigate to http://localhost:8000/signup
2. Fill in: Name, Username, Email, Password (min 8 chars)
3. Click "Sign Up"
4. Should redirect to login page
```

### 2. Test User Login
```
1. Go to http://localhost:8000/login
2. Enter registered username and password
3. Click "Log In"
4. Should redirect to home/dashboard
```

### 3. Test Weather Features
```
1. On dashboard, click "Get Weather Data"
2. Application detects your location via IP
3. Displays current weather and alerts
4. Check weather.html for alerts
```

### 4. Test Session Management
```
1. Login successfully
2. Close browser/clear cookies
3. Access http://localhost:8000/home
4. Should redirect to login (session cleared)
```

---

## Troubleshooting

### Database Connection Error
```
Error: Database connection failed
Solution:
1. Verify MySQL is running: sudo service mysql status (Linux) or Services (Windows)
2. Check credentials in .env file
3. Ensure database_setup.sql was executed
4. Test connection: mysql -h localhost -u root -p
```

### Port Already in Use
```
Error: Address already in use
Solution:
# Find what's using port 8000:
lsof -i :8000 (Mac/Linux)
netstat -ano | findstr :8000 (Windows)

# Kill the process or change port in app.py:
app.run(debug=False, port=8001)
```

### Module Not Found
```
Error: ModuleNotFoundError: No module named 'flask'
Solution:
1. Activate virtual environment
2. Run: pip install -r requirements.txt
3. Verify: pip list | grep -i flask
```

### Secrets Module Error
```
Error: No module named 'secrets'
Solution:
# secrets is built-in Python 3.6+
# Generate SECRET_KEY with:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Related Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **MySQL Documentation:** https://dev.mysql.com/doc/
- **Open-Meteo API:** https://open-meteo.com/
- **IP-API:** https://ip-api.com/

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## Next Steps & Future Versions

This is Version 1.0, the foundational release. For enhanced features, improvements, and fixes:

### **Upgrade to Version 2.0 (Latest)**
```bash
# Switch to main branch with latest features
git checkout main
cd path/to/version_2

# Version 2.0 includes:
- Encrypted password storage (bcrypt)
- Enhanced UI/UX
- Additional features
- Security improvements
- Better error handling
- API response validation
```

---

## Support & Contributions

For issues, questions, or contributions:
1. Check [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. Review GitHub issues
3. Submit pull requests for improvements

---

**Last Updated:** March 2026
**Version:** 1.0 (Historical Release)
**Branch:** Ayaan-v1.0
**Status:** Stable (Legacy)