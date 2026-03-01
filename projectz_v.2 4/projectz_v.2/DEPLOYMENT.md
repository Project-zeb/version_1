# DEPLOYMENT GUIDE - Version 1.0

**Last Updated**: March 2026  
**Version**: 1.0  
**Status**: Stable Release

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Production Deployment](#production-deployment)
3. [Database Configuration](#database-configuration)
4. [Google Cloud Platform (GCP)](#google-cloud-platform)
5. [HTTPS/SSL Configuration](#httpssl-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

```bash
# Check Python version (requires 3.8+)
python3 --version

# Check pip
pip3 --version

# Check MySQL (if using MySQL)
mysql --version

# Install required system packages (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3-pip python3-venv git
```

### Step 1: Clone Repository

```bash
git clone https://github.com/Project-zeb/version_1.git
cd version_1/projectz_v.2
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python3 -m venv .venv

# Activate venv (Linux/Mac)
source .venv/bin/activate

# Activate venv (Windows)
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create .env File

```bash
cat > .env << EOF
# Flask Configuration
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Database Configuration
PRIMARY_DB=sqlite
SQLITE_DB_PATH=app.db
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=password
DB_NAME=Save_India

# Server Configuration
PORT=5000
APP_URL_SCHEME=http
EOF
```

### Step 5: Run Application

```bash
python run.py
```

Access application at: `http://localhost:5000`

### Step 6: Create Test Admin User (Optional)

```bash
# Access MySQL
mysql -u root -p Save_India

# Insert admin user (execute in MySQL)
INSERT INTO Users (full_name, username, email_id, password_hash, role, phone)
VALUES ('Admin', 'admin', 'admin@example.com', 'hash_here', 'ADMIN', '9876543210');

EXIT;
```

---

## Production Deployment

### Prerequisites

- Ubuntu 20.04 LTS or newer
- Python 3.8+
- MySQL 5.7+
- Nginx
- Systemd

### Step 1: System Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    mysql-server \
    nginx \
    curl \
    wget \
    git

# Create app user
sudo useradd -m -s /bin/bash projectz
sudo su - projectz
```

### Step 2: Deploy Application

```bash
# As projectz user, clone repo
cd /home/projectz
git clone https://github.com/Project-zeb/version_1.git
cd version_1/projectz_v.2

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server
```

### Step 3: Configure Environment

```bash
# Create .env with production settings
cat > .env << EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
PRIMARY_DB=mysql
DB_HOST=localhost
DB_USER=projectz_user
DB_PASSWORD=strong_password_here
DB_NAME=Save_India
PORT=8000
APP_URL_SCHEME=https
EOF

# Restrict permissions
chmod 600 .env
```

### Step 4: Setup MySQL Database

```bash
# Login to MySQL as root
sudo mysql -u root -p

# Run these commands:
CREATE DATABASE Save_India CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'projectz_user'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON Save_India.* TO 'projectz_user'@'localhost';
FLUSH PRIVILEGES;
SHOW GRANTS FOR 'projectz_user'@'localhost';
EXIT;

# Import schema
mysql -u projectz_user -p Save_India < database_setup.sql

# Verify
mysql -u projectz_user -p -D Save_India -e "SHOW TABLES;"
```

### Step 5: Create Systemd Service

```bash
# Create service file
sudo cat > /etc/systemd/system/projectz-main-web.service << 'EOF'
[Unit]
Description=Save India Disaster Management System
After=network.target
After=mysql.service

[Service]
Type=notify
User=projectz
WorkingDirectory=/home/projectz/version_1/projectz_v.2
ExecStart=/home/projectz/version_1/projectz_v.2/.venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    run:app

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=projectz-web

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable projectz-main-web
sudo systemctl start projectz-main-web
sudo systemctl status projectz-main-web
```

### Step 6: Configure Nginx as Reverse Proxy

```bash
# Create Nginx config
sudo cat > /etc/nginx/sites-available/projectz.conf << 'EOF'
upstream projectz {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    client_max_body_size 20M;

    location / {
        proxy_pass http://projectz;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /home/projectz/version_1/projectz_v.2/static/;
        expires 30d;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/projectz.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

### Step 7: Verify Deployment

```bash
# Check service status
sudo systemctl status projectz-main-web

# Check logs
sudo journalctl -u projectz-main-web -f

# Test application
curl -I http://localhost:8000/health
curl -I http://yourdomain.com/health

# Verify Nginx
sudo systemctl status nginx
sudo nginx -t
```

---

## Database Configuration

### Supported Databases

#### SQLite (Development)
- **Pros**: No setup, file-based, portable
- **Cons**: Single connection, slower with concurrency
- **Use Case**: Development, testing, small scale

#### MySQL (Production)
- **Pros**: Multi-user, robust, scalable
- **Cons**: Requires setup, server management
- **Use Case**: Production deployment

### Creating Database Tables

#### Using SQL File (Recommended)

```bash
# MySQL
mysql -u root -p Save_India < database_setup.sql

# SQLite
sqlite3 app.db < database_setup.sql
```

#### Manual Table Creation

All table creation SQL is in `database_setup.sql`. Review and execute manually if needed.

### Database Backup

```bash
# MySQL backup
mysqldump -u projectz_user -p Save_India > backup_$(date +%Y%m%d_%H%M%S).sql

# Schedule daily backup (crontab)
0 2 * * * mysqldump -u projectz_user -p Save_India > /backups/save_india_$(date +\%Y\%m\%d).sql

# SQLite backup
cp app.db app.db.backup
```

### Database Restore

```bash
# MySQL restore
mysql -u projectz_user -p Save_India < backup_20260228_120000.sql

# SQLite restore
cp app.db.backup app.db
```

---

## Google Cloud Platform

### Prerequisites

- GCP account with billing enabled
- gcloud CLI installed
- Project created

### Step 1: Create VM Instance

```bash
# Set variables
PROJECT_ID="your-project-id"
INSTANCE_NAME="projectz-instance"
ZONE="asia-south1-a"
MACHINE_TYPE="e2-micro"

# Create VM
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --tags=projectz-web

# Reserve static IP
gcloud compute addresses create projectz-ip \
    --project=$PROJECT_ID \
    --region=asia-south1
```

### Step 2: Configure Firewall

```bash
# Allow HTTP/HTTPS
gcloud compute firewall-rules create projectz-allow-web \
    --project=$PROJECT_ID \
    --allow=tcp:80,tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=projectz-web

# Allow SSH (restricted to your IP)
gcloud compute firewall-rules create projectz-allow-ssh \
    --project=$PROJECT_ID \
    --allow=tcp:22 \
    --source-ranges=YOUR_IP/32 \
    --target-tags=projectz-web
```

### Step 3: SSH Into Instance

```bash
gcloud compute ssh $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE
```

### Step 4: Run Deployment Script

Once connected, execute the production deployment steps above.

---

## HTTPS/SSL Configuration

### Using Let's Encrypt (Free)

#### Install Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
```

#### Generate Certificate

```bash
sudo certbot certonly --standalone \
    -d yourdomain.com \
    -d www.yourdomain.com \
    --email admin@example.com \
    --agree-tos \
    --non-interactive
```

#### Update Nginx Config

```bash
sudo cat > /etc/nginx/sites-available/projectz.conf << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/projectz/version_1/projectz_v.2/static/;
    }
}
EOF

sudo nginx -t
sudo systemctl reload nginx
```

#### Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Enable auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Monitoring & Maintenance

### Application Logs

```bash
# View recent logs
sudo journalctl -u projectz-main-web -n 50

# Follow logs in real-time
sudo journalctl -u projectz-main-web -f

# Export logs to file
sudo journalctl -u projectz-main-web > app-logs.txt
```

### Database Monitoring

```bash
# Check MySQL status
sudo systemctl status mysql

# Monitor database size
mysql -u projectz_user -p -e "SELECT 
    table_name, 
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb 
FROM information_schema.tables 
WHERE table_schema = 'Save_India';"

# Check active connections
mysql -u projectz_user -p -e "SHOW PROCESSLIST;"
```

### Health Checks

```bash
# Application health
curl -s http://localhost:8000/health | jq .

# Database health
curl -s http://localhost:8000/health/db | jq .

# Check service
sudo systemctl is-active projectz-main-web
```

### Updates & Patches

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Update Python dependencies
source /home/projectz/version_1/projectz_v.2/.venv/bin/activate
pip install --upgrade -r requirements.txt
pip install --upgrade pip setuptools

# Restart service
sudo systemctl restart projectz-main-web
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u projectz-main-web -n 20

# Verify environment
sudo su - projectz
cd version_1/projectz_v.2
source .venv/bin/activate
cat .env
python run.py

# Check port binding
sudo netstat -tlnp | grep 8000
```

### Database Connection Error

```bash
# Test MySQL connection
mysql -u projectz_user -p -h 127.0.0.1 Save_India -e "SELECT 1;"

# Check credentials in .env
cat /home/projectz/version_1/projectz_v.2/.env

# Verify MySQL is running
sudo systemctl status mysql

# Check MySQL logs
sudo tail -50 /var/log/mysql/error.log
```

### Nginx Issues

```bash
# Test Nginx config
sudo nginx -t

# Check Nginx logs
sudo tail -50 /var/log/nginx/error.log
sudo tail -50 /var/log/nginx/access.log

# Verify proxy upstream
sudo netstat -tlnp | grep 8000
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Manual renewal
sudo certbot renew

# View certificate details
openssl s_client -connect yourdomain.com:443
```

### Performance Issues

```bash
# Check system resources
top
free -h
df -h

# Check database size
du -sh /var/lib/mysql/Save_India/

# Optimize MySQL
mysql -u projectz_user -p Save_India -e "OPTIMIZE TABLE Users, Disasters;"

# Increase Gunicorn workers (in systemd service)
# Change: --workers 4 to --workers 8
```

---

## Rollback Procedure

### If Deployment Fails

```bash
# Stop service
sudo systemctl stop projectz-main-web

# Revert to previous version
cd /home/projectz/version_1
git log --oneline -10
git revert HEAD  # or git checkout <commit-hash>

# Restart service
sudo systemctl start projectz-main-web

# Verify
sudo systemctl status projectz-main-web
```

### Database Rollback

```bash
# Stop application
sudo systemctl stop projectz-main-web

# Restore from backup
mysql -u projectz_user -p Save_India < backup_20260228_120000.sql

# Restart
sudo systemctl start projectz-main-web
```

---

## Post-Deployment Checklist

- [ ] Application starts without errors
- [ ] Database connection successful
- [ ] All endpoints respond correctly
- [ ] Admin dashboard accessible
- [ ] Disaster reporting works
- [ ] User authentication working
- [ ] Email notifications (if configured)
- [ ] Backups scheduled and tested
- [ ] Monitoring/alerts configured
- [ ] HTTPS/SSL verified
- [ ] Firewall rules applied
- [ ] Documentation updated

---

## Performance Optimization

### Gunicorn Configuration

Adjust workers based on CPU cores:

```bash
# For 1 CPU: 2-4 workers
# For 2 CPU: 4-8 workers
# Formula: (2 * CPU_count) + 1

# In systemd service:
ExecStart=/path/.venv/bin/gunicorn --workers 4 ...
```

### MySQL Optimization

```sql
-- Optimize tables
OPTIMIZE TABLE Users, Disasters, alerts, api_keys;

-- Analyze query performance
EXPLAIN SELECT * FROM Disasters WHERE verify_status = 1;

-- Check indexes
SHOW INDEX FROM Disasters;
```

### Caching Headers

Configure in Nginx for static files:

```nginx
location /static/ {
    alias /home/projectz/version_1/projectz_v.2/static/;
    expires 30d;
    add_header Cache-Control "public, max-age=2592000";
}
```

---

**Deployment completed successfully!**

For support, refer to main README.md or visit GitHub issues.
