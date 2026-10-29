import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app import models, schemas, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Beneficiary Registration Portal API",
    description="Enterprise Multi-Role Citizen Benefit Management & Verification System",
    version="2.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- Health Check ---
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "beneficiary-portal", "version": "2.0.0"}

# --- Web UI Routes ---
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin-page", response_class=HTMLResponse)
@app.get("/admin/login", response_class=HTMLResponse)
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/status-page", response_class=HTMLResponse)
def status_page(request: Request):
    return templates.TemplateResponse(request=request, name="status.html")

# --- Authentication API ---
@app.post("/api/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role = "ADMIN" if user_in.role == "ADMIN" else "USER"
    hashed_pwd = auth.get_password_hash(user_in.password)
    user = models.User(username=user_in.username, email=user_in.email, hashed_password=hashed_pwd, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/api/auth/login", response_model=schemas.Token, tags=["Auth"])
def login(login_data: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == login_data.username).first()
    if not user or not auth.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, samesite="lax")
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": user.username}

@app.post("/api/auth/logout", tags=["Auth"])
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}

# --- Beneficiary API ---
@app.post("/api/register", response_model=schemas.BeneficiaryResponse, status_code=status.HTTP_201_CREATED, tags=["Beneficiary"])
def register_beneficiary(
    beneficiary: schemas.BeneficiaryCreate,
    db: Session = Depends(get_db)
):
    if db.query(models.Beneficiary).filter(models.Beneficiary.national_id == beneficiary.national_id).first():
        raise HTTPException(status_code=400, detail="National ID is already registered in the system")

    ref_token = f"BEN-{uuid.uuid4().hex[:6].upper()}"
    new_record = models.Beneficiary(
        reference_id=ref_token,
        full_name=beneficiary.full_name,
        email=beneficiary.email,
        phone=beneficiary.phone,
        national_id=beneficiary.national_id,
        scheme=beneficiary.scheme,
        status="PENDING"
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

@app.get("/api/my-applications", response_model=List[schemas.BeneficiaryResponse], tags=["Beneficiary"])
def get_user_applications(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Beneficiary).filter(models.Beneficiary.user_id == current_user.id).all()

@app.get("/api/status/{ref_id}", response_model=schemas.BeneficiaryResponse, tags=["Beneficiary"])
def get_status(ref_id: str, db: Session = Depends(get_db)):
    record = db.query(models.Beneficiary).filter(models.Beneficiary.reference_id == ref_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application Reference ID not found")
    return record

# --- Admin API (Role-Protected) ---
@app.get("/api/admin/records", response_model=List[schemas.BeneficiaryResponse], tags=["Admin"])
def get_all_records(
    admin_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    return db.query(models.Beneficiary).order_by(models.Beneficiary.created_at.desc()).all()

@app.put("/api/admin/verify/{ref_id}", response_model=schemas.BeneficiaryResponse, tags=["Admin"])
def verify_application(
    ref_id: str,
    status_update: schemas.BeneficiaryStatusUpdate,
    admin_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    record = db.query(models.Beneficiary).filter(models.Beneficiary.reference_id == ref_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application Reference ID not found")
    
    if status_update.status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be either APPROVED or REJECTED")

    record.status = status_update.status
    db.commit()
    db.refresh(record)
    return record