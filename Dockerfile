# Use an official lightweight Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to optimize Python for containers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install minimal system dependencies required for building Python cryptographic packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition first (takes advantage of Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code, templates, and static assets
COPY app/ ./app/

# Seed default admin user inside the container database
RUN python -c "from app.database import Base, engine, SessionLocal; from app.models import User; from app.auth import get_password_hash; Base.metadata.create_all(bind=engine); db = SessionLocal(); db.query(User).filter(User.username=='admin').first() or (db.add(User(username='admin', email='admin@example.com', hashed_password=get_password_hash('Admin@123'), role='ADMIN')), db.commit()); db.close()"

# Expose the application port
EXPOSE 8000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]