import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import Beneficiary
from app.schemas import BeneficiaryCreate, BeneficiaryResponse, StatusUpdate

# Create the database table automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Beneficiary Registration Portal",
    version="1.0.0",
    description="Backend API for Beneficiary Self-Registration and Admin Verification"
)

def generate_reference_id() -> str:
    """Generate a unique reference code like BEN-A1B2C3D4"""
    return f"BEN-{uuid.uuid4().hex[:8].upper()}"

# 1. Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "beneficiary-portal"}

# 2. Beneficiary self-registration endpoint
@app.post("/api/register", response_model=BeneficiaryResponse, status_code=201)
def register_beneficiary(data: BeneficiaryCreate, db: Session = Depends(get_db)):
    # Check if this National ID is already registered
    existing = db.query(Beneficiary).filter(Beneficiary.national_id == data.national_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Beneficiary with National ID '{data.national_id}' is already registered."
        )

    new_beneficiary = Beneficiary(
        reference_id=generate_reference_id(),
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        national_id=data.national_id,
        scheme=data.scheme,
        status="PENDING"
    )
    db.add(new_beneficiary)
    db.commit()
    db.refresh(new_beneficiary)
    return new_beneficiary

# 3. Status lookup by Reference ID
@app.get("/api/status/{ref_id}", response_model=BeneficiaryResponse)
def get_status(ref_id: str, db: Session = Depends(get_db)):
    record = db.query(Beneficiary).filter(Beneficiary.reference_id == ref_id.upper()).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No registration found for Reference ID '{ref_id}'."
        )
    return record

# 4. Admin listing of all applications
@app.get("/api/admin/records", response_model=List[BeneficiaryResponse])
def list_records(db: Session = Depends(get_db)):
    return db.query(Beneficiary).order_by(Beneficiary.created_at.desc()).all()

# 5. Admin verification decision (APPROVED or REJECTED)
@app.put("/api/admin/verify/{ref_id}", response_model=BeneficiaryResponse)
def verify_application(ref_id: str, update: StatusUpdate, db: Session = Depends(get_db)):
    record = db.query(Beneficiary).filter(Beneficiary.reference_id == ref_id.upper()).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No registration found for Reference ID '{ref_id}'."
        )
    record.status = update.status
    db.commit()
    db.refresh(record)
    return record