CREATE DATABASE IF NOT EXISTS abt_dev;
USE abt_dev;

CREATE TABLE devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    device_token VARCHAR(255) NOT NULL,
    platform VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    title VARCHAR(255),
    message VARCHAR(500),
    type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Queries

-- Get notifications
SELECT * FROM notifications WHERE user_id = ?;

-- Mark as read
UPDATE notifications SET is_read = TRUE WHERE id = ?;

-- Delete device
DELETE FROM devices WHERE id = ?;
