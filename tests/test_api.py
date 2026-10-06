import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# Use an isolated, in-memory SQLite database specifically for running tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

# 1. Health Check Test
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "beneficiary-portal"}

# 2. Beneficiary Self-Registration Test
def test_register_beneficiary(client):
    payload = {
        "full_name": "Test Beneficiary",
        "email": "test.beneficiary@example.com",
        "phone": "9876543210",
        "national_id": "NID-TEST-001",
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Test Beneficiary"
    assert data["status"] == "PENDING"
    assert data["reference_id"].startswith("BEN-")

# 3. Duplicate National ID Prevention Test
def test_duplicate_national_id_fails(client):
    payload = {
        "full_name": "Applicant One",
        "email": "applicant1@example.com",
        "phone": "9876543210",
        "national_id": "NID-DUPLICATE",
        "scheme": "Healthcare Assistance"
    }
    first_resp = client.post("/api/register", json=payload)
    assert first_resp.status_code == 201

    duplicate_resp = client.post("/api/register", json=payload)
    assert duplicate_resp.status_code == 400
    assert "already registered" in duplicate_resp.json()["detail"]

# 4. Status Lookup Test
def test_status_lookup(client):
    payload = {
        "full_name": "Lookup Applicant",
        "email": "lookup@example.com",
        "phone": "9876543210",
        "national_id": "NID-LOOKUP-01",
        "scheme": "Rural Housing Subsidy"
    }
    reg_resp = client.post("/api/register", json=payload)
    ref_id = reg_resp.json()["reference_id"]

    lookup_resp = client.get(f"/api/status/{ref_id}")
    assert lookup_resp.status_code == 200
    assert lookup_resp.json()["reference_id"] == ref_id
    assert lookup_resp.json()["status"] == "PENDING"

# 5. Admin Approval Workflow Test
def test_admin_approval(client):
    payload = {
        "full_name": "Admin Test Applicant",
        "email": "admintest@example.com",
        "phone": "9876543210",
        "national_id": "NID-ADMIN-01",
        "scheme": "Education Grant"
    }
    reg_resp = client.post("/api/register", json=payload)
    ref_id = reg_resp.json()["reference_id"]

    update_resp = client.put(f"/api/admin/verify/{ref_id}", json={"status": "APPROVED"})
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "APPROVED"

    check_resp = client.get(f"/api/status/{ref_id}")
    assert check_resp.json()["status"] == "APPROVED"