import json
from unittest.mock import patch

from cloudinary.exceptions import Error as CloudinaryError

from src.services.auth import create_access_token
from src.services.limiter import limiter

AVATAR_URL = "https://res.cloudinary.com/test/image/upload/ContactsApp/admin"
IMAGE = {"file": ("avatar.png", b"fake-png-bytes", "image/png")}


async def test_me(client, user, user_headers):
    response = await client.get("/api/users/me", headers=user_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user.username
    assert data["role"] == "user"


async def test_me_is_cached_in_redis(client, user, user_headers, redis_client):
    await client.get("/api/users/me", headers=user_headers)

    cached = json.loads(await redis_client.get(f"user:{user.username}"))
    assert cached["email"] == user.email
    assert "hashed_password" not in cached

    # якщо кеш підмінити, відповідь бере дані саме з нього, а не з БД
    cached["avatar"] = "from-cache"
    await redis_client.set(f"user:{user.username}", json.dumps(cached))
    response = await client.get("/api/users/me", headers=user_headers)
    assert response.json()["avatar"] == "from-cache"


async def test_me_unauthorized(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 401


async def test_me_invalid_token(client):
    response = await client.get(
        "/api/users/me", headers={"Authorization": "Bearer bad-token"}
    )
    assert response.status_code == 401


async def test_me_unknown_user(client):
    token = create_access_token({"sub": "ghost"})
    response = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_me_rate_limit(client, user_headers):
    limiter.enabled = True
    limiter.reset()
    try:
        statuses = [
            (await client.get("/api/users/me", headers=user_headers)).status_code
            for _ in range(11)
        ]
    finally:
        limiter.reset()
        limiter.enabled = False

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


async def test_avatar_forbidden_for_user(client, user_headers):
    response = await client.patch("/api/users/avatar", files=IMAGE, headers=user_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


async def test_avatar_admin(client, admin, admin_headers, redis_client):
    await client.get("/api/users/me", headers=admin_headers)  # кладемо в кеш

    with patch(
        "src.api.users.UploadFileService.upload_file", return_value=AVATAR_URL
    ) as upload:
        response = await client.patch(
            "/api/users/avatar", files=IMAGE, headers=admin_headers
        )

    assert response.status_code == 200, response.text
    assert response.json()["avatar"] == AVATAR_URL
    upload.assert_called_once()
    assert await redis_client.get(f"user:{admin.username}") is None

    response = await client.get("/api/users/me", headers=admin_headers)
    assert response.json()["avatar"] == AVATAR_URL


async def test_avatar_not_an_image(client, admin_headers):
    response = await client.patch(
        "/api/users/avatar",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=admin_headers,
    )
    assert response.status_code == 422


async def test_avatar_upload_error(client, admin_headers):
    with patch(
        "src.api.users.UploadFileService.upload_file",
        side_effect=CloudinaryError("boom"),
    ):
        response = await client.patch(
            "/api/users/avatar", files=IMAGE, headers=admin_headers
        )
    assert response.status_code == 502
