# app/api/routers/job_offers.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import logging
from typing import List, Optional

from core.database import get_db
from utils.document_utils import process_document
from utils.langflow_utils import parse_skills_response
from services.langflow_client import langflow_client
from core.config import settings
from repositories.job_offer import job_offer_repository
from repositories.job_offer_skill import job_offer_skill_repository
from schemas.job_offer import JobOfferCreate, JobOfferUpdate, JobOfferWithSkills, JobOfferInDB
from services.storage import minio_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", status_code=status.HTTP_201_CREATED, 
           responses={
               201: {"description": "Job offer created successfully"},
               400: {"description": "Invalid request", "model": dict},
               500: {"description": "Server error", "model": dict}
           })
async def create_job_offer(
    title: str = Form(..., description="Job offer title"),
    document: UploadFile = File(..., description="Job offer description document"),
    db: Session = Depends(get_db)
):
    """
    Create a new job offer with required document upload.
    """
    
    try:
        # Handle validation and text extraction
        extracted_text, text_size_kb = await process_document(document)

        # Upload document to MinIO
        object_name = await minio_service.upload_file(document, minio_service.job_offers_bucket_name)
        logger.info(f"Document uploaded to MinIO with object name: {object_name}")
        
        # Reset file position
        await document.seek(0)

        # Create a summary flow
        summary_flow = langflow_client.flow(
            settings.LANGFLOW_SUMMARY_GENERATION_FLOW_ID,
            tweaks={
                "Agent-gE9mt": {},
                "TextOutput-riQeq": {},
                "TextInput-cTRS8": {
                    "input_value": extracted_text
                },
                "Prompt-kPUCU": {}
            }
        )

        # Create a skills extraction flow
        skills_extraction_flow = langflow_client.flow(
            settings.LANGFLOW_SKILLS_EXTRACTION_FLOW_ID,
            tweaks={
                "Agent-tFpjL": {},
                "TextOutput-9JOx7": {},
                "TextInput-ZLrFC": {
                    "input_value": extracted_text
                },
                "Prompt-NCiV2": {}
            }
        )

        # Run the flow to get summary
        logger.info(f"Calling LangFlow summary API with flow ID: {settings.LANGFLOW_SUMMARY_GENERATION_FLOW_ID}")
        summary_result = await summary_flow.run({
            "output_type": "text",
            "input_type": "text"
        })

        # Run the flow to get skills
        logger.info(f"Calling LangFlow skills API with flow ID: {settings.LANGFLOW_SKILLS_EXTRACTION_FLOW_ID}")
        skills_result = await skills_extraction_flow.run({
            "output_type": "text",
            "input_type": "text"
        })

        summary_text = summary_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]
        skills_text = skills_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]
        logger.info(f"Summary and skills extracted from langflow return")
        
        # Create the job offer with generated summary
        job_offer_data = {
            "title": title,
            "summary": summary_text,
            "storage_url": object_name,
        }
        
        job_offer = job_offer_repository.create(db, obj_in=JobOfferCreate(**job_offer_data))

        skills = parse_skills_response(skills_text)
        job_offer_skill_repository.bulk_create(db=db, job_offer_id=job_offer.id, skills=skills)

        return {"id": job_offer.id, 
            "title": job_offer.title,
            "summary": summary_text,
            "skills": skills_text
        }
    except Exception as e:
        # If any error occurs, clean up if needed
        if 'job_offer' in locals():
            job_offer_repository.remove(db, id=job_offer.id)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Error creating job offer: {str(e)}"}
        )

@router.get("/", response_model=List[JobOfferInDB])
def read_job_offers(
    skip: int = 0,
    limit: int = 100,
    title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all job offers, with optional filtering:
    - title: Filter by title (partial match)
    """
    if title:
        # Filter by title
        return job_offer_repository.get_by_title(db, title=title)
    else:
        # Get all
        return job_offer_repository.get_multi(db, skip=skip, limit=limit)

@router.get("/{job_offer_id}", response_model=JobOfferWithSkills)
def read_job_offer(
    job_offer_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job offer by ID with its skills"""
    job_offer = job_offer_repository.get_with_skills(db, job_offer_id=job_offer_id)
    if not job_offer:
        raise HTTPException(
            status_code=404,
            detail="Job offer not found"
        )
    return job_offer

@router.put("/{job_offer_id}", response_model=JobOfferInDB)
async def update_job_offer(
    job_offer_id: int,
    title: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    replace_file: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Update a job offer with optional file upload.
    
    - title: Updated title (if provided)
    - summary: Updated summary (if provided)
    - file: New file to attach (if provided)
    - replace_file: Whether to replace existing file (true) or keep it (false)
    """
    # Check if job offer exists
    job_offer = job_offer_repository.get(db, id=job_offer_id)
    if not job_offer:
        raise HTTPException(
            status_code=404,
            detail="Job offer not found"
        )
    
    # Prepare update data
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if summary is not None:
        update_data["summary"] = summary
    
    # Update the basic job offer information
    if update_data:
        job_offer = job_offer_repository.update(
            db, db_obj=job_offer, obj_in=JobOfferUpdate(**update_data)
        )
    
    # Handle file upload if a new file is provided
    if file and file.filename:
        # Validate file type
        allowed_types = [
            "application/pdf", 
            "application/msword", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF, Word document, text file, or Excel spreadsheet"
            )
        
        try:
            # Check if there's an existing file to delete
            if replace_file and job_offer.storage_url:
                try:
                    # Try to delete the existing file
                    minio_service.client.remove_object(minio_service.bucket_name, job_offer.storage_url)
                except Exception as e:
                    # Log but continue
                    print(f"Error deleting existing file: {e}")
            
            # Upload the new file
            object_name = await minio_service.upload_file(file)
            
            # Update the job offer with the new storage URL
            job_offer = job_offer_repository.update_storage_url(
                db, job_offer_id=job_offer_id, storage_url=object_name
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error handling file: {str(e)}"
            )
    
    return job_offer

@router.delete("/{job_offer_id}", response_model=JobOfferInDB)
def delete_job_offer(
    job_offer_id: int,
    db: Session = Depends(get_db)
):
    """Delete a job offer"""
    job_offer = job_offer_repository.get(db, id=job_offer_id)
    if not job_offer:
        raise HTTPException(
            status_code=404,
            detail="Job offer not found"
        )
    
    # Delete file from minio is there is one
    if job_offer.storage_url:
        try:
            minio_service.client.remove_object(minio_service.bucket_name, job_offer.storage_url)
        except Exception as e:
            # Log the error but continue with deleting the database entry
            print(f"Error deleting file from MinIO: {e}")
    
    return job_offer_repository.remove(db, id=job_offer_id)
