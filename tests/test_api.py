import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def generate_random_national_id():
    # Returns a unique 12-digit numeric string
    return str(uuid.uuid4().int)[:12].zfill(12)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_beneficiary_success():
    nid = generate_random_national_id()
    payload = {
        "full_name": "Aarav Sharma",
        "email": f"aarav_{nid[:4]}@example.com",
        "phone": "9876543210",
        "national_id": nid,
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["national_id"] == nid
    assert data["status"] == "PENDING"
    assert "reference_id" in data

def test_duplicate_national_id_fails():
    nid = generate_random_national_id()
    payload = {
        "full_name": "Priya Patel",
        "email": f"priya_{nid[:4]}@example.com",
        "phone": "8765432109",
        "national_id": nid,
        "scheme": "Healthcare Subsidy"
    }
    # First registration
    res1 = client.post("/api/register", json=payload)
    assert res1.status_code == 201

    # Second registration with exact same national_id
    res2 = client.post("/api/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]

def test_status_lookup_by_ref_id():
    nid = generate_random_national_id()
    payload = {
        "full_name": "Rohan Deshmukh",
        "email": f"rohan_{nid[:4]}@example.com",
        "phone": "7654321098",
        "national_id": nid,
        "scheme": "Housing Support"
    }
    reg_res = client.post("/api/register", json=payload)
    assert reg_res.status_code == 201
    ref_id = reg_res.json()["reference_id"]

    status_res = client.get(f"/api/status/{ref_id}")
    assert status_res.status_code == 200
    assert status_res.json()["reference_id"] == ref_id
    assert status_res.json()["status"] == "PENDING"

def test_admin_approval_and_rejection_workflow():
    # 1. Create a beneficiary
    nid = generate_random_national_id()
    payload = {
        "full_name": "Neha Joshi",
        "email": f"neha_{nid[:4]}@example.com",
        "phone": "9123456780",
        "national_id": nid,
        "scheme": "Education Grant"
    }
    reg_res = client.post("/api/register", json=payload)
    assert reg_res.status_code == 201
    ref_id = reg_res.json()["reference_id"]

    # 2. Authenticate as Admin
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Approve application
    approve_res = client.put(f"/api/admin/verify/{ref_id}", headers=headers, json={"status": "APPROVED"})
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 4. Reject application
    reject_res = client.put(f"/api/admin/verify/{ref_id}", headers=headers, json={"status": "REJECTED"})
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"