from unittest.mock import AsyncMock

from main import app
from src.database.db import get_db


async def test_healthchecker(client):
    response = await client.get("/api/healthchecker")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI!"}


async def test_healthchecker_db_down(client):
    broken = AsyncMock()
    broken.execute.side_effect = ConnectionError("db is down")

    async def override():
        yield broken

    app.dependency_overrides[get_db] = override
    response = await client.get("/api/healthchecker")

    assert response.status_code == 500
    assert response.json()["detail"] == "Error connecting to the database"
