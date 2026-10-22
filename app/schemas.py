from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Auth Schemas ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "USER"

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

# --- Beneficiary Schemas ---
class BeneficiaryCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    national_id: str
    scheme: str

class BeneficiaryStatusUpdate(BaseModel):
    status: str

class BeneficiaryResponse(BaseModel):
    reference_id: str
    full_name: str
    email: EmailStr
    phone: str
    national_id: str
    scheme: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}