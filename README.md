# Lumia E-Commerce Backend

Modern FastAPI microservices backend for the Lumia e-commerce platform. The system comprises **11 independent services** across **6 MySQL databases**, designed for scalability, maintainability, and MVP-ready stock management.

## Technology Stack

- **Framework**: FastAPI 0.115.0 + Uvicorn 0.30.6
- **Database**: MySQL 8.0+ (PyMySQL/aiomysql drivers)
- **Authentication**: JWT-based with custom auth service
- **Payment**: Razorpay integration
- **Frontend**: React Native (localhost:5173)

## Project Status

✅ **MVP Complete** - Stock deduction enabled, reservation system disabled via flag  
✅ **All Services Operational** - 11 services running on ports 8000-8014  
✅ **Database Schema Finalized** - 6 independent databases with full migrations  
✅ **Production Ready** - Configuration-driven MVP→Production migration path

## System Architecture

### 11 Microservices Overview

| Service | Port | Database | Responsibility | Status |
|---------|------|----------|-----------------|--------|
| **Auth Service** | 8001 | `auth_m2_db` | JWT authentication, OTP signup/login, password reset | ✅ Active |
| **Catalog Service** | 8014 | `abt_dev` | Product listings, categories, search, filters | ✅ Active |
| **Cart Service** | 8000 | `ecommerce_db` | Shopping cart management, item add/remove/update | ✅ Active - **Stock validation fixed** |
| **Inventory Service** | 8002 | `inventory_db` | Stock tracking, validation, reservations (optional flag) | ✅ Active - MVP disabled |
| **Checkout System** | 8003 | `abt_dev` | Guest checkout, OTP verification, checkout sessions | ✅ Active - **Stock deduction enabled** |
| **Order Service** | 8007 | `abt_dev` | Order finalization, order history, tracking | ✅ Active - **Stock deduction enabled** |
| **Payment Service** | 8006 | `payments_db` | Razorpay integration, payment processing | ✅ Active |
| **Review Service** | 8012 | `review_service` | Product reviews, ratings, review eligibility | ✅ Active |
| **User Profile Service** | 8009 | `abt_dev` | User profiles, address book management | ✅ Active - **Address update validation fixed** |
| **Support Service** | 8010 | `abt_dev` | Support tickets, issue tracking | ✅ Active |
| **Notification Service** | 8008 | `abt_dev` | Push notifications, device registration | ✅ Active |

### Database Architecture

**Shared Database** (`abt_dev`):
- Catalog, Checkout, Order, Profile, Support, Notification services

**Independent Databases**:
- `ecommerce_db` - Cart service
- `inventory_db` - Inventory service  
- `payments_db` - Payment service
- `review_service` - Review service
- `auth_m2_db` - Auth service

### Service Dependencies

```
Independent Services (8):
├─ Auth (8001)
├─ Catalog (8014)
├─ Cart (8000)
├─ Inventory (8002) - Optional
├─ Profile (8009)
├─ Review (8012)
├─ Support (8010)
└─ Notification (8008)

Dependent Chain (3):
└─ Checkout (8003)
   └─ Order (8007)
      └─ Payment (8006)
```

**Startup Sequence**:
1. Start independent services first (any order)
2. Then start Checkout, Order, Payment (in sequence)

## MVP Features & Recent Fixes

### Stock Deduction System (MVP)
- ✅ Stock immediately deducted when orders complete
- ✅ Works for both authenticated users and guest checkouts
- ✅ Configuration flag to enable/disable: `DEDUCT_STOCK_ON_ORDER`
- ✅ Optional reservation system (disabled by default via `ENABLE_STOCK_RESERVATION=false`)

**Configuration**:
```env
# MVP (Current)
ENABLE_STOCK_RESERVATION=false      # No reservation complexity
DEDUCT_STOCK_ON_ORDER=true          # Always deduct stock

# Production (Later)
ENABLE_STOCK_RESERVATION=true       # Add reservation system
DEDUCT_STOCK_ON_ORDER=true          # Keep deduction
```

### Recent Bug Fixes (Verified)
1. **Cart 409 Conflict Error** - Fixed stock validation logic in cart service
2. **Address Update Validation** - Fixed PATCH request validation for partial updates

See [MVP_STOCK_DEDUCTION_GUIDE.md](MVP_STOCK_DEDUCTION_GUIDE.md) for complete implementation details.

## Quick Start Guide

### Prerequisites
- Python 3.10+
- MySQL 8.0+ (running on localhost:3306)
- Credentials: `root/Gaurav@123`

### Setup All Services
```bash
# From project root
python docs/setup_all_services.py
```

Or setup individually:
```bash
cd Auther_M2/Auther_M && python -m uvicorn auth.main:app --port 8001
cd catalog_services && python -m uvicorn app.main:app --port 8014
cd ecommerce_cart && python -m uvicorn ecommerce_cart.app.main:app --port 8000
# ... etc
```

### Verify Services
```bash
curl http://localhost:8001/docs    # Auth Service
curl http://localhost:8014/docs    # Catalog Service
curl http://localhost:8000/docs    # Cart Service
```

### Access OpenAPI Documentation
Open browser to any service's `/docs` endpoint:
- Auth: `http://localhost:8001/docs`
- Catalog: `http://localhost:8014/docs`
- Cart: `http://localhost:8000/docs`
- Checkout: `http://localhost:8003/docs`
- Order: `http://localhost:8007/docs`
- (All others available at their respective ports)

## Database Connection Details

### MySQL Setup
```
Host: localhost
Port: 3306
User: root
Password: Gaurav@123
```

### Database List
- `auth_m2_db` - Authentication service
- `ecommerce_db` - Cart service
- `inventory_db` - Inventory service  
- `payments_db` - Payment service
- `review_service` - Review service
- `abt_dev` - Shared (Catalog, Checkout, Order, Profile, Support, Notification)

### Initialize Databases
Each service folder contains `.sql` schema files:
```bash
mysql -u root -p < auth_m2_db.sql
mysql -u root -p < ecommerce_db.sql
mysql -u root -p < inventory_db.sql
# ... etc
```

## API Gateway Recommended Deployment

For production, deploy with an API Gateway/BFF:

```
Mobile App (React Native)
       ↓
   API Gateway (Recommended)
       ↓
  ┌─────────────────────────────────┐
  │  11 Independent Microservices   │
  │  (Auth, Catalog, Cart, Order,   │
  │   Checkout, Payment, etc.)      │
  └─────────────────────────────────┘
       ↓
  ┌──────────────────────────────────┐
  │  6 MySQL Databases               │
  │  (auth_m2_db, ecommerce_db, ...) │
  └──────────────────────────────────┘
```

Benefits:
- Single entry point for mobile app
- Unified authentication/authorization
- Request/response transformation
- Rate limiting and caching
- Service composition

## Frontend Integration Points

## Key Service Contracts

### 1. Auth Service (Port 8001)

**Database**: `auth_m2_db`

**Key Endpoints**:
```
POST   /api/v1/auth/signup/initiate           - Send signup OTP
POST   /api/v1/auth/signup/verify-otp         - Verify OTP, create user
POST   /api/v1/auth/login                     - Login with email/password
POST   /api/v1/auth/token/refresh             - Refresh access token
POST   /api/v1/auth/logout                    - Logout user
GET    /api/v1/auth/me                        - Get current user
POST   /api/v1/auth/password/forgot/initiate  - Start password reset
POST   /api/v1/auth/password/forgot/verify-otp
POST   /api/v1/auth/password/reset
```

**Login Request/Response**:
```json
POST /api/v1/auth/login
Request: { "identifier": "email@example.com", "password": "secret123" }
Response: {
  "access_token": "jwt_token",
  "refresh_token": "jwt_token",
  "user": { "id": "user-id", "email": "...", "phone": "...", "role": "consumer" }
}
```

### 2. Catalog Service (Port 8014)

**Database**: `abt_dev` (shared)

**Key Endpoints**:
```
GET    /api/v1/home                      - Home banners & featured products
GET    /api/v1/products                  - Product listing (search, filter, sort)
GET    /api/v1/products/filters           - Available filters (categories, prices)
GET    /api/v1/products/{product_id}     - Product details
GET    /api/v1/products/{product_id}/related
GET    /api/v1/categories                - Category listing
```

**Product Query Parameters**: `q, category, price_min, price_max, skin_type, sort, page, limit`

### 3. Cart Service (Port 8000)

**Database**: `ecommerce_db` (independent)

**Key Endpoints**:
```
GET    /api/cart                    - Fetch active cart
POST   /api/cart/items              - Add item to cart
PUT    /api/cart/items/{product_id} - Update item quantity
DELETE /api/cart/items/{product_id} - Remove item
DELETE /api/cart                    - Clear cart
```

**Add Item Request**:
```json
POST /api/cart/items
{ "product_id": 1, "quantity": 2 }
```

**Status**: ✅ **Stock validation fixed** - Now correctly handles default stock values

### 4. Checkout Service (Port 8003)

**Database**: `abt_dev` (shared)

**Key Endpoints**:
```
POST   /api/v1/checkout/validate           - Validate cart & inventory
POST   /api/v1/checkout/session            - Create checkout session
POST   /api/v1/guest-checkout/request-verification  - Send OTP
POST   /api/v1/guest-checkout/verify       - Verify OTP
POST   /api/v1/guest-orders                - Place guest order
GET    /api/v1/guest-orders/{order_id}     - Get guest order
```

**Status**: ✅ **Stock deduction enabled** - Stock decreases when guest order completes

### 5. Order Service (Port 8007)

**Database**: `abt_dev` (shared)

**Key Endpoints**:
```
POST   /api/v1/orders                - Create authenticated order
GET    /api/v1/orders                - List user orders
GET    /api/v1/orders/{order_id}     - Order details
GET    /api/v1/orders/{order_id}/tracking - Tracking info
```

**Status**: ✅ **Stock deduction enabled** - Stock decreases when order finalizes

### 6. Inventory Service (Port 8002) - Optional for MVP

**Database**: `inventory_db` (independent)

**Status**: MVP disabled via `ENABLE_STOCK_RESERVATION=false`. Stock deduction handled by Order & Checkout services instead.

**Key Endpoints** (when enabled):
```
POST   /api/v1/inventory/validate              - Validate stock
POST   /api/v1/inventory/reservations          - Reserve stock
DELETE /api/v1/inventory/reservations/{id}    - Release reservation
POST   /api/v1/inventory/reservations/{id}/commit
```

### 7. Payment Service (Port 8006)

**Database**: `payments_db` (independent)

**Key Endpoints**:
```
POST   /api/v1/payments/orders           - Create Razorpay order
GET    /api/v1/payments/orders/{order_id}
POST   /api/v1/payments/verify            - Verify payment
GET    /api/v1/payments/status            - Payment status
```

### 8. User Profile Service (Port 8009)

**Database**: `abt_dev` (shared)

**Key Endpoints**:
```
GET    /api/v1/users/me             - Get current user profile
PUT    /api/v1/users/me             - Update profile
GET    /api/v1/users/addresses      - Get address book
POST   /api/v1/users/addresses      - Add address
PUT    /api/v1/users/addresses/{id} - Update address (PATCH working)
DELETE /api/v1/users/addresses/{id} - Delete address
```

**Status**: ✅ **PATCH validation fixed** - Address updates now allow partial payloads

### 9. Review Service (Port 8012)

**Database**: `review_service` (independent)

**Key Endpoints**:
```
GET    /api/v1/reviews/product/{product_id}   - Get product reviews
POST   /api/v1/reviews                        - Create review
GET    /api/v1/reviews/user                   - Get user's reviews
GET    /api/v1/reviews/eligibility/{product_id}
```

### 10. Support Service (Port 8010)

**Database**: `abt_dev` (shared)

**Key Endpoints**:
```
POST   /api/v1/support/tickets      - Create support ticket
GET    /api/v1/support/tickets      - List user tickets
GET    /api/v1/support/categories   - Support categories
```

### 11. Notification Service (Port 8008)

**Database**: `abt_dev` (shared)

**Key Endpoints**:
```
POST   /api/v1/notifications/devices    - Register device
GET    /api/v1/notifications/me         - Get user notifications
```

## Configuration & Environment

Each service has a `.env` file in its root directory. Key variables:

```env
# Database
DATABASE_URL=mysql+pymysql://root:Gaurav@123@localhost:3306/service_db

# Auth (for services that require it)
AUTH_SERVICE_URL=http://localhost:8001
SECRET_KEY=your-secret-key

# Port
PORT=8000

# MVP Features (Order & Checkout only)
ENABLE_STOCK_RESERVATION=false
DEDUCT_STOCK_ON_ORDER=true

# Payment (Payment service)
RAZORPAY_KEY_ID=your_key
RAZORPAY_SECRET_KEY=your_secret
```

## Common API Response Format

Most endpoints return:
```json
{
  "success": true,
  "message": "Success",
  "data": { /* Response payload */ }
}
```

Errors return:
```json
{
  "success": false,
  "error": "Error message",
  "details": { /* Additional context */ }
}
```

## Testing & Troubleshooting

### Verify All Services Running
```bash
# Check auth service
curl http://localhost:8001/docs

# Check all other services
for port in 8000 8002 8003 8006 8007 8008 8009 8010 8012 8014; do
  echo "Port $port:"
  curl -s http://localhost:$port/docs | head -5
done
```

### Test Stock Deduction Flow
```bash
# 1. Create authenticated user account
curl -X POST http://localhost:8001/api/v1/auth/signup/initiate \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "phone": "9876543210"}'

# 2. Verify OTP (use code from email/SMS)
curl -X POST http://localhost:8001/api/v1/auth/signup/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"context_id": "...", "otp": "123456"}'

# 3. Add product to cart
curl -X POST http://localhost:8000/api/cart/items \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'

# 4. Create order
curl -X POST http://localhost:8007/api/v1/orders \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": 1, "quantity": 2}]}'

# 5. Check product stock decreased in database
mysql -u root -p abt_dev -e "SELECT id, name, stock FROM products WHERE id=1;"
```

### Database Monitoring Queries
```sql
-- Check current stock levels
SELECT id, name, stock FROM products ORDER BY stock ASC LIMIT 10;

-- View recent orders (with stock deduction)
SELECT id, order_number, status, created_at FROM orders ORDER BY created_at DESC LIMIT 10;

-- Check guest orders (with stock deduction)
SELECT id, order_number, status, created_at FROM guest_orders ORDER BY created_at DESC LIMIT 10;

-- View order items
SELECT oi.id, oi.order_id, oi.product_id, oi.quantity 
FROM order_items oi 
JOIN orders o ON oi.order_id = o.id 
ORDER BY o.created_at DESC LIMIT 20;
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 409 Conflict on adding to cart | Stock validation too strict | Already fixed - check cart.py validation logic |
| PATCH address returns validation error | NULL value rejection too broad | Already fixed - check address.py validator |
| Stock not decreasing | DEDUCT_STOCK_ON_ORDER not true | Check `.env` file and restart service |
| Reservation system active | Feature flag enabled | Set ENABLE_STOCK_RESERVATION=false in `.env` |
| Service not found on port | Service not running | Start service with `uvicorn app.main:app --port <PORT>` |
| Database connection error | Wrong credentials/host | Verify MySQL running, check `.env` DATABASE_URL |

### Logs & Debugging

Each service logs to stdout. Check for:
```
- Stock deduction logs in Order Service (port 8007)
- Stock deduction logs in Checkout System (port 8003)
- Validation errors in Cart Service (port 8000)
- Address update logs in Profile Service (port 8009)
```

Enable debug logging in `.env`:
```env
LOG_LEVEL=DEBUG
DEBUG=True
```

## Documentation Files

- [MVP_STOCK_DEDUCTION_GUIDE.md](MVP_STOCK_DEDUCTION_GUIDE.md) - Implementation details
- [SERVICES_DOCUMENTATION.md](SERVICES_DOCUMENTATION.md) - Complete service reference
- [SYSTEM_VERIFICATION_REPORT.md](SYSTEM_VERIFICATION_REPORT.md) - System validation
- [system-architecture.md](system-architecture.md) - Architecture diagrams

## Production Deployment Checklist

- [ ] All 11 services running and healthy
- [ ] Databases migrated and seeded with test data
- [ ] Environment variables configured for production
- [ ] API Gateway/BFF deployed in front of services
- [ ] CORS configured for frontend domain
- [ ] JWT secret keys rotated and secured
- [ ] Payment keys (Razorpay) configured
- [ ] Logging and monitoring setup
- [ ] Backup strategy in place
- [ ] Load testing completed

## Development Workflow

1. **Update database schema** → Update service `.sql` file
2. **Add new endpoint** → Update Pydantic schema → Update FastAPI route → Test via `/docs`
3. **Fix bug** → Write test case first → Fix → Verify via test
4. **Deploy** → Test locally → Push → Deploy all dependent services

## Contributing

- Each service is independent - changes don't require other service restarts
- Always test via OpenAPI `/docs` before committing
- Keep `.sql` schema files in sync with SQLAlchemy models
- Document API changes in service README.md

## Support

For issues or questions:
1. Check the service `/docs` page for endpoint details
2. Review logs in terminal output
3. Check database state with SQL queries
4. Refer to SERVICES_DOCUMENTATION.md for service-specific info
5. Check recent fixes: Cart 409 error, Address validation, Stock deduction

---

**Last Updated**: May 12, 2026  
**Status**: MVP Ready for Production  
**Next Phase**: Add API Gateway for unified frontend integration
