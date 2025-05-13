# app/api/routers/job_offer_candidates.py
from typing import List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Path
from sqlalchemy.orm import Session
import logging
import json
import ast

from core.database import get_db
from utils.document_utils import process_document
from utils.skills_utils import parse_skills_response
from utils.anom_utils import SelectiveAnonymizer
from schemas.job_offer_candidate import JobOfferCandidateCreate, JobOfferCandidateDetail, JobOfferCandidateInDB
from schemas.candidates import CandidateBase, CandidateCreate, CandidateInDB, CandidateResponse  
from repositories.job_offer import job_offer_repository
from repositories.candidate import candidate_repository
from repositories.candidate_skill import candidate_skill_repository
from repositories.job_offer_candidate import job_offer_candidate_repository
from services.langflow_client import langflow_client
from core.config import settings
from services.storage import minio_service

router = APIRouter(prefix="/job-offers/{job_offer_id}/candidates", tags=["Job Offer Candidates"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=JobOfferCandidateDetail, 
            status_code=status.HTTP_201_CREATED,
            responses={
                201: {"description": "Candidate added to the job offer"},
                400: {"description": "Invalid request", "model": dict},
                500: {"description": "Server error", "model": dict}
            })
async def create_job_offer_candidate(
    job_offer_id: int = Path(..., description="ID of the job offer"),
    document: UploadFile = File(..., description="Candidate CV"),
    db: Session = Depends(get_db)
):
    """
    Add a new candidate to the platform and link it to a job offer.
    """
    try:
        # Verify job offer exists
        job_offer = job_offer_repository.get(db, id=job_offer_id)
        if not job_offer:
            raise HTTPException(status_code=404, detail="Job offer not found")
        
        # Process document and extract text
        extracted_text, text_size_kb = await process_document(document)
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
            "ignore_types": [],  
            "min_score": 0.5  
        }
        
        # Apply selective anonymization on the original text
        anonymized_text = SelectiveAnonymizer.anonymize_original_text(
            extracted_text,  
            entities,
            anonymization_rules
        )

        logger.info("Selective anonymization completed")

        # Generate summary and extract skills
        summary_flow = langflow_client.flow(settings.LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID)
        skills_extraction_flow = langflow_client.flow(settings.LANGFLOW_CANDIDATE_SKILLS_EXTRACTION_FLOW_ID,
                                                    tweaks={
                                                    "TextInput-FCe1H": {
                                                        "input_value": anonymized_text
                                                    },
                                                })    

        logger.info(f"Calling LangFlow cv summary flow with flow ID: {settings.LANGFLOW_CANDIDATE_SUMMARY_GENERATION_FLOW_ID}")
        summary_result = await summary_flow.run({
            "output_type": "text",
            "input_type": "text", 
            "input_value": anonymized_text
        })

        logger.info(f"Calling LangFlow cv skills extraction flow with flow ID: {settings.LANGFLOW_CANDIDATE_SKILLS_EXTRACTION_FLOW_ID}")
        skills_result = await skills_extraction_flow.run({
            "output_type": "text",
            "input_type": "text"        
        })
        
        summary_text = summary_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]
        skills_text = skills_result["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]
        logger.info(f"Summary and skills extracted from langflow return")

        # Create candidate
        candidate_data = {
            "name": person_name if person_name else "Anonymous Candidate",
            "summary": summary_text,
            "storage_url": minio_url
        }

        logger.info(f"Creating candidate in database with data: {candidate_data}")
        candidate = candidate_repository.create(db, obj_in=CandidateCreate(**candidate_data))

        # Extract and save skills
        skills = parse_skills_response(skills_text)
        logger.info(f"Creating candidate skills from LangFlow: {skills}")
        created_skills = candidate_skill_repository.bulk_create(db=db, candidate_id=candidate.id, skills=skills, skill_type="candidate")

        # Format data for fit score calculation
        job_offer_dict = {
            "id": job_offer.id,
            "skills": [
                {
                    "skill": skill.skill.name,
                    "priority": skill.priority,
                    "expertise_level": skill.expertise_level
                }
                for skill in job_offer.skills
            ]
        }
        
        candidate_dict = {
            "id": candidate.id,
            "skills": [
                {
                    "skill": skill.skill.name,
                    "expertise_level": skill.expertise_level
                }
                for skill in created_skills
            ]
        }
        
        # Calculate fit score
        fit_score, cot_summary = await _calculate_fit_score(job_offer_dict, candidate_dict)

        # Create job offer candidate association
        job_offer_candidate_data = {
            "candidate_id": candidate.id,
            "job_offer_id": job_offer_id,
            "fit_score": fit_score, 
            "cot_summary": cot_summary
        }

        # Link candidate to job offer
        job_offer_candidate = job_offer_candidate_repository.create(db, obj_in=JobOfferCandidateCreate(**job_offer_candidate_data))

        # Format skills for response
        skill_details = [
            {
                "name": skill.skill.name,
                "expertise_level": skill.expertise_level
            }
            for skill in created_skills
        ]

        return {
            "id": job_offer_candidate.id,
            "candidate_id": candidate.id,
            "job_offer_id": job_offer_id,
            "name": candidate.name,
            "summary": candidate.summary,
            "document": candidate.storage_url,
            "fit_score": job_offer_candidate.fit_score,
            "skills": skill_details
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Error adding candidate: {str(e)}"}
        )

@router.get("/", response_model=List[JobOfferCandidateDetail],
            status_code=status.HTTP_200_OK,
            responses={
                200: {"description": "List of candidates linked to job offer, order by descending fit score"},
                404: {"description": "Resource not found", "model": dict},
                500: {"description": "Server error", "model": dict}
            })
async def get_candidates_by_job_offer(
    job_offer_id: int = Path(..., description="ID of the job offer"),
    db: Session = Depends(get_db)
):
    """
    Get a list of candidates linked to a job offer, ordered by descending fit score
    """
    try:
        # Verify job offer exists
        job_offer = job_offer_repository.get(db, id=job_offer_id)
        if not job_offer:
            raise HTTPException(status_code=404, detail="Job offer not found")

        # Get candidates linked to the job offer
        candidates = job_offer_candidate_repository.get_candidates_by_job_offer(
            db, job_offer_id=job_offer_id
        )

        return candidates
    
    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        error_msg = f"Error retrieving candidates for job offer: {type(e).__name__}: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": error_msg}
        )

@router.put("/{candidate_id}", response_model=JobOfferCandidateDetail, 
             status_code=status.HTTP_201_CREATED,
             responses={
                 201: {"description": "Candidate linked to job offer successfully"},
                 400: {"description": "Invalid request", "model": dict},
                 404: {"description": "Resource not found", "model": dict},
                 500: {"description": "Server error", "model": dict}
             })
async def add_candidate_to_job_offer(
    job_offer_id: int,
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """
    Link an existing candidate to a job offer with fit score calculation
    """
    try:
        # Verify job offer exists
        job_offer = job_offer_repository.get(db, id=job_offer_id)
        if not job_offer:
            raise HTTPException(status_code=404, detail="Job offer not found")
        
        # Verify candidate exists
        candidate = candidate_repository.get(db, id=candidate_id)        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Check if already linked
        existing = job_offer_candidate_repository.get_by_job_offer_and_candidate(
            db, job_offer_id=job_offer_id, candidate_id=candidate_id
        )

        if existing:
            # Return existing association
            candidate_details = candidate_repository.get_with_skills(db, candidate_id=candidate_id)

            # Format skills for response
            skill_details = [
                {
                    "name": skill["skill"],
                    "expertise_level": skill["expertise_level"]
                }
                for skill in candidate_details["skills"]
            ]
            
            # Return flattened structure matching response model
            return {
                "id": existing.id,
                "name": candidate_details["name"],
                "summary": candidate_details["summary"],
                "document": candidate_details["storage_url"],
                "fit_score": existing.fit_score,
                "skills": skill_details
            }  
        
        # Get job offer with skills
        job_offer_with_skills = job_offer_repository.get_with_skills(db, job_offer_id=job_offer_id)

        # Get candidate with skills
        candidate_with_skills = candidate_repository.get_with_skills(db, candidate_id=candidate_id)

        # Check if both have skills
        if not job_offer_with_skills["skills"]:
            raise HTTPException(
                status_code=400, 
                detail={"error": "Job offer has no skills defined, cannot calculate fit score"}
            )

        if not candidate_with_skills["skills"]:
            raise HTTPException(
                status_code=400, 
                detail={"error": "Candidate has no skills defined, cannot calculate fit score"}
            )
        
        else:
            # Calculate fit score
            fit_score, cot_summary = await _calculate_fit_score(
                job_offer=job_offer_with_skills,
                candidate=candidate_with_skills
            )

        # Create job offer candidate association
        job_offer_candidate_data = {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "fit_score": fit_score, 
            "cot_summary": cot_summary
        }
        
        # Create the association in the database
        job_offer_candidate = job_offer_candidate_repository.create(db, obj_in=JobOfferCandidateCreate(**job_offer_candidate_data))

        # Format skills for response
        skill_details = [
            {
                "name": skill["skill"],
                "expertise_level": skill["expertise_level"]
            }
            for skill in candidate_with_skills["skills"]
        ]

        return {
            "id": job_offer_candidate.id,
            "name": candidate_with_skills["name"],
            "summary": candidate_with_skills["summary"],
            "document": candidate_with_skills["storage_url"],
            "fit_score": fit_score,
            "skills": skill_details
        }
    
    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        error_msg = f"Error adding candidate to job offer: {type(e).__name__}: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": error_msg}
        )

async def _calculate_fit_score(job_offer: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[float, str]:
    """
    Calculate fit score between job offer and candidate using LLM
    """
    try: 
        job_id = job_offer['id']
        candidate_id = candidate['id']
        logger.info(f"Calculating match score for job {job_id} and candidate {candidate_id}")

        # Prepare the input for langflow
        candidate_data = {
            "skills": [
                {
                    "name": skill["skill"],
                    "expertise_level": skill["expertise_level"],
                }
                for skill in candidate["skills"]
            ]
        }

        job_offer_data = {
            "skills": [
                {
                    "name": skill["skill"],
                    "priority": skill["priority"],
                    "expertise_level": skill["expertise_level"]
                } 
                for skill in job_offer["skills"]
            ]
        }

        # Create a matching flow with LangFlow
        matching_flow = langflow_client.flow(settings.LANGFLOW_JOB_OFFER_CANDIDATE_FIT_FLOW_ID,
            tweaks={
                "TextInput-FCe1H": {"input_value": json.dumps(job_offer_data)},
                "TextInput-ZLrFC": {"input_value": json.dumps(candidate_data)}
            }
        )

        # Run the flow to get match score
        logging.info(f"Calling LangFlow match flow with flow ID: {settings.LANGFLOW_JOB_OFFER_CANDIDATE_FIT_FLOW_ID}")
        fit_result = await matching_flow.run()
        result = fit_result["outputs"][0]["outputs"][0]["results"]["text"]["text"]

        # Extract match score
        try:
            fit_score_dict = ast.literal_eval(result)
            fit_score = int(fit_score_dict.get("fitScore", 0))
            cot_summary = str(fit_score_dict.get("resume", ''))
        except (ValueError, SyntaxError):
            fit_score = 0

        logging.info(f"LangFlow match result: {fit_score}")
        logging.info(f"LangFlow CoT summary result: {cot_summary}")

        return fit_score, cot_summary

    except Exception as e:
            logging.error(f"Error in fit score calculation: {type(e).__name__}: {str(e)}")
            return 0

@router.delete("/{candidate_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               responses={
                   204: {"description": "Candidate removed from job offer successfully"},
                   404: {"description": "Resource not found", "model": dict},
                   500: {"description": "Server error", "model": dict}
               })
async def remove_candidate_from_job_offer(
    job_offer_id: int = Path(..., description="ID of the job offer"),
    candidate_id: int = Path(..., description="ID of the candidate to remove"),
    db: Session = Depends(get_db)
):
    """
    Remove a candidate from a job offer by deleting the association
    """
    try:
        # Verify job offer exists
        job_offer = job_offer_repository.get(db, id=job_offer_id)
        if not job_offer:
            raise HTTPException(status_code=404, detail={"error": "Job offer not found"})
        
        # Verify candidate exists
        candidate = candidate_repository.get(db, id=candidate_id)        
        if not candidate:
            raise HTTPException(status_code=404, detail={"error": "Candidate not found"})
        
        # Check if the association exists
        association = job_offer_candidate_repository.get_by_job_offer_and_candidate(
            db, job_offer_id=job_offer_id, candidate_id=candidate_id
        )
        if not association:
            raise HTTPException(
                status_code=404, 
                detail={"error": "Candidate is not linked to this job offer"}
            )
        
        # Delete the association
        job_offer_candidate_repository.remove(db, id=association.id)
        
        return {"message": "Candidate removed from job offer successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as e:
        db.rollback()
        error_msg = f"Error removing candidate from job offer: {type(e).__name__}: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": error_msg}
        )