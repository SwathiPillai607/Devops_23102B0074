import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def generate_random_national_id():
    return str(uuid.uuid4().int)[:12].zfill(12)

def test_valid_beneficiary_registration():
    nid = generate_random_national_id()
    payload = {
        "full_name": "Swathi Pillai",
        "email": f"swathi_{nid[:4]}@example.com",
        "phone": "9876543210",
        "national_id": nid,
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["national_id"] == nid
    assert data["reference_id"].startswith("BEN-")

def test_national_id_less_than_12_digits():
    payload = {
        "full_name": "Valid Name",
        "email": "valid1@example.com",
        "phone": "9876543210",
        "national_id": "12345678901",  # 11 digits
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

def test_national_id_more_than_12_digits():
    payload = {
        "full_name": "Valid Name",
        "email": "valid2@example.com",
        "phone": "9876543210",
        "national_id": "1234567890123",  # 13 digits
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

def test_national_id_contains_letters_or_special_chars():
    payload = {
        "full_name": "Valid Name",
        "email": "valid3@example.com",
        "phone": "9876543210",
        "national_id": "12345678901A",  # Contains letter
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

    payload["national_id"] = "123456-89012"  # Contains hyphen
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

def test_invalid_email_formats():
    nid = generate_random_national_id()
    # Missing @ symbol
    payload = {
        "full_name": "Valid Name",
        "email": "plainaddress.com",
        "phone": "9876543210",
        "national_id": nid,
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

    # Missing top-level domain
    payload["email"] = "user@domain"
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

def test_phone_number_starting_digit_and_length():
    nid = generate_random_national_id()
    # Starts with 5 (disallowed)
    payload = {
        "full_name": "Valid Name",
        "email": f"phone_{nid[:4]}@example.com",
        "phone": "5876543210",
        "national_id": nid,
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

    # Less than 10 digits
    payload["phone"] = "987654321"
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

def test_name_must_be_letters_and_more_than_two_characters():
    nid = generate_random_national_id()
    # 2 or fewer characters
    payload = {
        "full_name": "Al",
        "email": f"name_{nid[:4]}@example.com",
        "phone": "9876543210",
        "national_id": nid,
        "scheme": "Education Grant"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422

    # Contains numbers
    payload["full_name"] = "Swathi123"
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422