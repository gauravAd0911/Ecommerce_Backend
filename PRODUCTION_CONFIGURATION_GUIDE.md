# System Configuration Guide - Production Ready

## Overview
This guide explains how to configure the Lumia Backend system for production use with real authenticated data (no mock data).

## Architecture Overview

The system consists of microservices that authenticate users via JWT tokens issued by the Auth Service:

```
┌─────────────┐
│  Auth Service
│  (JWT Token Generation)
└──────┬──────┘
       │ Issues JWT tokens with user_id
       │
       ├─────────────┬─────────────┬─────────────┐
       ▼             ▼             ▼             ▼
   Payment Service  Order Service  User Profile  Other Services
   (Requires JWT)   (Requires JWT) (Requires JWT)
```

## Required Environment Variables

### 1. JWT Configuration
```env
# Generate a strong secret key (minimum 32 characters)
JWT_SECRET=your-super-secure-secret-key-min-32-chars

# JWT expires after 15 minutes (access token)
# Refresh tokens expire after 7 days
```

### 2. Twilio Configuration (for SMS OTP)
```env
TWILIO_ACCOUNT_SID=AC... (from Twilio Console)
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890 (your Twilio number)
```

### 3. Razorpay Configuration (for Payments)
```env
RAZORPAY_KEY=rzp_live_... (or rzp_test_...)
RAZORPAY_SECRET=your-razorpay-secret
RAZORPAY_WEBHOOK_SECRET=your-webhook-secret
```

### 4. Database Configuration
```env
DB_HOST=your-database-host
DB_USER=your-database-user
DB_PASSWORD=your-secure-database-password
DB_NAME=lumia_production

# For each service, create a separate database:
# - Auth Service: lumia_auth
# - Payment Service: lumia_payments
# - Order Service: lumia_orders
# - User Profile Service: lumia_users
# - etc.
```

### 5. CORS Configuration
```env
ALLOWED_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
```

## Step-by-Step Setup

### Step 1: Install Dependencies
```bash
# Auth Service
cd Auther_M2/Auther_M
pip install -r requirements.txt

# Payment Service
cd ../payment_app
pip install -r requirements.txt

# Order Service
cd ../order_services
pip install -r requirements.txt

# ... (repeat for other services)
```

### Step 2: Create Databases
```bash
# For MySQL/MariaDB
mysql -u root -p -e "CREATE DATABASE lumia_auth DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE DATABASE lumia_payments DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE DATABASE lumia_orders DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE DATABASE lumia_users DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Step 3: Initialize Database Schemas
```bash
# Auth Service
cd Auther_M2/Auther_M
alembic upgrade head

# Other services will auto-create tables on startup
```

### Step 4: Configure Environment Files
Create `.env` files in each service directory with required variables:

```bash
# .env template for Auth Service
JWT_SECRET=<your-secure-secret>
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
TWILIO_PHONE_NUMBER=<your-number>
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=<your-password>
DB_NAME=lumia_auth
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### Step 5: Start Services
```bash
# Terminal 1 - Auth Service
cd Auther_M2/Auther_M
uvicorn auth.main:app --reload --port 8001

# Terminal 2 - Payment Service
cd payment_app
uvicorn app.main:app --reload --port 8002

# Terminal 3 - Order Service
cd order_services
uvicorn app.main:app --reload --port 8003

# ... (start other services on different ports)
```

## Authentication Flow

### 1. User Registration
```bash
POST /auth/v1/signup/initiate
{
  "identifier": "user@example.com",  # email or phone
  "password": "SecurePassword123!"
}

# Response: { "otp_token": "..." }

# User receives OTP via SMS/Email

POST /auth/v1/signup/verify
{
  "otp_token": "...",
  "otp_code": "123456",
  "full_name": "John Doe"
}

# Response: { "access_token": "jwt...", "refresh_token": "jwt..." }
```

### 2. User Login
```bash
POST /auth/v1/login
{
  "identifier": "user@example.com",
  "password": "SecurePassword123!"
}

# Response: { "access_token": "jwt...", "refresh_token": "jwt..." }
```

### 3. Using JWT Token in Other Services
```bash
# Include JWT in Authorization header
GET /api/v1/users/me
Headers:
  Authorization: Bearer <access_token>

# Response: { "id": "...", "email": "...", "full_name": "..." }
```

## Testing the System

### Test 1: Verify Authentication is Required
```bash
# This should FAIL with 401
curl http://localhost:8002/api/v1/payments/orders

# This should SUCCEED with JWT
curl -H "Authorization: Bearer <valid_jwt>" \
     http://localhost:8002/api/v1/payments/orders
```

### Test 2: Create a Real User
```bash
# 1. Register
curl -X POST http://localhost:8001/auth/v1/signup/initiate \
  -H "Content-Type: application/json" \
  -d '{"identifier":"test@example.com","password":"Test123!"}'

# 2. Verify OTP (get OTP from SMS)
curl -X POST http://localhost:8001/auth/v1/signup/verify \
  -H "Content-Type: application/json" \
  -d '{
    "otp_token":"<from_initiate>",
    "otp_code":"<from_sms>",
    "full_name":"Test User"
  }'

# 3. Get user profile using JWT
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

### Test 3: Create Payment Order
```bash
curl -X POST http://localhost:8002/api/v1/payments/orders \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "amount": 50000,
    "currency": "INR"
  }'
```

## Deprecated/Removed Features

### ❌ No More Mock Users
- Removed auto-seeded "user-123" from user_profile_service
- All users must register through proper signup flow

### ❌ No More Mock SMS
- Removed DEVELOPMENT_MODE that printed OTP to console
- SMS now requires real Twilio credentials
- Fails with clear error if Twilio env vars missing

### ❌ No More Hardcoded Payment User IDs
- Payment endpoints no longer accept `user_id` query parameter
- User ID extracted from JWT token automatically

### ⚠️ Deprecated (Not Deleted, but Don't Use)
- `Auther_M2/docs/seed_test_users.py` - Legacy test data
- `Auther_M2/docs/seed_admin.py` - Legacy admin seed
- `payment_app/app/seed.py` - Legacy cart seed

## Troubleshooting

### "Not authenticated. Please provide a valid JWT token."
- Ensure you're including `Authorization: Bearer <token>` header
- Check that token hasn't expired (15 minutes for access token)
- Use refresh token to get new access token

### "Twilio environment variables are missing"
- Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- SMS cannot be mocked anymore

### "JWT_SECRET must be configured"
- Set `JWT_SECRET` environment variable in all services that use auth

### Database Connection Errors
- Verify database is running and accessible
- Check `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` are correct
- Ensure database user has proper permissions

## Production Deployment Checklist

- [ ] All `.env` files created with production values
- [ ] JWT_SECRET is strong (32+ chars, alphanumeric + symbols)
- [ ] Twilio credentials are valid for production
- [ ] Razorpay keys are for production (rzp_live_*), not test
- [ ] Database backups configured
- [ ] CORS allowed origins match your domain
- [ ] SSL/TLS certificates installed on API servers
- [ ] Rate limiting configured
- [ ] Logging and monitoring configured
- [ ] Error handling and alerting configured
- [ ] All deprecated seed scripts removed or documented

## Next Steps

1. ✅ All mock data has been removed
2. Configure real credentials for:
   - JWT (generate strong secret)
   - Twilio (SMS OTP)
   - Razorpay (payments)
   - Database (production database)
3. Update product image URLs in SQL seed files from placeholder.com to real CDN
4. Deploy services with production environment variables
5. Test end-to-end authentication and payment flows
6. Monitor logs and metrics in production
