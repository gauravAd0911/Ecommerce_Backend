-- payment_app schema (MySQL / InnoDB)
--
-- Tables covered:
-- - carts
-- - payments
-- - payment_events
-- - orders
--
-- Design goals:
-- - Store money as DECIMAL (cart) or minor units INT (payments/orders).
-- - Idempotency support for provider order creation.
-- - Backend-only verification (never trust client-side success).
-- - Preserve reconciliation path using stored provider ids + events.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- Lightweight migrations (safe re-runs)
-- ------------------------------------------------------------
-- carts: rename legacy `unit_price` -> `price`, and ensure new columns exist.
SET @carts_exists := (
    SELECT COUNT(*)
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts'
);
SET @carts_price_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' AND COLUMN_NAME = 'price'
);
SET @carts_unit_price_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' AND COLUMN_NAME = 'unit_price'
);
SET @sql := (
    SELECT CASE
        WHEN @carts_exists = 0 THEN 'SELECT 1'
        WHEN @carts_price_exists = 1 THEN 'SELECT 1'
        WHEN @carts_unit_price_exists = 1 THEN
            'ALTER TABLE carts CHANGE COLUMN unit_price price DECIMAL(12, 2) NOT NULL DEFAULT 0.00'
        ELSE
            'ALTER TABLE carts ADD COLUMN price DECIMAL(12, 2) NOT NULL DEFAULT 0.00'
    END
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @carts_currency_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' AND COLUMN_NAME = 'currency'
);
SET @sql := (
    SELECT CASE
        WHEN @carts_exists = 0 OR @carts_currency_exists = 1 THEN 'SELECT 1'
        ELSE 'ALTER TABLE carts ADD COLUMN currency VARCHAR(10) NOT NULL DEFAULT ''INR'' AFTER price'
    END
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @carts_created_at_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' AND COLUMN_NAME = 'created_at'
);
SET @sql := (
    SELECT CASE
        WHEN @carts_exists = 0 OR @carts_created_at_exists = 1 THEN 'SELECT 1'
        ELSE 'ALTER TABLE carts ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP'
    END
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @carts_updated_at_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' AND COLUMN_NAME = 'updated_at'
);
SET @sql := (
    SELECT CASE
        WHEN @carts_exists = 0 OR @carts_updated_at_exists = 1 THEN 'SELECT 1'
        ELSE 'ALTER TABLE carts ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
    END
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS carts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    price DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    quantity INT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_carts_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    payment_reference VARCHAR(120) NOT NULL,
    provider ENUM('razorpay') NOT NULL,
    idempotency_key VARCHAR(80) NOT NULL,
    provider_order_id VARCHAR(64) NULL,
    provider_payment_id VARCHAR(64) NULL,
    amount_minor INT UNSIGNED NOT NULL,
    currency VARCHAR(10) NOT NULL,
    status ENUM('creating','created','pending','verified','failed','unknown') NOT NULL DEFAULT 'creating',
    provider_order_create_attempts INT UNSIGNED NOT NULL DEFAULT 0,
    provider_order_last_attempt_at DATETIME NULL,
    verified_at DATETIME NULL,
    failed_at DATETIME NULL,
    last_error VARCHAR(500) NULL,
    metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_payments_reference (payment_reference),
    UNIQUE KEY uq_payments_provider_idempotency (provider, idempotency_key),
    UNIQUE KEY uq_payments_provider_order (provider, provider_order_id),
    KEY ix_payments_provider_payment_id (provider_payment_id),
    KEY ix_payments_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payment_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    payment_id BIGINT UNSIGNED NULL,
    provider ENUM('razorpay') NOT NULL,
    provider_event_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    signature_verified TINYINT(1) NOT NULL,
    payload JSON NOT NULL,
    received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_payment_events_provider_event (provider, provider_event_id),
    KEY ix_payment_events_payment_id (payment_id),
    CONSTRAINT fk_payment_events_payment_id FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS orders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    order_number VARCHAR(40) NOT NULL,
    payment_reference VARCHAR(120) NULL,
    total_amount_minor INT UNSIGNED NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status ENUM('pending','paid','cancelled','failed') NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_orders_order_number (order_number),
    UNIQUE KEY uq_orders_payment_reference (payment_reference),
    KEY ix_orders_user_id (user_id),
    CONSTRAINT fk_orders_payment_reference FOREIGN KEY (payment_reference) REFERENCES payments(payment_reference) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- Useful operational queries (examples)
-- 1) Idempotent payment create lookup
-- SELECT * FROM payments WHERE provider='razorpay' AND idempotency_key='idem_123';
--
-- 2) Payment status (public)
-- SELECT payment_reference, status, provider_order_id, provider_payment_id, amount_minor, currency, updated_at
-- FROM payments
-- WHERE payment_reference='payref_123';
--
-- 3) Store provider webhook idempotently
-- INSERT INTO payment_events (payment_id, provider, provider_event_id, event_type, signature_verified, payload)
-- VALUES (123, 'razorpay', 'evt_abc', 'payment.captured', 1, JSON_OBJECT('raw', '...'));
--
-- 4) Reconciliation backlog (uncertain outcomes)
-- SELECT payment_reference, provider_order_id, status, updated_at
-- FROM payments
-- WHERE status IN ('creating','created','pending','unknown')
-- ORDER BY updated_at ASC
-- LIMIT 100;
