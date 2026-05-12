-- =============================================================================
-- catalog_service.sql
-- Catalog Service — single consolidated database file
-- Contains: table definitions, indexes, triggers, seed data, service queries
-- Database: MySQL 8.0+
-- Engine:   InnoDB  |  Charset: utf8mb4 / utf8mb4_unicode_ci
-- =============================================================================

-- =============================================================================
-- SECTION 0: DATABASE SETUP
-- =============================================================================

CREATE DATABASE IF NOT EXISTS abt_dev
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE abt_dev;

SET FOREIGN_KEY_CHECKS = 1;


-- =============================================================================
-- SECTION 1: TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: categories
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id          INT             NOT NULL AUTO_INCREMENT,
    name        VARCHAR(120)    NOT NULL,
    slug        VARCHAR(120)    NOT NULL,
    description TEXT                     DEFAULT NULL,
    image_url   VARCHAR(500)             DEFAULT NULL,
    parent_id   INT                      DEFAULT NULL,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    sort_order  SMALLINT        NOT NULL DEFAULT 0,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT uq_categories_slug   UNIQUE      (slug),
    CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id)
        REFERENCES categories (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Columns: id, name, slug, description, image_url, parent_id,
--          is_active, sort_order, created_at, updated_at


-- -----------------------------------------------------------------------------
-- Table: products
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id                  INT             NOT NULL AUTO_INCREMENT,
    category_id         INT             NOT NULL,
    name                VARCHAR(255)    NOT NULL,
    slug                VARCHAR(255)    NOT NULL,
    short_description   VARCHAR(500)             DEFAULT NULL,
    long_description    TEXT                     DEFAULT NULL,
    benefits            TEXT                     DEFAULT NULL,
    ingredients         TEXT                     DEFAULT NULL,
    price               DECIMAL(10, 2)  NOT NULL,
    compare_at_price    DECIMAL(10, 2)           DEFAULT NULL,
    size                VARCHAR(80)              DEFAULT NULL,
    skin_type           VARCHAR(80)              DEFAULT NULL,
    stock_quantity      INT             NOT NULL DEFAULT 0,
    availability        ENUM('in_stock','out_of_stock','low_stock')
                                        NOT NULL DEFAULT 'in_stock',
    is_featured         TINYINT(1)      NOT NULL DEFAULT 0,
    is_active           TINYINT(1)      NOT NULL DEFAULT 1,
    rating_average      DECIMAL(3, 2)   NOT NULL DEFAULT 0.00,
    rating_count        INT             NOT NULL DEFAULT 0,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT uq_products_slug     UNIQUE      (slug),
    CONSTRAINT chk_products_price   CHECK       (price >= 0),
    CONSTRAINT chk_products_compare CHECK       (compare_at_price IS NULL OR compare_at_price >= 0),
    CONSTRAINT chk_products_stock   CHECK       (stock_quantity >= 0),
    CONSTRAINT chk_products_rating  CHECK       (rating_average BETWEEN 0.00 AND 5.00),
    CONSTRAINT fk_products_category FOREIGN KEY (category_id)
        REFERENCES categories (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Columns: id, category_id, name, slug, short_description, long_description,
--          benefits, ingredients, price, compare_at_price, size, skin_type,
--          stock_quantity, availability, is_featured, is_active,
--          rating_average, rating_count, created_at, updated_at


-- -----------------------------------------------------------------------------
-- Table: product_images
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_images (
    id          INT             NOT NULL AUTO_INCREMENT,
    product_id  INT             NOT NULL,
    url         VARCHAR(500)    NOT NULL,
    alt_text    VARCHAR(255)             DEFAULT NULL,
    is_primary  TINYINT(1)      NOT NULL DEFAULT 0,
    sort_order  SMALLINT        NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    CONSTRAINT fk_product_images_product FOREIGN KEY (product_id)
        REFERENCES products (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Columns: id, product_id, url, alt_text, is_primary, sort_order


-- -----------------------------------------------------------------------------
-- Table: product_tags
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_tags (
    id          INT             NOT NULL AUTO_INCREMENT,
    product_id  INT             NOT NULL,
    tag         VARCHAR(80)     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_product_tags_product_tag UNIQUE      (product_id, tag),
    CONSTRAINT fk_product_tags_product     FOREIGN KEY (product_id)
        REFERENCES products (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Columns: id, product_id, tag


-- -----------------------------------------------------------------------------
-- Table: home_banners
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS home_banners (
    id          INT             NOT NULL AUTO_INCREMENT,
    title       VARCHAR(255)    NOT NULL,
    subtitle    VARCHAR(500)             DEFAULT NULL,
    image_url   VARCHAR(500)    NOT NULL,
    cta_text    VARCHAR(120)             DEFAULT NULL,
    cta_url     VARCHAR(500)             DEFAULT NULL,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    sort_order  SMALLINT        NOT NULL DEFAULT 0,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Columns: id, title, subtitle, image_url, cta_text, cta_url,
--          is_active, sort_order, created_at


-- =============================================================================
-- SECTION 2: INDEXES
-- =============================================================================

-- Note: Using conditional SQL to create indexes only if they don't exist (MySQL 5.7+ compatible)

-- Categories indexes
SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND INDEX_NAME='idx_categories_is_active');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_categories_is_active ON categories (is_active)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND INDEX_NAME='idx_categories_parent_id');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_categories_parent_id ON categories (parent_id)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Products indexes
SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_category_id');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_category_id ON products (category_id)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_is_active');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_is_active ON products (is_active)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_is_featured');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_is_featured ON products (is_featured)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_skin_type');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_skin_type ON products (skin_type)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_price');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_price ON products (price)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_active_featured');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_active_featured ON products (is_active, is_featured, rating_average)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_active_rating');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_active_rating ON products (is_active, rating_average)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exist := (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_active_created');
SET @sql := IF(@idx_exist=0, 'CREATE INDEX idx_products_active_created ON products (is_active, created_at)', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- FULLTEXT replaces PostgreSQL pg_trgm for keyword search
-- Add FULLTEXT index only if it doesn't already exist
SET @exist := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE table_schema = DATABASE()
      AND table_name   = 'products'
      AND index_name   = 'ft_products_search'
);
SET @sql := IF(@exist = 0,
    'ALTER TABLE products ADD FULLTEXT INDEX ft_products_search (name, short_description)',
    'SELECT ''ft_products_search already exists, skipping'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE INDEX IF NOT EXISTS idx_product_images_product_id    ON product_images (product_id);

CREATE INDEX IF NOT EXISTS idx_product_tags_product_id      ON product_tags  (product_id);
CREATE INDEX IF NOT EXISTS idx_product_tags_tag             ON product_tags  (tag);

CREATE INDEX IF NOT EXISTS idx_home_banners_is_active       ON home_banners  (is_active);


-- =============================================================================
-- SECTION 3: TRIGGERS  (updated_at is also handled by ON UPDATE CURRENT_TIMESTAMP
--                        in column definition; triggers add explicit audit trail)
-- =============================================================================

DROP TRIGGER IF EXISTS trg_categories_updated_at;
CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW
        SET NEW.updated_at = CURRENT_TIMESTAMP;

DROP TRIGGER IF EXISTS trg_products_updated_at;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
        SET NEW.updated_at = CURRENT_TIMESTAMP;


-- =============================================================================
-- SECTION 4: SEED DATA  (INSERT IGNORE skips duplicates on re-runs)
-- =============================================================================

INSERT IGNORE INTO categories (name, slug, description, sort_order) VALUES
    ('Moisturisers', 'moisturisers', 'Hydrating face and body creams',       1),
    ('Serums',       'serums',       'Targeted treatment serums',            2),
    ('Cleansers',    'cleansers',    'Gentle daily cleansers',               3),
    ('Sunscreens',   'sunscreens',   'SPF protection for all skin types',    4),
    ('Eye Care',     'eye-care',     'Treatments for the delicate eye area', 5),
    ('Toners',       'toners',       'Balancing and prep toners',            6);

INSERT IGNORE INTO home_banners (title, subtitle, image_url, cta_text, cta_url, sort_order) VALUES
    ('Summer Glow Sale',
     'Up to 30% off selected SPF',
     'https://cdn.example.com/banners/summer-glow.jpg',
     'Shop Now', '/products?category=sunscreens', 1),
    ('New: Retinol Serum',
     'Clinical-strength formula',
     'https://cdn.example.com/banners/retinol-serum.jpg',
     'Discover', '/products/retinol-serum', 2);


-- =============================================================================
-- SECTION 5: SERVICE QUERIES
-- Params use %(name)s style (aiomysql / PyMySQL named params).
-- MySQL uses LIKE + CONCAT instead of PostgreSQL ILIKE.
-- BOOLEAN = 1 / 0 instead of TRUE / FALSE.
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Q1  GET /api/v1/home — featured products
-- Param: %(limit)s INTEGER  default 10
-- ----------------------------------------------------------------------------
SELECT
    p.id,
    p.name,
    p.slug,
    p.short_description,
    p.price,
    p.compare_at_price,
    p.size,
    p.skin_type,
    p.availability,
    p.is_featured,
    p.rating_average,
    p.rating_count,
    p.category_id,
    (
        SELECT pi.url
        FROM   product_images pi
        WHERE  pi.product_id = p.id
        ORDER  BY pi.is_primary DESC, pi.sort_order
        LIMIT  1
    ) AS primary_image_url
FROM   products p
WHERE  p.is_active   = 1
  AND  p.is_featured = 1
ORDER  BY p.rating_average DESC
LIMIT  %(limit)s;


-- ----------------------------------------------------------------------------
-- Q2  GET /api/v1/home — top-level categories
-- Param: %(limit)s INTEGER  default 6
-- ----------------------------------------------------------------------------
SELECT id, name, slug, description, image_url, parent_id, sort_order
FROM   categories
WHERE  is_active  = 1
  AND  parent_id IS NULL
ORDER  BY sort_order, name
LIMIT  %(limit)s;


-- ----------------------------------------------------------------------------
-- Q3  GET /api/v1/home — active banners
-- Param: %(limit)s INTEGER  default 5
-- ----------------------------------------------------------------------------
SELECT id, title, subtitle, image_url, cta_text, cta_url, sort_order
FROM   home_banners
WHERE  is_active = 1
ORDER  BY sort_order
LIMIT  %(limit)s;


-- ----------------------------------------------------------------------------
-- Q4  GET /api/v1/products — total count for pagination
-- Optional params: %(q)s, %(category_slug)s, %(price_min)s,
--                  %(price_max)s, %(skin_type)s
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS total
FROM   products p
JOIN   categories c ON c.id = p.category_id
WHERE  p.is_active = 1
  AND  (%(q)s IS NULL
        OR  p.name              LIKE CONCAT('%%', %(q)s, '%%')
        OR  p.short_description LIKE CONCAT('%%', %(q)s, '%%'))
  AND  (%(category_slug)s IS NULL OR c.slug      = %(category_slug)s)
  AND  (%(price_min)s     IS NULL OR p.price    >= %(price_min)s)
  AND  (%(price_max)s     IS NULL OR p.price    <= %(price_max)s)
  AND  (%(skin_type)s     IS NULL OR p.skin_type = %(skin_type)s);


-- ----------------------------------------------------------------------------
-- Q5  GET /api/v1/products — product listing page  (price_asc example)
-- Params: %(q)s, %(category_slug)s, %(price_min)s, %(price_max)s,
--         %(skin_type)s, %(limit)s, %(offset)s
--
-- FULLTEXT alternative for keyword search (swap the LIKE block with):
--   AND  (%(q)s IS NULL
--         OR MATCH(p.name, p.short_description) AGAINST (%(q)s IN BOOLEAN MODE))
--
-- Swap ORDER BY for other sort options:
--   price DESC | rating_average DESC | created_at DESC | rating_count DESC
-- ----------------------------------------------------------------------------
SELECT
    p.id,
    p.name,
    p.slug,
    p.short_description,
    p.price,
    p.compare_at_price,
    p.size,
    p.skin_type,
    p.availability,
    p.is_featured,
    p.rating_average,
    p.rating_count,
    p.category_id,
    (
        SELECT pi.url
        FROM   product_images pi
        WHERE  pi.product_id = p.id
        ORDER  BY pi.is_primary DESC, pi.sort_order
        LIMIT  1
    ) AS primary_image_url
FROM   products p
JOIN   categories c ON c.id = p.category_id
WHERE  p.is_active = 1
  AND  (%(q)s IS NULL
        OR  p.name              LIKE CONCAT('%%', %(q)s, '%%')
        OR  p.short_description LIKE CONCAT('%%', %(q)s, '%%'))
  AND  (%(category_slug)s IS NULL OR c.slug      = %(category_slug)s)
  AND  (%(price_min)s     IS NULL OR p.price    >= %(price_min)s)
  AND  (%(price_max)s     IS NULL OR p.price    <= %(price_max)s)
  AND  (%(skin_type)s     IS NULL OR p.skin_type = %(skin_type)s)
ORDER  BY p.price ASC
LIMIT  %(limit)s
OFFSET %(offset)s;


-- ----------------------------------------------------------------------------
-- Q6  GET /api/v1/products/:product_id — product detail
-- Param: %(product_id)s INTEGER
-- ----------------------------------------------------------------------------
SELECT
    p.id, p.name, p.slug, p.short_description, p.long_description,
    p.benefits, p.ingredients, p.price, p.compare_at_price,
    p.size, p.skin_type, p.stock_quantity, p.availability,
    p.is_featured, p.rating_average, p.rating_count,
    p.category_id, p.created_at, p.updated_at
FROM   products p
WHERE  p.id       = %(product_id)s
  AND  p.is_active = 1;

-- Product images (run after Q6)
SELECT id, url, alt_text, is_primary, sort_order
FROM   product_images
WHERE  product_id = %(product_id)s
ORDER  BY is_primary DESC, sort_order;

-- Product tags (run after Q6)
SELECT tag
FROM   product_tags
WHERE  product_id = %(product_id)s
ORDER  BY tag;


-- ----------------------------------------------------------------------------
-- Q7  GET /api/v1/products/:product_id/related
-- Params: %(category_id)s INTEGER, %(product_id)s INTEGER, %(limit)s INTEGER
-- ----------------------------------------------------------------------------
SELECT
    p.id, p.name, p.slug, p.short_description,
    p.price, p.compare_at_price, p.size, p.skin_type,
    p.availability, p.is_featured, p.rating_average, p.rating_count,
    p.category_id,
    (
        SELECT pi.url
        FROM   product_images pi
        WHERE  pi.product_id = p.id
        ORDER  BY pi.is_primary DESC, pi.sort_order
        LIMIT  1
    ) AS primary_image_url
FROM   products p
WHERE  p.category_id = %(category_id)s
  AND  p.id         <> %(product_id)s
  AND  p.is_active   = 1
ORDER  BY p.rating_average DESC
LIMIT  %(limit)s;


-- ----------------------------------------------------------------------------
-- Q8  GET /api/v1/categories — full list
-- ----------------------------------------------------------------------------
SELECT id, name, slug, description, image_url, parent_id, sort_order
FROM   categories
WHERE  is_active = 1
ORDER  BY sort_order, name;


-- ----------------------------------------------------------------------------
-- Q9  GET /api/v1/products/filters — price range facet
-- ----------------------------------------------------------------------------
SELECT MIN(price) AS price_min, MAX(price) AS price_max
FROM   products
WHERE  is_active = 1;


-- ----------------------------------------------------------------------------
-- Q10  GET /api/v1/products/filters — distinct skin types
-- ----------------------------------------------------------------------------
SELECT DISTINCT skin_type
FROM   products
WHERE  is_active  = 1
  AND  skin_type IS NOT NULL
ORDER  BY skin_type;


-- =============================================================================
-- END OF FILE
-- =============================================================================