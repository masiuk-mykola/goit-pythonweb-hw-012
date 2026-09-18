import logging
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors

from src.conf.config import config
from src.services.auth import create_email_token

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_FROM=config.MAIL_FROM,
    MAIL_PORT=config.MAIL_PORT,
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_FROM_NAME=config.MAIL_FROM_NAME,
    MAIL_STARTTLS=config.MAIL_STARTTLS,
    MAIL_SSL_TLS=config.MAIL_SSL_TLS,
    USE_CREDENTIALS=config.MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=config.MAIL_VALIDATE_CERTS,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates",
)


async def send_verification_email(email: str, username: str) -> None:
    token = create_email_token({"sub": email})
    message = MessageSchema(
        subject="Підтвердіть вашу електронну адресу",
        recipients=[email],
        template_body={
            "username": username,
            "verify_url": f"{config.APP_BASE_URL}/api/auth/confirmed_email/{token}",
        },
        subtype=MessageType.html,
    )
    try:
        await FastMail(conf).send_message(message, template_name="verify_email.html")
    except ConnectionErrors as err:
        logger.error("Failed to send verification email to %s: %s", email, err)
