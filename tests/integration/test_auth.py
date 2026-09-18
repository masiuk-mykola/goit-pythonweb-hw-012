from sqlalchemy import select

from src.database.models import User
from src.services.auth import create_email_token, create_reset_token
from tests.conftest import TEST_PASSWORD, TestingSessionLocal

NEW_USER = {"username": "agent007", "email": "agent007@gmail.com", "password": "12345678"}


async def _login(client, username, password=TEST_PASSWORD):
    return await client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )


async def _get_user(username: str) -> User:
    async with TestingSessionLocal() as session:
        result = await session.execute(select(User).filter_by(username=username))
        return result.scalar_one()


async def test_register(client, mock_emails):
    response = await client.post("/api/auth/register", json=NEW_USER)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == NEW_USER["username"]
    assert data["email"] == NEW_USER["email"]
    assert data["role"] == "user"
    assert data["confirmed"] is False
    assert "password" not in data and "hashed_password" not in data
    mock_emails["verification"].assert_awaited_once_with(
        NEW_USER["email"], NEW_USER["username"]
    )


async def test_register_duplicate_email(client, user):
    response = await client.post(
        "/api/auth/register", json={**NEW_USER, "email": user.email}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "User with this email already exists"


async def test_register_duplicate_username(client, user):
    response = await client.post(
        "/api/auth/register", json={**NEW_USER, "username": user.username}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "User with this username already exists"


async def test_login_not_confirmed(client):
    await client.post("/api/auth/register", json=NEW_USER)

    response = await _login(client, NEW_USER["username"], NEW_USER["password"])

    assert response.status_code == 401
    assert response.json()["detail"] == "Email address is not confirmed"


async def test_login(client, user):
    response = await _login(client, user.username)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"] and data["refresh_token"]
    assert (await _get_user(user.username)).refresh_token == data["refresh_token"]


async def test_login_wrong_password(client, user):
    response = await _login(client, user.username, "wrong-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


async def test_login_unknown_user(client):
    response = await _login(client, "nobody")
    assert response.status_code == 401


async def test_confirmed_email(client):
    await client.post("/api/auth/register", json=NEW_USER)
    token = create_email_token({"sub": NEW_USER["email"]})

    response = await client.get(f"/api/auth/confirmed_email/{token}")
    assert response.status_code == 200
    assert response.json()["message"] == "Email confirmed"

    response = await client.get(f"/api/auth/confirmed_email/{token}")
    assert response.json()["message"] == "Your email is already confirmed"


async def test_confirmed_email_unknown_user(client):
    token = create_email_token({"sub": "ghost@example.com"})
    response = await client.get(f"/api/auth/confirmed_email/{token}")
    assert response.status_code == 400


async def test_confirmed_email_invalid_token(client):
    response = await client.get("/api/auth/confirmed_email/not-a-token")
    assert response.status_code == 422


async def test_request_email(client, mock_emails):
    await client.post("/api/auth/register", json=NEW_USER)
    mock_emails["verification"].reset_mock()

    response = await client.post(
        "/api/auth/request_email", json={"email": NEW_USER["email"]}
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Check your email for confirmation"
    mock_emails["verification"].assert_awaited_once()


async def test_request_email_already_confirmed(client, user, mock_emails):
    response = await client.post("/api/auth/request_email", json={"email": user.email})
    assert response.json()["message"] == "Your email is already confirmed"
    mock_emails["verification"].assert_not_awaited()


async def test_refresh_token_rotation(client, user):
    tokens = (await _login(client, user.username)).json()

    response = await client.post(
        "/api/auth/refresh_token", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200, response.text
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # старий refresh-токен більше не діє
    response = await client.post(
        "/api/auth/refresh_token", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401

    response = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert response.status_code == 200


async def test_refresh_token_invalid(client):
    response = await client.post(
        "/api/auth/refresh_token", json={"refresh_token": "garbage"}
    )
    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client, user, redis_client):
    tokens = (await _login(client, user.username)).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    await client.get("/api/users/me", headers=headers)
    assert await redis_client.get(f"user:{user.username}") is not None

    response = await client.post("/api/auth/logout", headers=headers)

    assert response.status_code == 204
    assert await redis_client.get(f"user:{user.username}") is None
    assert (await _get_user(user.username)).refresh_token is None
    response = await client.post(
        "/api/auth/refresh_token", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


async def test_logout_without_cached_user(client, user):
    tokens = (await _login(client, user.username)).json()

    response = await client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 204
    assert (await _get_user(user.username)).refresh_token is None


async def test_request_password_reset(client, user, mock_emails):
    response = await client.post(
        "/api/auth/request_password_reset", json={"email": user.email}
    )

    assert response.status_code == 202
    mock_emails["reset"].assert_awaited_once()
    email, username, token = mock_emails["reset"].await_args.args
    assert (email, username) == (user.email, user.username)
    assert token


async def test_request_password_reset_unknown_email(client, mock_emails):
    response = await client.post(
        "/api/auth/request_password_reset", json={"email": "ghost@example.com"}
    )

    assert response.status_code == 202  # та сама відповідь, що й для існуючого email
    mock_emails["reset"].assert_not_awaited()


async def test_reset_password(client, user, mock_emails):
    await client.post("/api/auth/request_password_reset", json={"email": user.email})
    token = mock_emails["reset"].await_args.args[2]

    response = await client.post(
        "/api/auth/reset_password", json={"token": token, "new_password": "new-pass-1"}
    )
    assert response.status_code == 200, response.text

    assert (await _login(client, user.username)).status_code == 401
    assert (await _login(client, user.username, "new-pass-1")).status_code == 201

    # токен одноразовий
    response = await client.post(
        "/api/auth/reset_password", json={"token": token, "new_password": "another-1"}
    )
    assert response.status_code == 400


async def test_reset_password_invalid_token(client):
    response = await client.post(
        "/api/auth/reset_password", json={"token": "garbage", "new_password": "new-pass-1"}
    )
    assert response.status_code == 400


async def test_reset_password_unknown_user(client):
    token = create_reset_token("ghost@example.com", "hash")
    response = await client.post(
        "/api/auth/reset_password", json={"token": token, "new_password": "new-pass-1"}
    )
    assert response.status_code == 400
