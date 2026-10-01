from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    national_id = Column(String(50), unique=True, index=True, nullable=False)
    scheme = Column(String(100), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)