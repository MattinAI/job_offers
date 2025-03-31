from minio import Minio
from minio.error import S3Error
import os
from fastapi import UploadFile
import io
from core.config import settings
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinioService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_URL,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_SECURE
        )
        self.job_offers_bucket_name = settings.MINIO_JOB_OFFERS_BUCKET_NAME
        self.candidates_bucket_name = settings.MINIO_CANDIDATES_BUCKET_NAME
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create it if it doesn't"""
        for bucket_name in [self.job_offers_bucket_name, self.candidates_bucket_name]:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info(f"Bucket '{bucket_name}' created successfully")
                else: 
                    logger.info(f"Bucket '{bucket_name}' already exists")
            except S3Error as e:
                logger.error(f"Error ensuring bucket exists: {e}")
    
    async def upload_file(self, file: UploadFile, bucket_name: str) -> str:
        """Upload a file to MinIO and return its path"""
        try:
            # Generate a unique filename
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ''
            object_name = f"{uuid.uuid4()}{file_extension}"
            
            # Read the file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=io.BytesIO(file_content),
                length=file_size,
                content_type=file.content_type
            )
            
            return object_name
        except S3Error as e:
            print(f"Error uploading file: {e}")
            raise

    def get_file_url(self, object_name: str) -> str:
        """Get a presigned URL for accessing a file"""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            return url
        except S3Error as e:
            print(f"Error getting file URL: {e}")
            raise

# Initialize the MinIO service
minio_service = MinioService()