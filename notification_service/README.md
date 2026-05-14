# Notification Service

FastAPI service for in-app notifications, device registration, email, WhatsApp, and SMS.

## Features

- Device registration and management
- In-app notification storage
- Email delivery through SendGrid first, SMTP fallback
- WhatsApp Business API integration
- Twilio SMS integration
- Standard API response envelope

## Environment

Create `notification_service/.env` from `.env.example` and fill real values locally. Do not commit real provider credentials.

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=replace_me
DB_NAME=abt_dev

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=your_smtp_app_password
EMAIL_FROM=noreply@example.com
SENDGRID_API_KEY=your_sendgrid_api_key

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id

SECRET_KEY=replace_me
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Email behavior:

- If `SENDGRID_API_KEY` and `EMAIL_FROM` are configured, the service sends through SendGrid.
- If SendGrid is missing or returns an error, the service falls back to SMTP.
- SMTP uses `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `EMAIL_FROM`.

## Run

```bat
cd notification_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload
```

Open docs at:

- `http://127.0.0.1:8008/docs`
- `http://127.0.0.1:8008/openapi.json`

## Endpoints

```http
POST   /api/v1/notifications/devices/register
POST   /api/v1/notifications/devices
DELETE /api/v1/notifications/devices/{device_id}
POST   /api/v1/notifications
GET    /api/v1/notifications?user_id=user-id
PATCH  /api/v1/notifications/{notification_id}/read
POST   /api/v1/notifications/email
POST   /api/v1/notifications/whatsapp
POST   /api/v1/notifications/sms
```

## Examples

Register or refresh a device:

```json
{
  "user_id": "user-id",
  "device_token": "fcm_or_browser_token",
  "platform": "web"
}
```

Create an in-app notification:

```json
{
  "user_id": "user-id",
  "title": "Order confirmed",
  "message": "Your order has been confirmed.",
  "type": "order_confirmation"
}
```

Send an order confirmation email:

```json
{
  "type": "order_confirmation",
  "recipient": "customer@example.com",
  "data": {
    "customerName": "Customer Name",
    "orderId": "ORD-2026-001",
    "orderTotal": 776.99,
    "items": [
      { "name": "Premium Cotton T-Shirt", "quantity": 1, "price": 29.99 }
    ]
  }
}
```

Send WhatsApp:

```json
{
  "type": "order_update",
  "recipient": "+919876543210",
  "message": "Your order has been shipped."
}
```

Send SMS:

```json
{
  "recipient": "+919876543210",
  "message": "Your order has been confirmed."
}
```

## Notes

- Tables are created automatically when the app starts.
- Existing local tables with integer `user_id` columns are migrated to string-compatible `VARCHAR(128)` on startup.
- Device registration is idempotent for the same `user_id + device_token`.
- `notification_schema.sql` is available if you want to create the schema manually.
