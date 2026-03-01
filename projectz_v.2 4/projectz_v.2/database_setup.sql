-- ============================================================================
-- Project-Zeb Version 1.0 - Database Setup Script
-- ============================================================================
-- This SQL script initializes the database schema for the Save India
-- Disaster Management System (Version 1.0)
--
-- Supports both MySQL and SQLite
-- Last Updated: March 2026
-- ============================================================================

-- ============================================================================
-- SECTION 1: USER MANAGEMENT TABLES
-- ============================================================================

-- Users table: Stores user account information
-- Fields: User ID, Full Name, Username, Email, Password Hash, Role, Phone, Status, Timestamp
CREATE TABLE IF NOT EXISTS Users (
    User_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    username VARCHAR(30) UNIQUE NOT NULL,
    email_id VARCHAR(100) UNIQUE NOT NULL,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'USER') DEFAULT 'USER',
    phone VARCHAR(10),
    INDEX idx_users_email (email_id),
    INDEX idx_users_username (username),
    INDEX idx_users_role (role)
);

-- ============================================================================
-- SECTION 2: DISASTER INCIDENT REPORTING
-- ============================================================================

-- Disasters table: Stores disaster incident reports
-- Fields: Incident ID, Type, Location, Description, Media, Status, Reporter, Admin ID, Timestamps
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
    FOREIGN KEY (admin_id) REFERENCES Users(User_id) ON DELETE SET NULL,
    INDEX idx_disasters_type (disaster_type),
    INDEX idx_disasters_date (created_at),
    INDEX idx_disasters_status (verify_status),
    INDEX idx_disasters_location (latitude, longitude)
);

-- ============================================================================
-- SECTION 3: INTERNAL API INTEGRATION (Optional - for Version 2.0+)
-- ============================================================================

-- Alerts table: Stores external disaster alerts from official sources
-- Sources: NDMA SACHET, data.gov.in, MOSDAC, IMD, CWC
-- Note: This table is for the Internal API service integration
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(120) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255),
    severity VARCHAR(128),
    urgency VARCHAR(128),
    certainty VARCHAR(128),
    area TEXT,
    status VARCHAR(64),
    issued_at VARCHAR(64),
    effective_at VARCHAR(64),
    expires_at VARCHAR(64),
    headline TEXT,
    description TEXT,
    instruction TEXT,
    payload_json TEXT,
    fetched_at VARCHAR(64) NOT NULL,
    updated_at VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_alert_source_external_id (source, external_id),
    INDEX idx_alerts_issued_at (issued_at),
    INDEX idx_alerts_source (source)
);

-- Source runs table: Tracks last successful fetch from each alert source
CREATE TABLE IF NOT EXISTS source_runs (
    source VARCHAR(120) PRIMARY KEY,
    last_status VARCHAR(32) NOT NULL,
    last_attempt_at VARCHAR(64) NOT NULL,
    last_success_at VARCHAR(64),
    last_error TEXT,
    records_fetched INT DEFAULT 0,
    updated_at VARCHAR(64) NOT NULL
);

-- ============================================================================
-- SECTION 4: API AUTHENTICATION & SECURITY
-- ============================================================================

-- API Keys table: Stores API keys for internal/external integrations
-- Roles: INTERNAL (for main app), ADMIN (for administrative operations)
-- Used by Internal API service for secure communication
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_hash VARCHAR(128) NOT NULL UNIQUE,
    role VARCHAR(32) NOT NULL,
    label VARCHAR(255),
    created_at VARCHAR(64) NOT NULL,
    expires_at VARCHAR(64),
    revoked_at VARCHAR(64),
    last_used_at VARCHAR(64),
    updated_at VARCHAR(64) NOT NULL,
    INDEX idx_api_keys_role (role)
);

-- ============================================================================
-- SECTION 5: SAMPLE DATA (OPTIONAL - For Development/Testing)
-- ============================================================================

-- INSERT INTO Users (full_name, username, email_id, password_hash, role, phone)
-- VALUES ('Admin User', 'admin', 'admin@example.com', 'hashed_password_here', 'ADMIN', '9876543210');

-- INSERT INTO Users (full_name, username, email_id, password_hash, role, phone)
-- VALUES ('Test User', 'testuser', 'test@example.com', 'hashed_password_here', 'USER', '9876543211');

-- ============================================================================
-- SECTION 6: INDEXES FOR PERFORMANCE OPTIMIZATION
-- ============================================================================

-- Indexes are created within each table definition above for:
-- - User lookup by email and username
-- - Disaster queries by type, date, verification status, and location
-- - Alert queries by source and timestamp
-- - API key validation by role

-- ============================================================================
-- SECTION 7: DATABASE CONFIGURATION NOTES
-- ============================================================================

-- Character Set: UTF8MB4 (supports emoji and special characters)
-- Collation: utf8mb4_unicode_ci (for multilingual support)
--
-- To set for existing database:
-- ALTER DATABASE Save_India CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ============================================================================
-- SECTION 8: MIGRATION HISTORY
-- ============================================================================

-- Migration 0001 (2026-02-28): Create core tables (alerts, source_runs)
-- Migration 0002 (2026-02-28): Add API keys table for authentication

-- ============================================================================
-- END OF DATABASE SETUP SCRIPT
-- ============================================================================

-- USAGE INSTRUCTIONS:
-- 1. Create Database: CREATE DATABASE Save_India;
-- 2. Select Database: USE Save_India;
-- 3. Run this script: mysql -u root -p Save_India < database_setup.sql
--
-- For SQLite, use: sqlite3 app.db < database_setup.sql
-- (Note: SQLite syntax differs slightly - use INT without AUTO_INCREMENT,
--  use INTEGER PRIMARY KEY AUTOINCREMENT instead)
