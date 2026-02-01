import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def test_endpoints():
    print("1. Testing POST /images/ (Upload)...")
    # Create a dummy file
    with open("test_upload.txt", "w") as f:
        f.write("dummy content")
    
    files = {'file': ('test_upload.txt', open('test_upload.txt', 'rb'))}
    data = {'description': 'Initial Description', 'tags': ['test']}
    
    response = requests.post(f"{BASE_URL}/images/", files=files, data=data)
    if response.status_code != 200:
        print(f"FAILED POST: {response.text}")
        return
    
    image_data = response.json()
    image_id = image_data['id']
    print(f"SUCCESS: Created Image ID {image_id}")
    print(f"Data: {image_data}")
    
    print("\n2. Testing GET /images/ (List)...")
    response = requests.get(f"{BASE_URL}/images/")
    if response.status_code != 200:
        print(f"FAILED GET LIST: {response.text}")
        return
    items = response.json()
    found = any(item['id'] == image_id for item in items)
    print(f"SUCCESS: Retrieved list. Found created ID? {found}")
    
    print(f"\n3. Testing GET /images/{image_id} (Detail)...")
    response = requests.get(f"{BASE_URL}/images/{image_id}")
    if response.status_code != 200:
        print(f"FAILED GET DETAIL: {response.text}")
        return
    print(f"SUCCESS: Retrieved detail: {response.json()}")

    print(f"\n4. Testing PATCH /images/{image_id} (Update)...")
    update_data = {"description": "Updated Description"}
    response = requests.patch(f"{BASE_URL}/images/{image_id}", json=update_data)
    if response.status_code != 200:
        print(f"FAILED PATCH: {response.text}")
        return
    print(f"SUCCESS: Updated record: {response.json()}")
    
    # Verify update
    response = requests.get(f"{BASE_URL}/images/{image_id}")
    assert response.json()['description'] == "Updated Description"
    print("Verified update persisted.")

    print(f"\n5. Testing DELETE /images/{image_id} (Delete)...")
    response = requests.delete(f"{BASE_URL}/images/{image_id}")
    if response.status_code != 200:
        print(f"FAILED DELETE: {response.text}")
        return
    print("SUCCESS: Deleted record.")
    
    print(f"\n6. Testing GET /images/{image_id} (Verify Delete)...")
    response = requests.get(f"{BASE_URL}/images/{image_id}")
    if response.status_code == 404:
        print("SUCCESS: Record correctly not found (404).")
    else:
        print(f"FAILED: Expected 404, got {response.status_code}")

    # Cleanup
    os.remove("test_upload.txt")

if __name__ == "__main__":
    try:
        test_endpoints()
    except Exception as e:
        print(f"An error occurred: {e}")
