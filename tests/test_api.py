import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models, auth

# StaticPool ensures all threads and requests share the exact same in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# --- Health & Diagnostic Tests ---
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# --- User & Admin Authentication Tests ---
def test_user_registration_success(client):
    payload = {
        "username": "citizen_john",
        "email": "john@example.com",
        "password": "Password123",
        "role": "USER"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["username"] == "citizen_john"
    assert response.json()["role"] == "USER"

def test_duplicate_user_registration_fails(client):
    payload = {
        "username": "citizen_john",
        "email": "john@example.com",
        "password": "Password123"
    }
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_user_login_success(client):
    client.post("/api/auth/register", json={
        "username": "citizen_jane",
        "email": "jane@example.com",
        "password": "SecretPassword"
    })
    response = client.post("/api/auth/login", json={
        "username": "citizen_jane",
        "password": "SecretPassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["role"] == "USER"

def test_invalid_login_credentials_fail(client):
    response = client.post("/api/auth/login", json={
        "username": "non_existent_user",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]

# --- Role-Based Access Control (RBAC) Guard Tests ---
def test_unauthenticated_user_cannot_access_admin_records(client):
    response = client.get("/api/admin/records")
    assert response.status_code == 401

def test_citizen_user_forbidden_from_admin_records(client, db_session):
    user = models.User(
        username="regular_user",
        email="regular@example.com",
        hashed_password=auth.get_password_hash("password"),
        role="USER"
    )
    db_session.add(user)
    db_session.commit()
    
    token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/admin/records", headers=headers)
    assert response.status_code == 403
    assert "Administrator privileges required" in response.json()["detail"]

def test_admin_user_can_access_admin_records(client, db_session):
    admin = models.User(
        username="admin_officer",
        email="officer@example.com",
        hashed_password=auth.get_password_hash("adminpass"),
        role="ADMIN"
    )
    db_session.add(admin)
    db_session.commit()
    
    token = auth.create_access_token(data={"sub": admin.username, "role": admin.role})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/admin/records", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# --- Beneficiary Application & Lifecycle Tests ---
def test_register_beneficiary_success(client):
    payload = {
        "full_name": "Anita Verma",
        "email": "anita@example.com",
        "phone": "+919876543210",
        "national_id": "NID-998877",
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["reference_id"].startswith("BEN-")
    assert data["status"] == "PENDING"
    assert data["national_id"] == "NID-998877"

def test_duplicate_national_id_fails(client):
    payload = {
        "full_name": "Anita Verma",
        "email": "anita@example.com",
        "phone": "+919876543210",
        "national_id": "NID-DUPLICATE",
        "scheme": "Education Grant"
    }
    client.post("/api/register", json=payload)
    response = client.post("/api/register", json=payload)
    assert response.status_code == 400
    assert "National ID is already registered" in response.json()["detail"]

def test_status_lookup_by_ref_id(client):
    payload = {
        "full_name": "Karan Mehra",
        "email": "karan@example.com",
        "phone": "+919876543211",
        "national_id": "NID-554433",
        "scheme": "Healthcare Assistance"
    }
    reg_response = client.post("/api/register", json=payload)
    ref_id = reg_response.json()["reference_id"]

    status_response = client.get(f"/api/status/{ref_id}")
    assert status_response.status_code == 200
    assert status_response.json()["reference_id"] == ref_id
    assert status_response.json()["status"] == "PENDING"

def test_admin_approval_and_rejection_workflow(client, db_session):
    admin = models.User(
        username="super_admin",
        email="super@example.com",
        hashed_password=auth.get_password_hash("superpass"),
        role="ADMIN"
    )
    db_session.add(admin)
    db_session.commit()
    admin_token = auth.create_access_token(data={"sub": admin.username, "role": admin.role})
    headers = {"Authorization": f"Bearer {admin_token}"}

    reg_response = client.post("/api/register", json={
        "full_name": "Pooja Shah",
        "email": "pooja@example.com",
        "phone": "+919876543212",
        "national_id": "NID-112233",
        "scheme": "Rural Housing Subsidy"
    })
    ref_id = reg_response.json()["reference_id"]

    approve_res = client.put(f"/api/admin/verify/{ref_id}", json={"status": "APPROVED"}, headers=headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    reject_res = client.put(f"/api/admin/verify/{ref_id}", json={"status": "REJECTED"}, headers=headers)
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"