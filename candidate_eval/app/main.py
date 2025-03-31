from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn

from core.config import settings
from api.routers import job_offers, candidates
from db.models import Base
from core.database import engine
from services.storage import minio_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
logger.info("Creating database tables...")
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully.")

# Ensure MinIO bucket exists
logger.info("Ensuring MinIO buckets exists...")
try:
    minio_service._ensure_bucket_exists()
    logger.info("MinIO bucket setup complete.")
except Exception as e:
    logger.error(f"Error setting up MinIO bucket: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    job_offers.router,
    prefix=f"{settings.API_V1_STR}/job-offers",
    tags=["job-offers"]
)
app.include_router(
    candidates.router,
    prefix=f"{settings.API_V1_STR}/candidates",
    tags=["candidates"]
)

@app.get("/")
def root():
    return {"message": "Welcome to the Recruitment System API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)