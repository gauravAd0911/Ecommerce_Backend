# Lumia Backend

FastAPI microservices backend for the Lumia/Mahi Skin D2C commerce platform. The codebase is split by business capability: auth, catalog, cart, inventory, checkout, payment, orders, reviews, profile/address book, support, and notifications.

## At A Glance

| Service | Port | Main path | Database | Purpose |
| --- | ---: | --- | --- | --- |
| Auth | 8001 | `Auther_M2/Auther_M/auth` | `auth_m2_db` | Signup/login OTP, JWT sessions, password reset |
| Catalog | 8014 | `catalog_services` | `abt_dev` | Products, categories, storefront/admin catalog APIs |
| Cart | 8000 | `ecommerce_cart` | `ecommerce_db` | Guest/user carts and cart pricing |
| Inventory | 8002 | `Inventory_services` | `inventory_db` | Stock checks and optional reservations |
| Checkout | 8003 | `checkout_system` | `abt_dev` | Checkout validation, delivery checks, guest OTP, guest orders |
| Payment | 8006 | `payment_app/payment_app` | `payments_db` | Razorpay order/intent creation, verification, webhooks |
| Order | 8007 | `order_services` | `abt_dev` | Authenticated order creation/history/tracking |
| Notification | 8008 | `notification_service` | `abt_dev` | Devices, in-app notifications, email, WhatsApp, SMS |
| Profile | 8009 | `user_profile_service` | `abt_dev` | User profile and persistent address book |
| Support | 8010 | `support_service` | `abt_dev` | Customer support tickets/queries |
| Reviews | 8012 | `review_services` | `review_service` | Product reviews and verified-review checks |

## Local Requirements

- Python 3.10+
- MySQL 8+
- Service `.env` files configured with DB credentials and any provider secrets
- Razorpay keys in `payment_app/payment_app/app/config.py` environment variables when live payments are used

Each service is a standalone FastAPI app. Start only the services needed for the flow you are testing.

```powershell
# Examples
cd "Auther_M2\Auther_M"; python -m uvicorn auth.main:app --host 0.0.0.0 --port 8001 --reload
cd "checkout_system"; python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
cd "payment_app\payment_app"; python -m uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
cd "user_profile_service"; python -m uvicorn app.main:app --host 0.0.0.0 --port 8009 --reload
cd "notification_service"; python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload
```

OpenAPI docs are available at `http://localhost:<port>/docs`.

## Storefront Flow

1. Auth creates or resumes a customer session.
2. Catalog supplies products.
3. Cart stores selected products and quantities.
4. Checkout validates cart, inventory, and delivery address.
5. Payment creates a Razorpay intent/order and verifies the returned gateway result.
6. Order or guest checkout persists the final order after payment verification.
7. Profile stores reusable customer addresses.
8. Notification sends order/customer communication.

## Important Configuration

```env
# Inventory/checkout MVP behavior
ENABLE_STOCK_RESERVATION=false
DEDUCT_STOCK_ON_ORDER=true

# Payment service
RAZORPAY_KEY=...
RAZORPAY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

The current MVP keeps stock reservation optional and deducts stock when an order completes.

## Key APIs

### Auth Service `:8001`

Common endpoints live under `/api/v1/auth`. The auth service supports registration/login OTP flows, password reset, token refresh, and protected user identity. Use the OpenAPI docs for the exact request models because OTP contexts are validated by the auth service.

### Catalog Service `:8014`

```http
GET    /api/v1/products
GET    /api/v1/products/{product_id}
POST   /api/v1/admin/products
PATCH  /api/v1/admin/products/{product_id}
DELETE /api/v1/admin/products/{product_id}
GET    /api/v1/categories
```

### Checkout Service `:8003`

```http
POST /api/v1/checkout/validate
POST /api/v1/checkout/session
POST /api/v1/delivery/check
POST /api/v1/guest-checkout/request-verification
POST /api/v1/guest-checkout/verify
POST /api/v1/guest-orders
GET  /api/v1/guest-orders/{order_id}
```

Checkout payload example:

```json
{
  "items": [
    {
      "product_id": "product-id",
      "quantity": 2,
      "name": "Premium Cotton T-Shirt",
      "unit_price": 29.99,
      "stock_qty": 20
    }
  ],
  "address": {
    "full_name": "Customer Name",
    "email": "customer@example.com",
    "line1": "House / street",
    "line2": "Area",
    "city": "Mumbai",
    "state": "Maharashtra",
    "postal_code": "400001",
    "country": "IN",
    "phone": "9876543210"
  }
}
```

### Payment Service `:8006`

```http
POST /api/v1/payments/intent
POST /api/v1/payments/orders
POST /api/v1/payments/verify
GET  /api/v1/payments/{payment_reference}/status
POST /api/v1/payments/webhooks/razorpay
```

Frontend/mobile intent payload:

```json
{
  "amount": 776.99,
  "orderReference": "checkout-session-id",
  "methodLabel": "Razorpay",
  "reservationId": "reservation-id",
  "guestToken": "optional-guest-token",
  "currency": "INR",
  "receipt": "Mahi-123",
  "notes": {
    "userId": "user-id-or-guest-checkout",
    "email": "customer@example.com",
    "phone": "9876543210",
    "reservationId": "reservation-id"
  }
}
```

The `amount` is in major units for `/intent` when `orderReference`, `methodLabel`, or `reservationId` is present. The service converts it to paise for Razorpay.

### Order Service `:8007`

```http
POST /api/v1/orders
GET  /api/v1/orders
GET  /api/v1/orders/{order_id}
GET  /api/v1/orders/{order_id}/tracking
```

### User Profile And Address Book `:8009`

Authenticated address APIs use the bearer token first. For local service testing, the profile service also accepts `X-User-Id`.

```http
GET    /api/v1/users/me/addresses/
GET    /api/v1/users/me/addresses/{address_id}
POST   /api/v1/users/me/addresses/
PATCH  /api/v1/users/me/addresses/{address_id}
PATCH  /api/v1/users/me/addresses/{address_id}/default
DELETE /api/v1/users/me/addresses/{address_id}
```

Create address payload:

```json
{
  "full_name": "Customer Name",
  "phone": "9876543210",
  "address_line1": "House / building / street",
  "address_line2": "Landmark or area",
  "landmark": "Near metro",
  "city": "Mumbai",
  "state": "Maharashtra",
  "postal_code": "400001",
  "country": "India",
  "address_type": "Home",
  "is_default": true
}
```

Address rules implemented in code:

- `full_name`, `phone`, `address_line1`, `city`, `state`, and `postal_code` are required for create.
- `phone` must be a valid Indian 10-digit mobile number. A leading `91` country code is accepted.
- `postal_code` must be exactly 6 digits.
- First saved address becomes default when no default exists.
- Maximum saved address count is controlled by `MAX_ADDRESS_LIMIT`.
- `PATCH` supports partial updates and rejects null for required DB columns.

Compatibility routes also exist under `/account/addresses`.

### Notification Service `:8008`

```http
POST   /api/v1/notifications/devices/register
DELETE /api/v1/notifications/devices/{device_id}
POST   /api/v1/notifications
GET    /api/v1/notifications?user_id=user-id
PATCH  /api/v1/notifications/{notification_id}/read
POST   /api/v1/notifications/email
POST   /api/v1/notifications/whatsapp
POST   /api/v1/notifications/sms
```

Device registration:

```json
{
  "user_id": "user-id",
  "device_token": "device-token",
  "platform": "web"
}
```

Create in-app notification:

```json
{
  "user_id": "user-id",
  "title": "Order confirmed",
  "message": "Your order has been confirmed.",
  "type": "order_confirmation"
}
```

Email notification:

```json
{
  "type": "order_confirmation",
  "recipient": "customer@example.com",
  "data": {
    "orderId": "ORD-123",
    "customerName": "Customer Name",
    "orderTotal": 776.99,
    "items": [
      { "name": "Premium Cotton T-Shirt", "quantity": 1, "price": 29.99 }
    ]
  }
}
```

WhatsApp notification:

```json
{
  "type": "order_update",
  "recipient": "+919876543210",
  "message": "Your order has been shipped."
}
```

SMS notification:

```json
{
  "recipient": "+919876543210",
  "message": "Your order has been confirmed."
}
```

### Support Service `:8010`

Support APIs manage customer queries/tickets under the service's `/api` routes. Check `support_service/app/api/support_routes.py` and `/docs` for the exact request models.

### Review Service `:8012`

Review APIs support product review listing and create/update flows. Eligibility checks are service-owned so only valid buyers can review where configured.

## Frontend Environment Mapping

The D2C frontend can target each service independently:

```env
VITE_USE_MOCK_BACKEND=false
VITE_MAHI_AUTH_BASE_URL=http://localhost:8001
VITE_MAHI_PRODUCT_BASE_URL=http://localhost:8014
VITE_MAHI_CART_BASE_URL=http://localhost:8000
VITE_MAHI_CHECKOUT_BASE_URL=http://localhost:8003
VITE_MAHI_INVENTORY_BASE_URL=http://localhost:8002
VITE_MAHI_PAYMENT_BASE_URL=http://localhost:8006
VITE_MAHI_ORDER_BASE_URL=http://localhost:8007
VITE_MAHI_PROFILE_BASE_URL=http://localhost:8009
VITE_MAHI_SUPPORT_BASE_URL=http://localhost:8010
VITE_MAHI_NOTIFICATION_BASE_URL=http://localhost:8008
VITE_MAHI_REVIEW_BASE_URL=http://localhost:8012
VITE_PAYMENT_MODE=razorpay
VITE_RAZORPAY_KEY_ID=...
```

## Troubleshooting

| Problem | Likely cause | What to check |
| --- | --- | --- |
| Payment amount differs from checkout total | Frontend/backend pricing mismatch | Send shipping-inclusive `amount` to `/api/v1/payments/intent` and keep product prices as decimals |
| Address save returns 401 | Missing auth context | Send bearer token or local `X-User-Id` header |
| Address update returns 422 | Invalid partial payload | Do not send null for required fields; send only changed fields |
| Stock does not decrease | MVP stock flag off | Confirm `DEDUCT_STOCK_ON_ORDER=true` and restart checkout/order service |
| Notification endpoint returns provider error | Email/Twilio/WhatsApp env missing | Check notification service provider credentials |
| Frontend receives HTML instead of JSON | Wrong service base URL | Ensure each `VITE_MAHI_*_BASE_URL` points to a FastAPI service, not the Vite app |

## Notes For Contributors

- Keep external provider secrets in service `.env` files only.
- Keep payment verification on the backend; never expose Razorpay secret keys to the frontend.
- Treat checkout totals as decimal major units in frontend/API payloads and paise/minor units only inside Razorpay-facing payment service code.
- Prefer adding new API shapes through service schemas and OpenAPI docs so the frontend can normalize one stable contract.
