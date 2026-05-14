# Frontend Integration Guide for Payment Backend

This document outlines the requirements and specifications for the frontend to integrate with the payment backend API. The backend handles payment processing using Razorpay, supporting order creation, payment verification, and status checking.

## API Base URLs

- **Legacy API**: `/payment`
- **Modern API**: `/api/v1/payments`

All requests should be made to the appropriate base URL. The modern API is recommended for new integrations.

## Authentication

Currently, no authentication is required for the payment endpoints. However, ensure that requests are made over HTTPS in production.

## Endpoints

### 1. Create Payment Order (Modern API)

**Endpoint**: `POST /api/v1/payments/orders`

**Purpose**: Creates a new payment order with Razorpay.

**Request Headers**:
- `Content-Type: application/json`
- `Idempotency-Key` (optional): A unique key to ensure idempotent requests.

**Request Payload**:
```json
{
  "amount": 1000,
  "currency": "INR"
}
```

- `amount`: Integer, amount in minor units (e.g., paise for INR, so 1000 = ₹10.00). Must be greater than 0.
- `currency`: String, default "INR". Will be normalized to uppercase.

**Response**:
```json
{
  "success": true,
  "message": "Payment order created successfully.",
  "data": {
    "payment_reference": "pay_ref_123",
    "provider": "razorpay",
    "razorpay_order_id": "order_abc123",
    "amount": 1000,
    "currency": "INR",
    "key_id": "rzp_test_key"
  },
  "error": null
}
```

**Frontend Usage**: Use the `razorpay_order_id` and `key_id` to initialize Razorpay checkout on the frontend.

### 2. Create Payment Intent (Modern API)

**Endpoint**: `POST /api/v1/payments/intent`

**Purpose**: Creates a payment intent, flexible for different frontend payloads.

**Request Headers**:
- `Content-Type: application/json`
- `Idempotency-Key` (optional)

**Request Payload**: Flexible JSON object, but typically includes:
```json
{
  "amount": 10.00,
  "currency": "INR",
  "orderReference": "order_123",
  "reservationId": "res_456",
  "guestToken": true
}
```

- `amount`: Number, can be in major units (e.g., 10.00 for ₹10.00) or minor units depending on context.
- `currency`: String, default "INR".
- Other fields like `orderReference`, `reservationId` are stored in metadata.

**Response**: Varies based on whether it's a mobile intent or not.
- For mobile intent:
```json
{
  "success": true,
  "message": "Payment intent created successfully.",
  "data": {
    "id": "pay_ref_123",
    "amount": 10.00,
    "provider": "razorpay",
    "status": "created",
    "gatewayOrderId": "order_abc123",
    "currency": "INR"
  },
  "error": null
}
```
- Otherwise:
```json
{
  "success": true,
  "message": "Payment intent created successfully.",
  "data": {
    "id": "order_abc123",
    "payment_reference": "pay_ref_123",
    "provider": "razorpay",
    "amount": 1000,
    "currency": "INR",
    "key_id": "rzp_test_key"
  },
  "error": null
}
```

### 3. Verify Payment (Modern API)

**Endpoint**: `POST /api/v1/payments/verify`

**Purpose**: Verifies a payment after completion using Razorpay's signature.

**Request Payload**:
```json
{
  "payment_reference": "pay_ref_123",
  "razorpay_order_id": "order_abc123",
  "razorpay_payment_id": "pay_def456",
  "razorpay_signature": "signature_here"
}
```

- `payment_reference`: Optional, string.
- `razorpay_order_id`: Required, string.
- `razorpay_payment_id`: Required, string.
- `razorpay_signature`: Required, string.

Alternatively, can send `gatewayResult` object with the same fields.

**Response**:
```json
{
  "success": true,
  "message": "Payment verified successfully.",
  "data": {
    "payment_reference": "pay_ref_123",
    "paymentReference": "pay_ref_123",
    "status": "success",
    "provider_payment_id": "pay_def456",
    "paymentId": "pay_def456",
    "verified": true,
    "verifiedAt": "2023-10-01T12:00:00",
    "mode": "live",
    "order_id": 123,
    "order_number": "ORD_123"
  },
  "error": null
}
```

### 4. Get Payment Status (Modern API)

**Endpoint**: `GET /api/v1/payments/{payment_reference}/status`

**Purpose**: Retrieves the status of a payment.

**Query Parameters**:
- `reconcile`: Boolean, optional. If true, queries the provider for latest status.

**Response**:
```json
{
  "success": true,
  "message": "Payment status fetched successfully.",
  "data": {
    "payment_reference": "pay_ref_123",
    "provider": "razorpay",
    "status": "verified",
    "razorpay_order_id": "order_abc123",
    "provider_payment_id": "pay_def456",
    "amount": 1000,
    "currency": "INR",
    "verified_at": "2023-10-01T12:00:00",
    "failed_at": null,
    "updated_at": "2023-10-01T12:00:00"
  },
  "error": null
}
```

## Legacy Endpoints

For backward compatibility:

### Create Order (Legacy)

**Endpoint**: `GET /payment/create-order?user_id=1`

**Response**:
```json
{
  "key": "rzp_test_key",
  "amount": 1000,
  "currency": "INR",
  "razorpay_order_id": "order_abc123",
  "payment_reference": "pay_ref_123"
}
```

### Verify Payment (Legacy)

**Endpoint**: `POST /payment/verify`

**Request Payload**:
```json
{
  "razorpay_order_id": "order_abc123",
  "razorpay_payment_id": "pay_def456",
  "razorpay_signature": "signature_here"
}
```

**Response**:
```json
{
  "status": "success",
  "order_id": 123
}
```

## Error Handling

All endpoints return errors in the following format:
```json
{
  "success": false,
  "message": "Error message",
  "data": null,
  "error": {
    "code": 400,
    "details": "Additional details"
  }
}
```

Common HTTP status codes:
- 400: Bad Request (invalid payload)
- 404: Not Found (payment not found)
- 502: Bad Gateway (provider error)

## Integration Steps

1. **Create Order/Intent**: Call the create endpoint to get Razorpay order ID and key.
2. **Initialize Razorpay Checkout**: Use the returned data to set up Razorpay on the frontend.
3. **Handle Payment Completion**: After payment, collect `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`.
4. **Verify Payment**: Send verification request to confirm and update backend.
5. **Check Status**: Optionally poll the status endpoint for updates.

## Notes

- Amounts are in minor units (paise for INR) unless specified otherwise.
- Use idempotency keys for safe retries.
- Webhooks are handled automatically by the backend; frontend doesn't need to interact with them directly.
- Ensure CORS is configured if frontend is on a different domain (currently set to allow all origins).</content>
<parameter name="filePath">e:\Learning Projects\Lumia_Backend_updated\payment_app\frontend_integration_guide.md