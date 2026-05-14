class EmailTemplates:
    """HTML email templates for different notification types."""

    @staticmethod
    def order_confirmation(customer_name: str, order_id: str, order_total: float, items: list) -> tuple[str, str]:
        """Generate order confirmation email."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Order Confirmation</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; color: #2c5530; margin-bottom: 30px; }}
                .order-details {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .item {{ margin: 10px 0; padding: 10px; border-bottom: 1px solid #eee; }}
                .total {{ font-weight: bold; font-size: 18px; color: #2c5530; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Order Confirmed!</h1>
                    <p>Thank you for your order, {customer_name}!</p>
                </div>

                <div class="order-details">
                    <h3>Order #{order_id}</h3>
                    <div class="items">
                        {"".join([f'<div class="item"><strong>{item["name"]}</strong> - Quantity: {item["quantity"]} - ₹{item["price"]}</div>' for item in items])}
                    </div>
                    <div class="total">Total: ₹{order_total}</div>
                </div>

                <p>Your order has been received and is being processed. We'll send you shipping updates soon!</p>

                <div class="footer">
                    <p>Lumira Skin - Natural Beauty, Naturally</p>
                    <p>If you have any questions, please contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """

        items_text = "\n".join([f"- {item['name']} (Qty: {item['quantity']}) - ₹{item['price']}" for item in items])
        
        text = f"""
        Order Confirmation

        Dear {customer_name},

        Thank you for your order! Your order #{order_id} has been confirmed.

        Order Details:
        {items_text}

        Total: ₹{order_total}

        We'll send you shipping updates soon!

        Best regards,
        Lumira Skin Team
        """

        return html, text

    @staticmethod
    def order_shipped(customer_name: str, order_id: str, tracking_number: str = None) -> tuple[str, str]:
        """Generate order shipped email."""
        tracking_info = f"<p><strong>Tracking Number:</strong> {tracking_number}</p>" if tracking_number else ""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Order Shipped</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; color: #2c5530; margin-bottom: 30px; }}
                .tracking {{ background-color: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚚 Order Shipped!</h1>
                    <p>Great news, {customer_name}!</p>
                </div>

                <p>Your order #{order_id} has been shipped and is on its way to you.</p>

                <div class="tracking">
                    {tracking_info}
                    <p>You can track your order status in your account dashboard.</p>
                </div>

                <p>Expected delivery: 3-5 business days</p>

                <div class="footer">
                    <p>Lumira Skin - Natural Beauty, Naturally</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
        Order Shipped

        Dear {customer_name},

        Great news! Your order #{order_id} has been shipped.

        {f"Tracking Number: {tracking_number}" if tracking_number else ""}

        Expected delivery: 3-5 business days

        Best regards,
        Lumira Skin Team
        """

        return html, text

    @staticmethod
    def password_reset(customer_name: str, reset_link: str) -> tuple[str, str]:
        """Generate password reset email."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Password Reset</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; color: #2c5530; margin-bottom: 30px; }}
                .reset-button {{ display: inline-block; background-color: #2c5530; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .warning {{ color: #d32f2f; font-size: 12px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset</h1>
                    <p>Hello {customer_name},</p>
                </div>

                <p>You requested a password reset for your Lumira Skin account.</p>

                <p>Click the button below to reset your password:</p>

                <div style="text-align: center;">
                    <a href="{reset_link}" class="reset-button">Reset Password</a>
                </div>

                <p class="warning">
                    This link will expire in 1 hour. If you didn't request this reset, please ignore this email.
                </p>

                <div class="footer">
                    <p>Lumira Skin - Natural Beauty, Naturally</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
        Password Reset

        Hello {customer_name},

        You requested a password reset for your Lumira Skin account.

        Reset your password here: {reset_link}

        This link will expire in 1 hour. If you didn't request this reset, please ignore this email.

        Best regards,
        Lumira Skin Team
        """

        return html, text