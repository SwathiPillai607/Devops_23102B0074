import uuid
from pathlib import Path
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import Beneficiary
from app.schemas import BeneficiaryCreate, BeneficiaryResponse, StatusUpdate

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Beneficiary Registration Portal",
    version="1.0.0"
)

# Robust directory path resolution for Jinja2
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def generate_reference_id() -> str:
    return f"BEN-{uuid.uuid4().hex[:8].upper()}"

# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "beneficiary-portal"}

# --- Web UI Pages (Using updated FastAPI / Starlette keyword syntax) ---
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/status-page", response_class=HTMLResponse)
def status_page(request: Request):
    return templates.TemplateResponse(request=request, name="status.html")

@app.get("/admin-page", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

# --- REST APIs ---
@app.post("/api/register", response_model=BeneficiaryResponse, status_code=201)
def register_beneficiary(data: BeneficiaryCreate, db: Session = Depends(get_db)):
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

@app.get("/api/status/{ref_id}", response_model=BeneficiaryResponse)
def get_status(ref_id: str, db: Session = Depends(get_db)):
    record = db.query(Beneficiary).filter(Beneficiary.reference_id == ref_id.upper()).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No registration found for Reference ID '{ref_id}'."
        )
    return record

@app.get("/api/admin/records", response_model=List[BeneficiaryResponse])
def list_records(db: Session = Depends(get_db)):
    return db.query(Beneficiary).order_by(Beneficiary.created_at.desc()).all()

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