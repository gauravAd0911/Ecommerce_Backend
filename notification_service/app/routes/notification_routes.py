from typing import Annotated, Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.notification_model import Device
from app.schemas.notification_schema import (
    DeviceRegister,
    NotificationCreate,
    NotificationResponse,
    APIResponse,
)
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService
from app.services.twilio_service import TwilioService
from app.templates.email_templates import EmailTemplates


router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"]
)


# -------------------------------
# Dependency
# -------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session for each request.
    Ensures proper cleanup after request lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


# -------------------------------
# Device APIs
# -------------------------------
@router.post("/devices/register", status_code=status.HTTP_201_CREATED)
@router.post("/devices", status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceRegister, db: DBSession):
    """
    Register or refresh a user device for notifications.
    """
    device = (
        db.query(Device)
        .filter(
            Device.user_id == payload.user_id,
            Device.device_token == payload.device_token,
        )
        .first()
    )
    message = "Device registered successfully"

    if device:
        device.platform = payload.platform
        message = "Device registration refreshed successfully"
    else:
        device = Device(
            user_id=payload.user_id,
            device_token=payload.device_token,
            platform=payload.platform,
        )
        db.add(device)

    db.commit()
    db.refresh(device)

    return APIResponse(
        success=True,
        message=message,
        data={
            "device_id": device.id,
            "user_id": device.user_id,
            "device_token": device.device_token,
            "platform": device.platform,
        }
    )


@router.delete("/devices/{device_id}", status_code=status.HTTP_200_OK)
def delete_device(device_id: int, db: DBSession):
    """
    Remove a registered device.
    """
    device = db.get(Device, device_id)

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "Device not found",
                "error": {
                    "code": "DEVICE_NOT_FOUND",
                    "message": "The specified device does not exist"
                }
            }
        )

    db.delete(device)
    db.commit()

    return APIResponse(
        success=True,
        message=f"Device {device_id} removed successfully"
    )


# -------------------------------
# Notification APIs
# -------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, db: DBSession):
    """
    Create a notification for a user.
    """
    notification = NotificationService.create_notification(
        db=db,
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        type_=payload.type,
    )
    return APIResponse(
        success=True,
        message="Notification created successfully",
        data=NotificationResponse.model_validate(notification)
    )


@router.get("")
def get_notifications(user_id: str, db: DBSession):
    """
    Fetch all notifications for a given user.
    """
    notifications = NotificationService.get_notifications(db, user_id)
    return APIResponse(
        success=True,
        message="Notifications retrieved successfully",
        data=[NotificationResponse.model_validate(n) for n in notifications]
    )


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: DBSession):
    """
    Mark a notification as read.
    """
    notification = NotificationService.mark_as_read(db, notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "Notification not found",
                "error": {
                    "code": "NOTIFICATION_NOT_FOUND",
                    "message": "The specified notification does not exist"
                }
            }
        )

    return APIResponse(
        success=True,
        message="Notification marked as read",
        data=NotificationResponse.model_validate(notification)
    )


# -------------------------------
# Email APIs
# -------------------------------
@router.post("/email")
def send_email_notification(payload: dict, db: DBSession):
    """
    Send email notification.
    Expected payload: {
        "type": "order_confirmation",
        "recipient": "user@example.com",
        "data": {
            "orderId": "order-123",
            "customerName": "John Doe",
            "orderTotal": 2740,
            "items": [...]
        }
    }
    """
    email_service = EmailService()
    notification_type = payload.get("type")
    recipient = payload.get("recipient")
    data = payload.get("data", {})

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Recipient email is required",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "recipient field is required"
                }
            }
        )

    # Generate email content based on type
    if notification_type == "order_confirmation":
        html_content, text_content = EmailTemplates.order_confirmation(
            customer_name=data.get("customerName", "Valued Customer"),
            order_id=data.get("orderId", "N/A"),
            order_total=data.get("orderTotal", 0),
            items=data.get("items", [])
        )
        subject = f"Order Confirmation - {data.get('orderId', 'N/A')}"

    elif notification_type == "order_shipped":
        html_content, text_content = EmailTemplates.order_shipped(
            customer_name=data.get("customerName", "Valued Customer"),
            order_id=data.get("orderId", "N/A"),
            tracking_number=data.get("trackingNumber")
        )
        subject = f"Order Shipped - {data.get('orderId', 'N/A')}"

    elif notification_type == "password_reset":
        html_content, text_content = EmailTemplates.password_reset(
            customer_name=data.get("customerName", "Valued Customer"),
            reset_link=data.get("resetLink", "#")
        )
        subject = "Password Reset Request"

    else:
        # Generic email
        html_content = f"<h1>{data.get('title', 'Notification')}</h1><p>{data.get('message', '')}</p>"
        text_content = data.get('message', '')
        subject = data.get('title', 'Notification from Lumira Skin')

    # Send email
    success = email_service.send_email(recipient, subject, html_content, text_content)

    if success:
        return APIResponse(
            success=True,
            message="Email sent successfully",
            data={
                "recipient": recipient,
                "type": notification_type or "generic",
                "subject": subject,
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Failed to send email",
                "error": {
                    "code": "EMAIL_SEND_FAILED",
                    "message": "Email service encountered an error"
                }
            }
        )


# -------------------------------
# WhatsApp APIs
# -------------------------------
@router.post("/whatsapp")
def send_whatsapp_notification(payload: dict, db: DBSession):
    """
    Send WhatsApp notification.
    Expected payload: {
        "type": "order_update",
        "recipient": "+919876543210",
        "message": "Your order has been shipped!"
    }
    """
    whatsapp_service = WhatsAppService()
    notification_type = payload.get("type")
    recipient = payload.get("recipient")
    message = payload.get("message", "")

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Recipient phone number is required",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "recipient field is required"
                }
            }
        )

    # Send WhatsApp message
    success = whatsapp_service.send_message(recipient, message)

    if success:
        return APIResponse(
            success=True,
            message="WhatsApp message sent successfully",
            data={
                "recipient": recipient,
                "type": notification_type or "generic",
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Failed to send WhatsApp message",
                "error": {
                    "code": "WHATSAPP_SEND_FAILED",
                    "message": "WhatsApp service encountered an error"
                }
            }
        )


# -------------------------------
# SMS APIs (existing)
# -------------------------------
@router.post("/sms")
def send_sms_notification(payload: dict, db: DBSession):
    """
    Send SMS notification via Twilio.
    Expected payload: {
        "recipient": "+919876543210",
        "message": "Your order has been confirmed!"
    }
    """
    twilio_service = TwilioService()
    recipient = payload.get("recipient")
    message = payload.get("message", "")

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Recipient phone number is required",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "recipient field is required"
                }
            }
        )

    try:
        twilio_service.send_sms(recipient, message)
        return APIResponse(
            success=True,
            message="SMS sent successfully",
            data={"recipient": recipient}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Failed to send SMS",
                "error": {
                    "code": "SMS_SEND_FAILED",
                    "message": str(e)
                }
            }
        )
