-- =========================================
-- DATABASE SETUP
-- =========================================
CREATE DATABASE IF NOT EXISTS abt_dev;
USE abt_dev;

-- =========================================
-- USERS TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Safe insert
INSERT INTO users (name, email)
SELECT 'Test User', 'test@example.com'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'test@example.com'
);

-- =========================================
-- SUPPORT OPTIONS
-- =========================================
CREATE TABLE IF NOT EXISTS support_options (
    id INT PRIMARY KEY AUTO_INCREMENT,
    type VARCHAR(50) NOT NULL,
    value VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Safe inserts
INSERT INTO support_options (type, value)
SELECT 'email', 'support@company.com'
WHERE NOT EXISTS (
    SELECT 1 FROM support_options WHERE type='email'
);

INSERT INTO support_options (type, value)
SELECT 'phone', '+91 9999999999'
WHERE NOT EXISTS (
    SELECT 1 FROM support_options WHERE type='phone'
);

-- =========================================
-- SUPPORT TICKETS
-- =========================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NULL,

    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    phone VARCHAR(20),

    message TEXT NOT NULL,

    status VARCHAR(50) DEFAULT 'OPEN',
    priority VARCHAR(20) DEFAULT 'MEDIUM',

    assigned_to_employee_id VARCHAR(64) NULL,
    assigned_by_admin_id VARCHAR(64) NULL,
    internal_note TEXT NULL,
    resolution_note TEXT NULL,
    resolved_by VARCHAR(64) NULL,
    resolved_at TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

ALTER TABLE support_tickets
    MODIFY COLUMN user_id VARCHAR(64) NULL;

SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND COLUMN_NAME = 'assigned_to_employee_id'
);
SET @sql = IF(@column_exists = 0, 'ALTER TABLE support_tickets ADD COLUMN assigned_to_employee_id VARCHAR(64) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND COLUMN_NAME = 'assigned_by_admin_id'
);
SET @sql = IF(@column_exists = 0, 'ALTER TABLE support_tickets ADD COLUMN assigned_by_admin_id VARCHAR(64) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND COLUMN_NAME = 'internal_note'
);
SET @sql = IF(@column_exists = 0, 'ALTER TABLE support_tickets ADD COLUMN internal_note TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND COLUMN_NAME = 'resolution_note'
);
SET @sql = IF(@column_exists = 0, 'ALTER TABLE support_tickets ADD COLUMN resolution_note TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND COLUMN_NAME = 'resolved_by'
);
SET @sql = IF(@column_exists = 0, 'ALTER TABLE support_tickets ADD COLUMN resolved_by VARCHAR(64) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND COLUMN_NAME = 'resolved_at'
);
SET @sql = IF(@column_exists = 0, 'ALTER TABLE support_tickets ADD COLUMN resolved_at TIMESTAMP NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =========================================
-- INDEXES (RUN ONLY FIRST TIME)
-- =========================================
-- This section is now safe to rerun repeatedly.

SET @idx_support_status_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND INDEX_NAME = 'idx_support_status'
);
SET @idx_support_created_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'support_tickets'
      AND INDEX_NAME = 'idx_support_created'
);

SET @sql = IF(
    @idx_support_status_exists = 0,
    'CREATE INDEX idx_support_status ON support_tickets(status)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
    @idx_support_created_exists = 0,
    'CREATE INDEX idx_support_created ON support_tickets(created_at)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =========================================
-- SAMPLE DATA
-- =========================================

INSERT INTO support_tickets (name, email, phone, message)
SELECT 'Aarav Sharma', 'aarav@example.com', '+919876543210', 'Need help with order'
WHERE NOT EXISTS (
    SELECT 1 FROM support_tickets WHERE email='aarav@example.com'
);

INSERT INTO support_tickets (user_id, name, email, phone, message)
SELECT 1, 'Test User', 'test@example.com', '+919999999999', 'Skin concern issue'
WHERE EXISTS (
    SELECT 1 FROM users WHERE id=1
)
AND NOT EXISTS (
    SELECT 1 FROM support_tickets WHERE email='test@example.com'
);

-- =========================================
-- TEST QUERIES
-- =========================================

SELECT * FROM support_tickets;
SELECT * FROM support_tickets WHERE status = 'OPEN';
