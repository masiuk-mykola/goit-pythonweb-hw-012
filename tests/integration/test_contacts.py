from datetime import date, timedelta

import pytest

CONTACT = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone_number": "0501234567",
    "dob": "1990-05-17",
    "additional_info": "friend",
}


async def _create(client, headers, **overrides):
    response = await client.post(
        "/api/contacts/", json={**CONTACT, **overrides}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_requires_auth(client):
    response = await client.get("/api/contacts/")
    assert response.status_code == 401


async def test_create_contact(client, user_headers):
    data = await _create(client, user_headers)

    assert data["id"] is not None
    assert data["first_name"] == "John"
    assert data["dob"].startswith("1990-05-17")


async def test_create_contact_validation(client, user_headers):
    response = await client.post(
        "/api/contacts/", json={**CONTACT, "email": "not-an-email"}, headers=user_headers
    )
    assert response.status_code == 422


async def test_read_contact(client, user_headers):
    created = await _create(client, user_headers)

    response = await client.get(f"/api/contacts/{created['id']}", headers=user_headers)

    assert response.status_code == 200
    assert response.json() == created


async def test_read_contact_not_found(client, user_headers):
    response = await client.get("/api/contacts/999", headers=user_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Contact not found"


async def test_contacts_are_isolated_between_users(
    client, user_headers, admin_headers
):
    created = await _create(client, user_headers)

    response = await client.get(f"/api/contacts/{created['id']}", headers=admin_headers)
    assert response.status_code == 404
    assert (await client.get("/api/contacts/", headers=admin_headers)).json() == []


async def test_read_contacts_with_filters(client, user_headers):
    await _create(client, user_headers)
    await _create(
        client, user_headers, first_name="Jane", last_name="Roe", email="jane@example.com"
    )

    all_contacts = await client.get("/api/contacts/", headers=user_headers)
    assert len(all_contacts.json()) == 2

    by_name = await client.get(
        "/api/contacts/", params={"first_name": "jane"}, headers=user_headers
    )
    assert [c["first_name"] for c in by_name.json()] == ["Jane"]

    by_last_and_email = await client.get(
        "/api/contacts/",
        params={"last_name": "DOE", "email": "JOHN@example.com"},
        headers=user_headers,
    )
    assert [c["first_name"] for c in by_last_and_email.json()] == ["John"]

    paged = await client.get(
        "/api/contacts/", params={"skip": 1, "limit": 1}, headers=user_headers
    )
    assert len(paged.json()) == 1


async def test_read_contacts_upcoming_birthdays(client, user_headers):
    soon = date.today() + timedelta(days=3)
    later = date.today() + timedelta(days=30)
    await _create(client, user_headers, first_name="Soon", dob=soon.replace(year=1992).isoformat())
    await _create(client, user_headers, first_name="Later", dob=later.replace(year=1992).isoformat())

    response = await client.get(
        "/api/contacts/", params={"days_to_birthday": 7}, headers=user_headers
    )

    assert [c["first_name"] for c in response.json()] == ["Soon"]


async def test_update_contact(client, user_headers):
    created = await _create(client, user_headers)

    response = await client.put(
        f"/api/contacts/{created['id']}",
        json={**CONTACT, "first_name": "Johnny"},
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Johnny"


async def test_update_contact_not_found(client, user_headers):
    response = await client.put("/api/contacts/999", json=CONTACT, headers=user_headers)
    assert response.status_code == 404


async def test_delete_contact(client, user_headers):
    created = await _create(client, user_headers)

    response = await client.delete(f"/api/contacts/{created['id']}", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]

    response = await client.get(f"/api/contacts/{created['id']}", headers=user_headers)
    assert response.status_code == 404


@pytest.mark.parametrize("method", ["delete", "get"])
async def test_missing_contact(client, user_headers, method):
    response = await getattr(client, method)("/api/contacts/12345", headers=user_headers)
    assert response.status_code == 404
