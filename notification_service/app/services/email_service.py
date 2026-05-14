import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from app.config import settings

class EmailService:
    """Handles email notifications."""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.sendgrid_api_key = settings.SENDGRID_API_KEY

    def _send_with_sendgrid(self, to: str, subject: str, html_content: str, text_content: str = None) -> bool:
        if not self.sendgrid_api_key or not self.email_from:
            return False

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self.email_from},
            "subject": subject,
            "content": [
                {
                    "type": "text/plain",
                    "value": text_content or "",
                },
                {
                    "type": "text/html",
                    "value": html_content,
                },
            ],
        }

        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if response.status_code not in {200, 202}:
            print(f"SendGrid email failed: {response.status_code} {response.text[:200]}")
            return False
        return True

    def _send_with_smtp(self, to: str, subject: str, html_content: str, text_content: str = None) -> bool:
        if not self.smtp_host or not self.smtp_user or not self.smtp_password or not self.email_from:
            print("SMTP email is not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and EMAIL_FROM.")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = to

        if text_content:
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)

        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        server.starttls()
        server.login(self.smtp_user, self.smtp_password)
        server.sendmail(self.email_from, to, msg.as_string())
        server.quit()
        return True

    def send_email(self, to: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send HTML email with optional text fallback."""
        try:
            if self.sendgrid_api_key and self._send_with_sendgrid(to, subject, html_content, text_content):
                return True

            return self._send_with_smtp(to, subject, html_content, text_content)
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
