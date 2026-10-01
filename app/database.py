from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Uses a local SQLite file named 'beneficiaries.db'
DATABASE_URL = "sqlite:///./beneficiaries.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to provide a database session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()