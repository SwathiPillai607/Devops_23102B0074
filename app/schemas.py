from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# Schema for incoming registration data
class BeneficiaryCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    national_id: str = Field(..., min_length=4, max_length=50)
    scheme: str = Field(..., min_length=2, max_length=100)

# Schema for returning beneficiary details
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

    class Config:
        from_attributes = True

# Schema for admin updating status
class StatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(APPROVED|REJECTED)$")