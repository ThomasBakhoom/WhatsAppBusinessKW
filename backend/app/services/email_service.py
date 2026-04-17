"""Email notification service (SES or SMTP)."""

import structlog
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class EmailService:
    """Send transactional emails. Uses AWS SES in production, logs in development."""

    def __init__(self):
        self._domain = settings.app_domain.rstrip("/")

    async def send_welcome(self, to_email: str, company_name: str, first_name: str):
        subject = "Welcome to Kuwait WhatsApp Growth Engine"
        body = (
            f"Hi {first_name},\n\n"
            f"Welcome to {company_name} on KW Growth Engine!\n\n"
            f"Get started by connecting your WhatsApp number and importing your contacts.\n\n"
            f"Best,\nKW Growth Team"
        )
        await self._send(to_email, subject, body)

    async def send_invite(self, to_email: str, company_name: str, inviter_name: str, temp_password: str):
        subject = f"You've been invited to {company_name}"
        body = (
            f"Hi,\n\n"
            f"{inviter_name} has invited you to join {company_name} on KW Growth Engine.\n\n"
            f"Login at: {self._domain}/login\n"
            f"Email: {to_email}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Please change your password after first login."
        )
        await self._send(to_email, subject, body)

    async def send_invoice(self, to_email: str, invoice_number: str, amount: str, currency: str):
        subject = f"Invoice {invoice_number} - {amount} {currency}"
        body = (
            f"Your invoice {invoice_number} for {amount} {currency} is ready.\n\n"
            f"View and pay at: {self._domain}/settings/billing"
        )
        await self._send(to_email, subject, body)

    async def send_password_reset(self, to_email: str, reset_link: str):
        subject = "Reset Your Password"
        body = f"Click the link below to reset your password:\n\n{reset_link}\n\nThis link expires in 1 hour."
        await self._send(to_email, subject, body)

    async def _send(self, to: str, subject: str, body: str):
        if settings.is_production:
            try:
                import boto3
                client = boto3.client("ses", region_name="me-south-1")
                from_addr = f"noreply@{self._domain.split('://')[-1].split('/')[0]}"
                client.send_email(
                    Source=from_addr,
                    Destination={"ToAddresses": [to]},
                    Message={
                        "Subject": {"Data": subject},
                        "Body": {"Text": {"Data": body}},
                    },
                )
                logger.info("email_sent", to=to, subject=subject)
            except Exception as e:
                logger.error("email_send_failed", to=to, error=str(e))
        else:
            # Log the full body in dev so reset-token URLs aren't truncated.
            logger.info("email_mock", to=to, subject=subject, body=body)
