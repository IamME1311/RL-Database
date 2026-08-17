import aiosmtplib
from email.message import EmailMessage
from app.core.config import settings


async def send_email(to: str, subject: str, html_body: str, text_body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )


def verification_email_body(name: str, verify_url: str) -> tuple[str, str]:
    text = f"Hi {name},\n\nVerify your RippleLinks account:\n{verify_url}\n\nThis link expires in 24 hours."
    html = f"""
    <p>Hi {name},</p>
    <p><a href="{verify_url}">Verify your RippleLinks account</a></p>
    <p>This link expires in 24 hours.</p>
    """
    return (text, html)
