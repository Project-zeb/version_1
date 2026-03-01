# Quick Start Guide

Get up and running with the Emergency Relief Platform in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- MySQL Server running
- Git (optional, for cloning)

## Quick Setup

### 1. Extract and Navigate

```bash
cd path/to/project
```

### 2. Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

Create database in MySQL:

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

### 5. Environment File

Copy and update configuration:

```bash
copy .env.example .env
```

Edit `.env` and add your MySQL credentials:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=expense_tracker_dbms
SECRET_KEY=your_secret_key_here
```

### 6. Run Application

```bash
python app.py
```

Open browser: `http://localhost:8000`

## First Steps

1. **Create Account**
   - Click Sign Up
   - Enter name, email, password
   - Click Register

2. **Login**
   - Use your credentials
   - Access dashboard

3. **Check Weather**
   - View current conditions
   - See active alerts

4. **Find Relief Organizations**
   - Click NGO map
   - Browse nearby organizations
   - Submit contact inquiry

## Common Issues

**Database Error?**
- Verify MySQL is running
- Check credentials in .env
- Ensure database exists

**Module Not Found?**
- Verify virtual environment is activated
- Run `pip install -r requirements.txt` again

**Port Already in Use?**
- Change port in app.py or close port 8000

## Next Steps

- Read full README.md for detailed documentation
- Check FEATURES.md for feature explanations  
- Review DEPLOYMENT.md for production setup

---

**Need help?** See README.md Troubleshooting section.
