# Installation & Setup Guide - Save India v1.0

## Quick Start (5 minutes)

### For Experienced Developers:
```bash
# 1. Clone and navigate
git clone <repo-url>
cd version_1

# 2. Setup environment
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup database
mysql -u root -p < database_setup.sql

# 5. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 6. Run application
python app.py
```

---

## Detailed Setup Guide

### Part 1: System Requirements

Check your system:

```bash
# Python version (must be 3.8+)
python --version

# MySQL/MariaDB (must be running)
mysql --version
mysql -u root -p -e "SELECT VERSION();"

# pip and virtual environment
pip --version
python -m venv --help
```

**Expected Output:**
- Python: 3.8.0 or higher
- MySQL: 5.7+ or MariaDB 10.3+
- pip: Any recent version

---

### Part 2: Environment Setup
```bash
# Navigate to desired location
cd /path/to/projects

# Clone repository (if using Git)
git clone https://github.com/yourusername/Project-Zeb.git
cd Project-Zeb/versions_history/v1.0/version_1

# Or extract from ZIP
unzip version_1.zip
cd version_1
```

#### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate it:
# ============ WINDOWS ============
venv\Scripts\activate

# ============ macOS/LINUX ============
source venv/bin/activate

# Verify activation (should show "venv" in prompt)
which python  # or "where python" on Windows
```

#### Step 3: Install Python Packages
```bash
# Upgrade pip first (recommended)
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

**Should display:**
- Flask 3.1.3
- mysql-connector-python 9.6.0
- python-dotenv 1.2.1
- requests 2.32.5
- And other dependencies

---

### Part 3: Database Setup

#### Option A: Command Line Setup (Simple)

```bash
# 1. Open MySQL command line
mysql -u root -p

# 2. Type password when prompted
# (If no password, just press Enter)

# 3. Run the setup script
source /path/to/database_setup.sql;

# 4. Verify creation
USE save_india_db;
SHOW TABLES;
DESCRIBE users;
```

#### Option B: MySQL Workbench (GUI)

```
1. Open MySQL Workbench
2. Create connection to localhost
3. Double-click connection to open
4. File → Open SQL Script
5. Select database_setup.sql
6. Click ⚡ Execute (or Ctrl+Shift+Enter)
7. Check Schema tab for save_india_db
```

#### Option C: phpMyAdmin (Web Interface)

```
1. Open http://localhost/phpmyadmin
2. Login with your credentials
3. Click "Import" tab
4. Choose file → database_setup.sql
5. Scroll down, click "Go"
6. Check left panel for "save_india_db"
```

#### Option D: Python Script (Automated)

If you prefer to use Python to set up:

```python
# create_db.py
import mysql.connector

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_password"
)

cursor = conn.cursor()

# Read and execute SQL file
with open('database_setup.sql', 'r') as sql_file:
    sql_script = sql_file.read()
    
for statement in sql_script.split(';'):
    if statement.strip():
        try:
            cursor.execute(statement)
            conn.commit()
            print(f"✅ Executed: {statement[:50]}...")
        except Exception as e:
            print(f"❌ Error: {e}")

cursor.close()
conn.close()
print("\n✅ Database setup complete!")
```

**Run it:**
```bash
python create_db.py
```

---

### Part 4: Environment Configuration

#### Step 1: Copy Template File
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

#### Step 2: Edit Configuration
Open `.env` file in your text editor:

```env
# Database settings (match your MySQL setup)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=save_india_db

# Generate a strong SECRET_KEY
SECRET_KEY=your_generated_secret_key
```

#### Step 3: Generate SECRET_KEY
```bash
# Run this command and copy the output
python -c "import secrets; print(secrets.token_hex(32))"

# Example output:
# a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# Copy this value to .env:
# SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

#### Step 4: Verify Configuration
```bash
# On Windows
type .env

# On macOS/Linux
cat .env

# Should show:
# DB_HOST=localhost
# DB_USER=root
# DB_PASSWORD=...
# DB_NAME=save_india_db
# SECRET_KEY=...
```

---

### Part 5: Running the Application

#### Start the Application:
```bash
python app.py
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:8000
```

#### Access the Application:
1. Open browser: http://localhost:8000
2. Should see landing page with "Save India" title
3. Click "Login to Get Started"

#### Stop the Application:
```
Press Ctrl+C in terminal
```

---

## 🧪 Verification Checklist

After setup, verify everything works:

```bash
# ☑️ Database connection
# 1. Open MySQL and check:
mysql -u root -p
USE save_india_db;
SELECT COUNT(*) FROM users;
# Should show: 0

# ☑️ Python imports
# 2. Test imports:
python -c "import flask, mysql.connector, requests; print('✅ All imports work')"

# ☑️ Environment variables
# 3. Check .env is readable:
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DB_HOST'))"
# Should print: localhost

# ☑️ Application startup
# 4. Run app (Ctrl+C after startup):
python app.py
# Should show "Running on http://127.0.0.1:8000"
```

---

## Common Issues & Solutions

### Issue 1: MySQL Connection Error
```
Error: "Access denied for user 'root'@'localhost'"
```

**Solutions:**
```bash
# Check MySQL is running
sudo service mysql status  # Linux
brew services list         # macOS

# Start MySQL if not running
sudo service mysql start   # Linux
brew services start mysql  # macOS

# Test connection directly
mysql -h localhost -u root -p

# If password wrong, reset it following MySQL docs
```

### Issue 2: Port 8000 Already in Use
```
Error: "Address already in use"
```

**Solutions:**
```bash
# Option 1: Find and kill process
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -i :8000
kill -9 <PID>

# Option 2: Change port in app.py
# Change: app.run(debug=False, port=8000)
# To:     app.run(debug=False, port=8001)
```

### Issue 3: Module Not Found
```
Error: "ModuleNotFoundError: No module named 'flask'"
```

**Solutions:**
```bash
# Make sure virtual environment is activated
# (Look for "venv" in command prompt)

# If not, activate it:
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Then install again:
pip install -r requirements.txt
```

### Issue 4: .env File Not Loaded
```
Error: "NoneType" or credentials are None
```

**Solutions:**
```bash
# 1. Verify .env exists and has content:
ls -la .env  # or: dir .env

# 2. Check .env format (no spaces around =):
# CORRECT:   DB_HOST=localhost
# WRONG:     DB_HOST = localhost

# 3. Verify it's in project root:
pwd  # or: cd (make sure you're in right directory)
```

### Issue 5: Weather API Error
```
Error: "Could not detect location" or API timeout
```

**Solutions:**
```bash
# Check internet connection
ping 8.8.8.8  # or any public server

# IP-API might be blocked, test:
python -c "import requests; print(requests.get('http://ip-api.com/json/').json())"

# If blocked, use different IP API service
# (Available in Version 2.0)
```

---

## Verify Database Setup

After database creation, check tables:

```sql
-- Connect to database
USE save_india_db;

-- Show all tables
SHOW TABLES;

-- Describe users table
DESCRIBE users;

-- Should show columns:
-- | id         | int(11)      | NO   | PRI | NULL       | auto_increment |
-- | username   | varchar(50)  | NO   | UNI | NULL       |                |
-- | email      | varchar(100) | NO   | UNI | NULL       |                |
-- | password   | varchar(255) | NO   |     | NULL       |                |
-- | name       | varchar(100) | NO   |     | NULL       |                |
-- | created_at | timestamp    | NO   |     | CURRENT... |                |

-- Insert test user (optional)
INSERT INTO users (username, email, password, name) 
VALUES ('testuser', 'test@example.com', 'password123', 'Test User');

-- Verify insert
SELECT * FROM users;
```

---

## Additional Commands

### View Project Dependencies
```bash
pip list
pip show flask
```

### Update All Packages (Optional)
```bash
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### Uninstall Virtual Environment (Cleanup)
```bash
# Deactivate first
deactivate

# Remove folder
# Windows: rmdir /s venv
# Mac/Linux: rm -rf venv
```

### Run Python Interactively
```bash
python

# Then test imports:
>>> from flask import Flask
>>> import mysql.connector
>>> import requests
>>> print("All good!")
```

---

## Success Indicators

When everything is set up correctly:

1. ✅ `python --version` shows 3.8+
2. ✅ `mysql -u root -p -e "USE save_india_db; SHOW TABLES;"` shows users table
3. ✅ `pip list` shows Flask, mysql-connector-python, etc.
4. ✅ `.env` file exists with all required variables
5. ✅ `python app.py` runs without errors
6. ✅ Browser shows Welcome page at http://localhost:8000
7. ✅ Can sign up and login successfully

---

## Next Steps

After successful setup:

1. **Test the application** - Create an account and login
2. **Check weather features** - Click "Get Weather Data" on dashboard
3. **Review code** - Understand the structure
4. **Customize** - Modify templates or add features
5. **Deploy** - Follow deployment guide for production

---

## Need Help?

1. Check this guide again for common issues
2. Review logs: `python app.py` (watch for error messages)
3. Check [README.md](README.md) for full documentation
4. Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

---

**Last Updated:** March 2026
**Version:** 1.0
**Status:** Ready for Use
