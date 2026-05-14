# Lumia Backend - Complete Database Structure Guide

## Overview
This e-commerce backend uses a **microservices architecture** with multiple independent databases and services. Each service manages its own data.

---

## 📊 Database Breakdown by Service

### 1. **Authentication Service** (`Auther_M2`)
**Database Name:** `auth_m2_db`

| Table | Purpose | Key Data |
|-------|---------|----------|
| `users` | User accounts | `id`, `email`, `password_hash`, `role` (admin/consumer/vendor), `is_active`, `is_verified` |
| `otp_contexts` | OTP verification | `id`, `purpose` (signup/password_forgot), `user_id`, `email`, `phone`, `otp_hash`, `expires_at` |
| `auth_sessions` | Active sessions | `id`, `user_id`, `refresh_token_hash`, `created_at`, `last_used_at` |
| `password_reset_tokens` | Password reset | `id`, `user_id`, `token_hash`, `expires_at`, `used_at` |

---

### 2. **User Profile Service** (`user_profile_service`)
**Database Name:** Not specified (uses separate DB)

| Table | Purpose | Key Data |
|-------|---------|----------|
| `app_users` | User profiles | `id`, `email`, `full_name`, `phone`, `is_active`, `created_at`, `updated_at` |
| `addresses` | User addresses | `id`, `user_id`, `full_name`, `phone`, `address_line1/2`, `city`, `state`, `postal_code`, `country`, `is_default` |

---

### 3. **Catalog Service** (`catalog_services`)
**Database Name:** Not explicitly named (appears to be `catalog_db` or similar)

| Table | Purpose | Key Data |
|-------|---------|----------|
| `categories` | Product categories | `id`, `name`, `slug`, `description`, `image_url`, `parent_id`, `is_active`, `sort_order` |
| `products` | Product listings | `id`, `category_id`, `name`, `slug`, `price`, `compare_at_price`, `size`, `skin_type`, `stock_quantity`, `availability`, `is_featured`, `is_active`, `rating_average`, `rating_count` |
| `product_images` | Product images | `id`, `product_id`, `url`, `alt_text`, `is_primary`, `sort_order` |
| `product_tags` | Product tags | `id`, `product_id`, `tag` |
| `home_banners` | Homepage banners | `id`, `title`, `subtitle`, `image_url`, `cta_text`, `cta_url`, `is_active`, `sort_order` |

---

### 4. **Cart Service** (`ecommerce_cart`)
**Database Name:** `ecommerce_db`

| Table | Purpose | Key Data |
|-------|---------|----------|
| `products` | Product reference | `id`, `name`, `description`, `price`, `stock`, `image_url`, `is_active` |
| `carts` | Shopping carts | `id`, `user_id`, `is_active`, `created_at`, `updated_at` |
| `cart_items` | Items in cart | `id`, `cart_id`, `product_id`, `quantity`, `added_at`, `updated_at` |

---

### 5. **Payment Service** (`payment_app`)
**Database Name:** Not specified

| Table | Purpose | Key Data |
|-------|---------|----------|
| `carts` | Payment carts | `id`, `user_id`, `item_name`, `price`, `currency`, `quantity`, `created_at`, `updated_at` |
| `payments` | Payment records | `id`, `payment_reference`, `provider` (razorpay), `idempotency_key`, `provider_order_id`, `amount_minor`, `currency`, `status` (creating/created/pending/verified/failed) |
| `payment_events` | Webhook events | `id`, `payment_id`, `provider`, `provider_event_id`, `event_type`, `signature_verified`, `payload`, `received_at` |
| `orders` | Order records | `id`, `user_id`, `order_number`, `payment_reference`, `total_amount_minor`, `currency`, `status` (pending/paid/cancelled/failed) |

---

### 6. **Checkout System** (`checkout_system`)
**Database Name:** `abt_dev`

| Table | Purpose | Key Data |
|-------|---------|----------|
| `categories` | Categories | `id`, `name`, `slug`, `description`, `is_active` |
| `products` | Products | `id`, `category_id`, `name`, `slug`, `description`, `price`, `compare_price`, `sku`, `stock_qty`, `images` (JSON) |
| `guest_checkout_sessions` | Guest sessions | `id`, `guest_name`, `email`, `phone`, `purpose`, `email_verified`, `sms_verified`, `session_token`, `session_expires_at` |
| `guest_otps` | OTPs for guests | `id`, `session_id`, `channel` (email/sms), `purpose`, `code_hash`, `status`, `expires_at`, `verified_at` |
| `addresses` | Addresses | `id`, `full_name`, `line1`, `line2`, `city`, `state`, `postal_code`, `country`, `phone` |
| `guest_orders` | Guest orders | `id`, `session_id`, `order_number`, `guest_name`, `guest_email`, `guest_phone`, `shipping_address_id`, `billing_address_id`, `items` (JSON), `subtotal`, `shipping_amount`, `tax_amount`, `discount_amount`, `total_amount`, `status`, `payment_status` |
| `order_status_history` | Order status changes | `id`, `order_id`, `old_status`, `new_status`, `note`, `created_at` |

---

### 7. **Order Service** (`order_services`)
**Database Name:** `abt_dev`

| Table | Purpose | Key Data |
|-------|---------|----------|
| `orders` | Orders (auth & guest) | `id`, `order_number`, `user_id`, `guest_token`, `guest_email`, `guest_phone`, `payment_reference`, `total`, `status`, `payment_method`, `shipping_address`, `item_count`, `created_at` |
| `order_items` | Order item snapshots | `id`, `order_id`, `product_id`, `product_name`, `price`, `quantity`, `image_url` |
| `order_tracking` | Order timeline | `id`, `order_id`, `status`, `message`, `created_at` |

---

### 8. **Inventory Service** (`Inventory_services`)
**Database Name:** Not explicitly named

| Table | Purpose | Key Data |
|-------|---------|----------|
| `warehouses` | Warehouse locations | `id`, `name`, `location`, `created_at` |
| `products` | Product reference | `id`, `name` |
| `stock` | Stock levels | `id`, `product_id`, `warehouse_id`, `total_quantity`, `reserved_quantity`, `available_quantity` (computed), `created_at`, `updated_at` |
| `reservations` | Reserved stock | `id`, `product_id`, `warehouse_id`, `quantity`, `status` (ACTIVE/COMMITTED/RELEASED/EXPIRED), `expires_at`, `idempotency_key` |
| `stock_ledger` | Stock transactions | (Audit trail of stock movements) |

---

### 9. **Review Service** (`review_services`)
**Database Name:** Not explicitly named

| Table | Purpose | Key Data |
|-------|---------|----------|
| `products` | Product catalog | `product_id`, `name`, `created_at`, `updated_at` |
| `users` | User shadow table | `user_id`, `email`, `created_at`, `updated_at` |
| `orders` | Purchase verification | `order_id`, `user_id`, `product_id`, `status` (COMPLETED/CANCELLED), `purchased_at` |
| `reviews` | Product reviews | `review_id`, `product_id`, `user_id`, `rating` (1-5), `title`, `body`, `is_verified` (verified purchaser), `status` (PUBLISHED/HIDDEN/DELETED) |
| `vw_product_rating_summary` | Rating aggregation (VIEW) | Aggregated rating stats per product |

---

### 10. **Notification Service** (`notification_service`)
**Database Name:** `abt_dev`

| Table | Purpose | Key Data |
|-------|---------|----------|
| `devices` | User devices | `id`, `user_id`, `device_token`, `platform`, `created_at` |
| `notifications` | Notifications | `id`, `user_id`, `title`, `message`, `type`, `is_read`, `created_at` |

---

### 11. **Support Service** (`support_service`)
**Database Name:** `abt_dev`

| Table | Purpose | Key Data |
|-------|---------|----------|
| `users` | Support users | `id`, `name`, `email`, `created_at` |
| `support_options` | Support channels | `id`, `type` (email/phone), `value`, `is_active`, `created_at` |
| `support_tickets` | Support tickets | `id`, `user_id`, `name`, `email`, `phone`, `message`, `status`, `priority`, `assigned_to_employee_id`, `internal_note`, `resolution_note`, `resolved_at`, `created_at`, `updated_at` |

---

## 📍 Database Location Summary

| Database Name | Services | Tables |
|---------------|----------|--------|
| `auth_m2_db` | Authentication Service | 4 tables |
| `ecommerce_db` | Cart Service | 3 tables |
| `abt_dev` | Checkout, Order, Notification, Support | 13+ tables |
| Service-specific DBs | User Profile, Catalog, Payment, Inventory, Review | Multiple databases |

---

## 🔑 Key Relationships & Data Flow

### User Journey:
1. **Registration** → `auth_m2_db.users`
2. **Profile Setup** → `user_profile_service.app_users` + `addresses`
3. **Browse Products** → `catalog_services.products` + `categories`
4. **Add to Cart** → `ecommerce_db.carts` + `cart_items`
5. **Guest Checkout** → `abt_dev.guest_checkout_sessions` + `guest_orders`
6. **Payment** → `payment_app.payments` + `payment_events`
7. **Order Confirmation** → `abt_dev.orders` + `order_items` + `order_tracking`
8. **Notification** → `abt_dev.notifications`
9. **Post-Purchase Review** → Review service tables
10. **Support Ticket** → `abt_dev.support_tickets`

### Inventory Management:
- `Inventory_services.stock` tracks available quantities per warehouse
- `reservations` table holds items reserved during checkout
- `stock_ledger` maintains audit trail

---

## 💾 Important Notes

- **Database Isolation**: Each microservice has independent data storage for scalability
- **Shared Database (`abt_dev`)**: Used by checkout, orders, notifications, and support services
- **Idempotency Keys**: Payment and Inventory services use these for safe retries
- **Guest vs. Authenticated**: Separate tables for guest checkout (`guest_orders`) vs. user orders
- **JSON Fields**: Some services store complex data as JSON (e.g., `guest_orders.items`)
- **Computed Columns**: Inventory service uses `GENERATED ALWAYS AS` for `available_quantity`
