"""
API test suite for real authentication endpoints (Contract 3, Endpoints 2-4).
Uses TestClient with create_app(False) and monkeypatched repository layer.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import pytest
from fastapi.testclient import TestClient

from backend.app import repository
from backend.app.main import create_app
from backend.app.security import decode_access_token
from shared.contracts import TokenResponse, UserOut


@pytest.fixture
def in_memory_user_repo(monkeypatch):
    """
    Monkeypatches repository database calls with an isolated in-memory dictionary.
    No MySQL database connection is needed.
    """
    db_store: Dict[int, Dict[str, Any]] = {}
    next_id = [1]

    def fake_create_user(email: str, password_hash: str, full_name: str) -> int:
        user_id = next_id[0]
        next_id[0] += 1
        record = {
            "user_id": user_id,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
        }
        db_store[user_id] = record
        return user_id

    def fake_get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        for record in db_store.values():
            if record["email"].lower() == email.lower():
                return dict(record)
        return None

    def fake_get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        record = db_store.get(user_id)
        return dict(record) if record else None

    monkeypatch.setattr(repository, "create_user", fake_create_user)
    monkeypatch.setattr(repository, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(repository, "get_user_by_id", fake_get_user_by_id)

    return db_store


@pytest.fixture
def auth_client(in_memory_user_repo) -> TestClient:
    """Provide a TestClient connected to create_app(mock_mode=False)."""
    app = create_app(mock_mode=False)
    return TestClient(app)


def test_register_201_success(auth_client: TestClient):
    """POST /api/v1/auth/register creates a user and returns 201 UserOut."""
    payload = {
        "email": "sarah.connor@example.com",
        "password": "Password123!",
        "full_name": "Sarah Connor",
    }
    response = auth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    user_out = UserOut.model_validate(data)
    assert user_out.email == "sarah.connor@example.com"
    assert user_out.full_name == "Sarah Connor"
    assert user_out.user_id >= 1
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_409(auth_client: TestClient):
    """POST /api/v1/auth/register returns 409 Conflict if email is already taken."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "First User",
    }
    first_res = auth_client.post("/api/v1/auth/register", json=payload)
    assert first_res.status_code == 201

    duplicate_res = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "AnotherPassword456!",
            "full_name": "Second User",
        },
    )
    assert duplicate_res.status_code == 409
    err = duplicate_res.json()
    assert "detail" in err
    assert "already registered" in err["detail"].lower()


def test_login_200_returns_access_token(auth_client: TestClient):
    """POST /api/v1/auth/login with valid credentials returns 200 TokenResponse."""
    register_payload = {
        "email": "john.doe@example.com",
        "password": "SecretPassword99!",
        "full_name": "John Doe",
    }
    reg_res = auth_client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user_id"]

    login_payload = {
        "email": "john.doe@example.com",
        "password": "SecretPassword99!",
    }
    login_res = auth_client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200

    token_data = login_res.json()
    token_resp = TokenResponse.model_validate(token_data)
    assert token_resp.token_type == "bearer"
    assert len(token_resp.access_token) > 0

    decoded_id = decode_access_token(token_resp.access_token)
    assert decoded_id == user_id


def test_login_wrong_password_or_email_401(auth_client: TestClient):
    """POST /api/v1/auth/login returns 401 when password or email is incorrect."""
    register_payload = {
        "email": "target@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Target User",
    }
    auth_client.post("/api/v1/auth/register", json=register_payload)

    # Wrong password
    wrong_pwd_res = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "target@example.com", "password": "WrongPassword!"},
    )
    assert wrong_pwd_res.status_code == 401
    assert wrong_pwd_res.json()["detail"] == "Invalid email or password"

    # Non-existent email
    unknown_email_res = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "CorrectPassword123!"},
    )
    assert unknown_email_res.status_code == 401
    assert unknown_email_res.json()["detail"] == "Invalid email or password"


def test_auth_me_with_bearer_token_200(auth_client: TestClient):
    """GET /api/v1/auth/me returns 200 UserOut when authenticated with Bearer token."""
    register_payload = {
        "email": "authenticated@example.com",
        "password": "SecurePassword1!",
        "full_name": "Authenticated User",
    }
    reg_res = auth_client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201

    login_res = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "authenticated@example.com", "password": "SecurePassword1!"},
    )
    token = login_res.json()["access_token"]

    me_res = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_out = UserOut.model_validate(me_res.json())
    assert user_out.email == "authenticated@example.com"
    assert user_out.full_name == "Authenticated User"


def test_auth_me_without_token_401(auth_client: TestClient):
    """GET /api/v1/auth/me returns 401 Unauthorized when missing Authorization header."""
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "missing" in data["detail"].lower()


def test_auth_me_with_invalid_token_401(auth_client: TestClient):
    """GET /api/v1/auth/me returns 401 Unauthorized when token is invalid or corrupted."""
    response = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer corrupted.garbage.token"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

