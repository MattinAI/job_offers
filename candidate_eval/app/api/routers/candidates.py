# app/api/routers/job_offers.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import logging
import json
from typing import List, Optional

from core.database import get_db
from utils.document_utils import process_document
from utils.skills_utils import parse_skills_response
from utils.anom_utils import SelectiveAnonymizer
from services.langflow_client import langflow_client
from core.config import settings
from repositories.candidate import candidate_repository
from repositories.job_offer_candidate import job_offer_candidate_repository
from repositories.candidate_skill import candidate_skill_repository
from schemas.candidates import CandidateBase, CandidateCreate, CandidateInDB, CandidateResponse  
from services.storage import minio_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", status_code=status.HTTP_201_CREATED, 
           responses={
               201: {"description": "Candidate created successfully"},
               400: {"description": "Invalid request", "model": dict},
               500: {"description": "Server error", "model": dict}
           })
async def create_candidate(
    document: UploadFile = File(..., description="Candidate CV"),
    db: Session = Depends(get_db)
):
    """
    Create a new job offer with required document upload.
    """
    
    try:
        # Handle validation and text extraction
        extracted_text, text_size_kb = await process_document(document)

        # Upload document to MinIO
        object_name = await minio_service.upload_file(document, minio_service.candidates_bucket_name)
        minio_url = f"{minio_service.candidates_bucket_name}/{object_name}"
        logger.info(f"Document uploaded to MinIO with object name: {object_name}")
        
        # Reset file position
        await document.seek(0)

        # Create and anonymization flow
        anom_flow = langflow_client.flow(settings.LANGFLOW_CANDIDATE_ANONYMIZATION_API_FLOW_ID)
    
        # Run the flow to get anonimization
        logger.info(f"Calling LangFlow anonimization API with flow ID: {settings.LANGFLOW_CANDIDATE_ANONYMIZATION_API_FLOW_ID}")
        anom_result = await anom_flow.run({
            "output_type": "text",
            "input_type": "text", 
            "input_value": extracted_text
        })

        # Extract the result text containing detected entities
        presidio_output = json.loads(anom_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"])
        logger.info("PII detection completed")

        # Parse the Presidio output to get entities
        entities = presidio_output['entities']

        # Sort entities by their position in the text
        sorted_entities = sorted(entities, key=lambda e: e["start"])

        # Extract the first occurrence of a person's name
        person_name = None
        for entity in sorted_entities:
            if entity["entity_type"] == "PERSON":
                person_name = entity["text"]
                break

        # Define selective anonymization rules
        anonymization_rules = {
            "first_occurrence_only": ["PERSON"],
            "all_occurrences": ["EMAIL_ADDRESS", "URL", "PHONE_NUMBER", "CREDIT_CARD", "IP_ADDRESS", "ES_NIF", "ES_NIE"],
            "ignore_types": []        
            }
        
        # Apply selective anonymization on the original text
        anonymized_text = SelectiveAnonymizer.anonymize_original_text(
            extracted_text,  
            entities,
            anonymization_rules
        )

        logger.info("Selective anonymization completed")

        # Create a summary and skill extraction flow
        summary_flow = langflow_client.flow(settings.LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID)
        skills_extraction_flow = langflow_client.flow(settings.LANGFLOW_CANDIDATE_SKILLS_EXTRACTION_FLOW_ID,
                                                    tweaks={
                                                    "TextInput-FCe1H": {
                                                        "input_value": anonymized_text
                                                    },
                                                })

        # Run the flow to get summary
        logger.info(f"Calling LangFlow summary API with flow ID: {settings.LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID}")
        summary_result = await summary_flow.run({
            "output_type": "text",
            "input_type": "text",
            "input_value": anonymized_text       
            })

        # Run the flow to get skills
        logger.info(f"Calling LangFlow skills API with flow ID: {settings.LANGFLOW_CANDIDATE_SKILLS_EXTRACTION_FLOW_ID}")
        skills_result = await skills_extraction_flow.run({
            "output_type": "text",
            "input_type": "text"
            })

        summary_text = summary_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]
        skills_text = skills_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]
        logger.info(f"Summary and skills extracted from langflow return")
        
        # Create the job offer with generated summary
        candidate_data = {
            "name": person_name if person_name else "Anonymous Candidate",
            "summary": summary_text,
            "storage_url": minio_url
        }
        
        candidate = candidate_repository.create(db, obj_in=CandidateCreate(**candidate_data))

        skills = parse_skills_response(skills_text)
        created_skills = candidate_skill_repository.bulk_create(db=db, candidate_id=candidate.id, skills=skills, skill_type="candidate")

        # Extract skill names for the response
        skill_details = [
            {
                "id": skill.id,
                "skill": skill.skill.name,  
                "type": skill.skill.type,   
                "expertise_level": skill.expertise_level
            }
            for skill in created_skills
        ]

        return {"id": candidate.id, 
            "name": candidate.name,
            "summary": summary_text,
            "sotrage_url": candidate.storage_url,
            "skills": skill_details
        }
    except Exception as e:
        # If any error occurs, clean up if needed
        if 'job_offer' in locals():
            candidate_skill_repository.remove(db, id=candidate.id)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Error creating job offer: {str(e)}"}
        )

@router.get("/", response_model=List[CandidateInDB])
def read_candidates(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all job offers, with optional filtering:
    - title: Filter by title (partial match)
    """
    if name:
        # Filter by title
        return candidate_repository.get_by_name(db, name=name)
    else:
        # Get all
        return candidate_repository.get_multi(db, skip=skip, limit=limit)

@router.get("/{candidate_id}", response_model=CandidateResponse)
def read_candidate(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job offer by ID with its skills"""
    candidate = candidate_repository.get_with_skills(db, candidate_id=candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found"
        )
    return candidate

@router.delete("/{candidate_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               responses={
                   204: {"description": "Candidate removed from job offer successfully"},
                   404: {"description": "Resource not found", "model": dict},
                   500: {"description": "Server error", "model": dict}
               })
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Delete a candidate and all associated data"""
        
    candidate = candidate_repository.get(db, id=candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found"
        )
    
    # Delete file from minio is there is one
    if candidate.storage_url:
        try:
            minio_service.client.remove_object(minio_service.candidates_bucket_name, candidate.storage_url)
        except Exception as e:
            # Log the error but continue with deleting the database entry
            print(f"Error deleting file from MinIO: {e}")
    
    return candidate_repository.remove(db, id=candidate_id)
