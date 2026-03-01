# Setup Instructions - Save India v1.2

This guide will help you set up and run the Save India disaster reporting application on your local machine.

## System Requirements

Before starting, ensure your system has:
- Windows, macOS, or Linux
- Python 3.8 or higher
- MySQL Server (version 5.7 or higher)
- At least 2 GB free disk space
- Internet connection for API calls

## Step-by-Step Installation

### 1. Download and Navigate to Project

Download this project and open a terminal in the project directory:

```bash
cd path/to/version_1
```

### 2. Create Python Virtual Environment

Creating a virtual environment isolates project dependencies from your system Python installation.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal after activation.

### 3. Install Required Packages

With the virtual environment activated:

```bash
pip install -r requirements.txt
```

This installs all dependencies including Flask, MySQL connector, and API libraries.

### 4. Set Up MySQL Database

**Open MySQL Command Line:**

**Windows (using MySQL Command Line Client):**
```bash
mysql -u root -p
```

**macOS/Linux (using terminal):**
```bash
mysql -u root -p
```

**Create the database:**

```sql
CREATE DATABASE Save_India;
EXIT;
```

Replace `root` with your MySQL username if different.

### 5. Configure Environment Variables

Copy the example environment file to create your configuration:

**Windows:**
```bash
copy .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

Edit the `.env` file with a text editor and update with your MySQL credentials:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=Save_India
SECRET_KEY=your_secret_key_here
```

**To generate a secure SECRET_KEY**, run in Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output into the SECRET_KEY field in .env

### 6. Start the Application

With your virtual environment activated:

```bash
python app.py
```

You should see output showing the app is running. Open your web browser and navigate to:

```
http://localhost:8000
```

## First Time Setup

### Create an Admin Account

1. Click "Sign Up"
2. Fill in the registration form
3. Select "ADMIN" as the role (for testing purposes)
4. Password must be at least 8 characters
5. Click Sign Up

### Create a Regular User Account

1. Repeat steps 1-4 above but select "USER" as the role

## Troubleshooting

### MySQL Connection Error

**Problem:** "Connection refused" or "Can't connect to MySQL server"

**Solution:**
- Ensure MySQL Server is running
  - Windows: Check Services application
  - macOS: MySQL usually runs automatically
  - Linux: Run `sudo service mysql start` or `sudo systemctl start mysql`
- Verify credentials in .env file match your MySQL setup
- Check if database `Save_India` was created

### Port 8000 Already in Use

**Problem:** "Address already in use"

**Solution:**
Change the port in app.py, line 547:
```python
app.run(debug=True, port='8001')
```

### Module Not Found Error

**Problem:** "ModuleNotFoundError: No module named 'flask'"

**Solution:**
- Ensure virtual environment is activated (you should see `(venv)` in terminal)
- Run `pip install -r requirements.txt` again

### API features not working

**Problem:** Weather or NGO features not working

**Solution:**
- Check internet connection
- API rate limits may apply
- Check browser console (F12) for specific errors

## Creating Test Data

### Manual Test

1. Log in with your admin account
2. Go to "Report Disaster" page
3. Fill in disaster details
4. Admin reports are auto-verified
5. Regular user reports need admin verification

## Database Reset

To clear all data and start fresh:

**In MySQL:**
```sql
DROP DATABASE Save_India;
CREATE DATABASE Save_India;
```

Then restart the application - tables will be recreated automatically.

## File Locations

Important files in the project:

- `app.py` - Main application file
- `.env` - Your local configuration (never commit this)
- `requirements.txt` - All Python dependencies
- `templates/` - HTML files for all pages
- `static/` - CSS and JavaScript files
- `ngos_contacts.json` - Database of NGO contact information

## Running in Production

This application is configured for development. For production deployment:

1. Set `debug=False` in app.py
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Use HTTPS with valid SSL certificates
4. Store passwords securely with bcrypt hashing
5. Use environment-specific configuration management

## Getting Help

If you encounter issues:

1. Check the terminal output for error messages
2. Look at the troubleshooting section above
3. Verify all prerequisites are installed
4. Ensure .env file is properly configured
5. Check that MySQL database and tables were created

## Version Information

This is version 1.2 - a development history version.

Latest version: Check the main branch for the most recent stable release.

---

Setup Date: March 2026
Version: 1.2
