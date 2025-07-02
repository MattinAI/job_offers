import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Recruitment System"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = ""    
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", 30))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", 60))
    DATABASE_POOL_TIMEOUT: int = int(os.getenv("DATABASE_POOL_TIMEOUT", 60))
    DATABASE_POOL_RECYCLE: int = int(os.getenv("DATABASE_POOL_RECYCLE", 3600))

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
    LANGFLOW_TIMEOUT: int = os.getenv("LANGFLOW_TIMEOUT", 420)
    LANGFLOW_JOB_OFFER_SUMMARY_GENERATION_FLOW_ID: str = os.getenv("LANGFLOW_JOB_OFFER_SUMMARY_GENERATION_FLOW_ID", "")
    LANGFLOW_JOB_OFFER_SKILLS_EXTRACTION_FLOW_ID: str= os.getenv("LANGFLOW_JOB_OFFER_SKILLS_EXTRACTION_FLOW_ID", "")
    LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID: str = os.getenv("LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID", "")
    LANGFLOW_CANDIDATE_SKILLS_EXTRACTION_FLOW_ID: str = os.getenv("LANGFLOW_CANDIDATE_SKILLS_EXTRACTION_FLOW_ID", "")
    LANGFLOW_CANDIDATE_ANONYMIZATION_API_FLOW_ID: str = os.getenv("LANGFLOW_CANDIDATE_ANONYMIZATION_API_FLOW_ID", "")
    LANGFLOW_JOB_OFFER_CANDIDATE_FIT_FLOW_ID: str = os.getenv("LANGFLOW_JOB_OFFER_CANDIDATE_FIT_FLOW_ID", "")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()