import os

import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"
TEST_FILENAME = "test_upload.txt"


@pytest.fixture(scope="session", autouse=True)
def test_upload_file():
    with open(TEST_FILENAME, "wb") as f:
        f.write(b"dummy content")
    yield TEST_FILENAME
    try:
        os.remove(TEST_FILENAME)
    except OSError:
        pass


def test_image_lifecycle(test_upload_file):
    with open(TEST_FILENAME, "rb") as upload_file:
        files = {"file": (TEST_FILENAME, upload_file)}
        data = {"description": "Initial Description", "tags": ["test"]}
        response = requests.post(f"{BASE_URL}/images/", files=files, data=data)

    assert response.status_code == 200, f"POST /images/ failed: {response.status_code} {response.text}"
    image_data = response.json()
    image_id = image_data["id"]
    assert image_data["description"] == "Initial Description"
    assert "tags" in image_data

    response = requests.get(f"{BASE_URL}/images/")
    assert response.status_code == 200, f"GET /images/ failed: {response.status_code} {response.text}"
    items = response.json()
    assert any(item["id"] == image_id for item in items)

    response = requests.get(f"{BASE_URL}/images/{image_id}")
    assert response.status_code == 200, f"GET /images/{image_id} failed: {response.status_code} {response.text}"
    assert response.json()["id"] == image_id

    update_data = {"description": "Updated Description"}
    response = requests.patch(f"{BASE_URL}/images/{image_id}", json=update_data)
    assert response.status_code == 200, f"PATCH /images/{image_id} failed: {response.status_code} {response.text}"
    assert response.json()["description"] == "Updated Description"

    response = requests.get(f"{BASE_URL}/images/{image_id}")
    assert response.status_code == 200
    assert response.json()["description"] == "Updated Description"

    response = requests.delete(f"{BASE_URL}/images/{image_id}")
    assert response.status_code == 200, f"DELETE /images/{image_id} failed: {response.status_code} {response.text}"

    response = requests.get(f"{BASE_URL}/images/{image_id}")
    assert response.status_code == 404, f"Expected 404 after delete, got {response.status_code}"
