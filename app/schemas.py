import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    role: Optional[str] = "USER"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", clean):
            raise ValueError("Invalid email format. Must contain @ and a valid domain (e.g., .com, .in)")
        return clean

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class BeneficiaryCreate(BaseModel):
    full_name: str
    email: str
    phone: str
    national_id: str
    scheme: str

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean_name = v.strip()
        if len(clean_name) <= 2:
            raise ValueError("Name must be more than 2 characters")
        if not re.match(r"^[A-Za-z\s]+$", clean_name):
            raise ValueError("Name must contain only letters and spaces")
        return clean_name

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", clean):
            raise ValueError("Invalid email format. Must contain @ and a valid domain (e.g., .com, .in)")
        return clean

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, v: str) -> str:
        clean_id = v.strip()
        if not re.match(r"^\d{12}$", clean_id):
            raise ValueError("National ID must be exactly 12 digits containing only numbers")
        return clean_id

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_phone = v.strip()
        if not re.match(r"^[6-9]\d{9}$", clean_phone):
            raise ValueError("Phone number must be exactly 10 digits starting with 6, 7, 8, or 9")
        return clean_phone

class BeneficiaryStatusUpdate(BaseModel):
    status: str

class BeneficiaryResponse(BaseModel):
    id: int
    reference_id: str
    full_name: str
    email: str
    phone: str
    national_id: str
    scheme: str
    status: str
    created_at: datetime
    user_id: Optional[int] = None

    class Config:
        from_attributes = True