"""Transactional emails (verification and password reset) via ``fastapi-mail``."""

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


async def _send(message: MessageSchema, template_name: str, email: str) -> None:
    try:
        await FastMail(conf).send_message(message, template_name=template_name)
    except ConnectionErrors as err:
        logger.error("Failed to send %s to %s: %s", template_name, email, err)


async def send_verification_email(email: str, username: str) -> None:
    """Send an email with a link that confirms the address.

    SMTP errors are logged and swallowed: the function runs as a background task.

    Args:
        email: Recipient address.
        username: Name used in the greeting.
    """
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
    await _send(message, "verify_email.html", email)


async def send_reset_password_email(email: str, username: str, token: str) -> None:
    """Send an email with a single-use password reset token.

    SMTP errors are logged and swallowed: the function runs as a background task.

    Args:
        email: Recipient address.
        username: Name used in the greeting.
        token: Reset token created by :func:`src.services.auth.create_reset_token`.
    """
    message = MessageSchema(
        subject="Скидання пароля",
        recipients=[email],
        template_body={
            "username": username,
            "token": token,
            "reset_url": f"{config.APP_BASE_URL}/api/auth/reset_password",
            "expires_minutes": config.RESET_TOKEN_EXPIRATION_SECONDS // 60,
        },
        subtype=MessageType.html,
    )
    await _send(message, "reset_password.html", email)
