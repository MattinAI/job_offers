# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from core.config import settings
from api.routers import job_offers, candidates, job_offer_candidates
from db.models import Base
from core.database import engine
from services.storage import minio_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Acquire lock to prevent race condition
                conn.execute(text("LOCK TABLE pg_catalog.pg_namespace IN SHARE ROW EXCLUSIVE MODE"))
                Base.metadata.create_all(bind=conn, checkfirst=True)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    logger.info("Ensuring MinIO buckets exists...")
    try:
        minio_service._ensure_bucket_exists()
        logger.info("MinIO bucket setup complete.")
    except Exception as e:
        logger.error(f"Error setting up MinIO bucket: {e}")
    
    yield
    
    # Shutdown 
    logger.info("Application shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
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
app.include_router(
    job_offer_candidates.router,
    prefix=f"{settings.API_V1_STR}"
)

@app.get("/")
def root():
    return {"message": "Welcome to the Recruitment System API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
