import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Recruitment System"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://recruiter:password@localhost:5432/recruitment")
    
    # MinIO
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    MINIO_URL: str = os.getenv("MINIO_URL", "localhost:9000")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"
    MINIO_CANDIDATES_BUCKET_NAME: str = os.getenv("MINIO_CANDIDATES_BUCKET_NAME", "cvs")
    MINIO_JOB_OFFERS_BUCKET_NAME: str = os.getenv("MINIO_JOB_OFFERS_BUCKET_NAME", "job_offers")

    # LangFlow API
    LANGFLOW_API_URL: str = os.getenv("LANGFLOW_API_URL", "localhost:7860")
    LANGFLOW_API_KEY: str = os.getenv("LANGFLOW_API_KEY", "sdfsfsd")
    LANGFLOW_TIMEOUT: int = os.getenv("LANGFLOW_TIMEOUT", 30)
    LANGFLOW_SUMMARY_GENERATION_FLOW_ID: str = os.getenv("LANGFLOW_SUMMARY_GENERATION_FLOW_ID", "")
    LANGFLOW_SKILLS_EXTRACTION_FLOW_ID: str= os.getenv("LANGFLOW_SKILLS_EXTRACTION_FLOW_ID", "")
    LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID: str = os.getenv("LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID", "")

    class Config:
        case_sensitive = True

settings = Settings()