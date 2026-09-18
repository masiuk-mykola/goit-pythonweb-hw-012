from unittest.mock import AsyncMock, MagicMock, patch

from fastapi_mail.errors import ConnectionErrors

from src.services import email
from src.services.upload_file import UploadFileService


async def test_send_verification_email():
    with patch.object(email.FastMail, "send_message", AsyncMock()) as send:
        await email.send_verification_email("a@example.com", "alice")

    message = send.await_args.args[0]
    assert message.recipients[0].email == "a@example.com"
    assert "/api/auth/confirmed_email/" in message.template_body["verify_url"]
    assert send.await_args.kwargs["template_name"] == "verify_email.html"


async def test_send_reset_password_email():
    with patch.object(email.FastMail, "send_message", AsyncMock()) as send:
        await email.send_reset_password_email("a@example.com", "alice", "tok")

    message = send.await_args.args[0]
    assert message.template_body["token"] == "tok"
    assert send.await_args.kwargs["template_name"] == "reset_password.html"


async def test_email_connection_error_is_logged(caplog):
    with patch.object(
        email.FastMail, "send_message", AsyncMock(side_effect=ConnectionErrors("down"))
    ):
        await email.send_verification_email("a@example.com", "alice")

    assert "Failed to send verify_email.html" in caplog.text


def test_upload_file():
    file = MagicMock()
    with (
        patch("src.services.upload_file.cloudinary.uploader.upload") as upload,
        patch("src.services.upload_file.cloudinary.CloudinaryImage") as image,
    ):
        upload.return_value = {"version": 42}
        image.return_value.build_url.return_value = "https://img/alice"

        url = UploadFileService("cloud", "key", "secret").upload_file(file, "alice")

    assert url == "https://img/alice"
    upload.assert_called_once_with(
        file.file, public_id="ContactsApp/alice", overwrite=True
    )
    image.return_value.build_url.assert_called_once_with(
        width=250, height=250, crop="fill", version=42
    )
