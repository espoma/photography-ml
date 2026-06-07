"""
Pytest-based endpoint tests using FastAPI TestClient (no live server needed).
Runs against the CI PostgreSQL instance (or local DB via backend/.env).
"""
import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, delete

# Create static dir before importing main (StaticFiles mount requires it to exist)
Path("static/images").mkdir(parents=True, exist_ok=True)

# Provide defaults so database.py doesn't raise ValueError when .env is absent
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://photography_user:photography_password@localhost:5432/photography_db",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci")
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-ci")

from main import app  # noqa: E402 — env must be set first
from app.database import engine  # noqa: E402
from app.models import Image, User, UserPreference  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the test session."""
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def truncate_tables(create_tables):
    """Delete all rows before each test so each test starts clean."""
    with Session(engine) as session:
        session.exec(delete(Image))
        session.exec(delete(UserPreference))
        session.exec(delete(User))
        session.commit()
    yield


@pytest.fixture
def client(truncate_tables):
    with TestClient(app) as c:
        yield c


def _fake_image():
    """Return (files, data) suitable for a multipart image upload."""
    return (
        {"file": ("photo.jpg", io.BytesIO(b"fake-jpeg-bytes"), "image/jpeg")},
        {"description": "test photo"},
    )


def _signup(client, username="alice", password="pass1234"):
    r = client.post("/auth/signup", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────────


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "active"


# ── Auth ──────────────────────────────────────────────────────────────────────


def test_signup_success(client):
    r = client.post("/auth/signup", json={"username": "bob", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "bob"
    assert "access_token" in body


def test_signup_duplicate_username(client):
    _signup(client, "bob")
    r = client.post("/auth/signup", json={"username": "bob", "password": "other"})
    assert r.status_code == 400


def test_login_success(client):
    _signup(client, "bob", "secret123")
    r = client.post("/auth/login", json={"username": "bob", "password": "secret123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    _signup(client, "bob", "secret123")
    r = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert r.status_code == 401


def test_me_authenticated(client):
    token = _signup(client)["access_token"]
    r = client.get("/auth/me", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_me_unauthenticated(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


# ── Images ────────────────────────────────────────────────────────────────────


@patch("main.generate_embedding", return_value=[0.1] * 768)
@patch("main.generate_tags", return_value=["sky", "outdoor"])
def test_upload_image(mock_tags, mock_emb, client):
    files, data = _fake_image()
    r = client.post("/images/", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["filename"].endswith(".jpg")
    assert "sky" in body["tags"]
    assert body["embedding"] is not None


@patch("main.generate_embedding", return_value=None)
@patch("main.generate_tags", return_value=["tag1"])
def test_list_images(mock_tags, mock_emb, client):
    files, data = _fake_image()
    client.post("/images/", files=files, data=data)
    r = client.get("/images/")
    assert r.status_code == 200
    assert len(r.json()) == 1


@patch("main.generate_embedding", return_value=None)
@patch("main.generate_tags", return_value=["tag1"])
def test_get_image_by_id(mock_tags, mock_emb, client):
    files, data = _fake_image()
    image_id = client.post("/images/", files=files, data=data).json()["id"]
    r = client.get(f"/images/{image_id}")
    assert r.status_code == 200
    assert r.json()["id"] == image_id


def test_get_image_not_found(client):
    r = client.get("/images/99999")
    assert r.status_code == 404


@patch("main.generate_embedding", return_value=None)
@patch("main.generate_tags", return_value=["tag1"])
def test_update_image(mock_tags, mock_emb, client):
    files, data = _fake_image()
    image_id = client.post("/images/", files=files, data=data).json()["id"]
    r = client.patch(f"/images/{image_id}", json={"description": "updated desc"})
    assert r.status_code == 200
    assert r.json()["description"] == "updated desc"


@patch("main.generate_embedding", return_value=None)
@patch("main.generate_tags", return_value=["tag1"])
def test_delete_image(mock_tags, mock_emb, client):
    files, data = _fake_image()
    image_id = client.post("/images/", files=files, data=data).json()["id"]
    assert client.delete(f"/images/{image_id}").status_code == 200
    assert client.get(f"/images/{image_id}").status_code == 404


@patch("main.generate_embedding", return_value=None)
@patch("main.generate_tags", return_value=["tag1"])
def test_upload_associates_user_when_authenticated(mock_tags, mock_emb, client):
    token = _signup(client)["access_token"]
    files, data = _fake_image()
    r = client.post("/images/", files=files, data=data, headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["user_id"] is not None


# ── Similarity ────────────────────────────────────────────────────────────────

@patch("main.generate_embedding", return_value=[0.1] * 768)
@patch("main.generate_tags", return_value=["tag1"])
def test_similar_images(mock_tags, mock_emb, client):
    files, _ = _fake_image()
    id1 = client.post("/images/", files=files, data={"description": "a"}).json()["id"]
    files, _ = _fake_image()
    client.post("/images/", files=files, data={"description": "b"})
    r = client.get(f"/images/similar/{id1}?n=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_similar_images_no_embedding(client):
    # Image without embedding should return 422
    from app.models import Image
    from sqlmodel import Session
    from app.database import engine
    img = Image(filename="x.jpg", file_path="/static/images/x.jpg", tags=[], embedding=None)
    with Session(engine) as s:
        s.add(img)
        s.commit()
        s.refresh(img)
        img_id = img.id
    r = client.get(f"/images/similar/{img_id}")
    assert r.status_code == 422


# ── Preferences ───────────────────────────────────────────────────────────────

def test_preferences_upsert_and_get(client):
    token = _signup(client)["access_token"]
    h = _auth_header(token)
    r = client.put("/users/me/preferences/", json={"key": "theme_weights", "value": {"street": 0.8}}, headers=h)
    assert r.status_code == 200
    r2 = client.get("/users/me/preferences/", headers=h)
    assert r2.status_code == 200
    prefs = {p["key"]: p["value"] for p in r2.json()}
    assert prefs["theme_weights"] == {"street": 0.8}


def test_preferences_update(client):
    token = _signup(client)["access_token"]
    h = _auth_header(token)
    client.put("/users/me/preferences/", json={"key": "theme_weights", "value": {"street": 0.8}}, headers=h)
    client.put("/users/me/preferences/", json={"key": "theme_weights", "value": {"portrait": 0.9}}, headers=h)
    r = client.get("/users/me/preferences/", headers=h)
    prefs = {p["key"]: p["value"] for p in r.json()}
    assert prefs["theme_weights"] == {"portrait": 0.9}


def test_preferences_delete(client):
    token = _signup(client)["access_token"]
    h = _auth_header(token)
    client.put("/users/me/preferences/", json={"key": "style", "value": "street"}, headers=h)
    assert client.delete("/users/me/preferences/style", headers=h).status_code == 200
    r = client.get("/users/me/preferences/", headers=h)
    assert all(p["key"] != "style" for p in r.json())
