-- Save India v1.0 - Database Setup Script
-- This script creates the necessary database and tables for the application

-- Create Database
CREATE DATABASE IF NOT EXISTS save_india_db;
USE save_india_db;

-- Create Users Table
-- This table stores user account information
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create indexes for better query performance
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);

-- Insert sample data (optional - for testing)
-- Note: In production, remove or comment out this section
-- INSERT INTO users (username, email, password, name) VALUES
-- ('testuser', 'test@example.com', 'testpass123', 'Test User');

-- Display created tables
SHOW TABLES;
SHOW COLUMNS FROM users;
