from typing import List, Dict, Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.db.models import User
from app.schemas.candidate import JobOfferCandidateCreate, JobOfferCandidateDetail, CandidateCreate
from app.repositories.candidate import job_offer_candidate_repository, candidate_repository
from app.repositories.job_offer import job_offer_repository
from app.services.storage import storage_service
from app.services.document import document_processor
from app.services.matching import matching_service

router = APIRouter(prefix="/job-offers/{job_offer_id}/candidates", tags=["Job Offer Candidates"])


@router.get("/", response_model=List[JobOfferCandidateDetail])
async def get_job_offer_candidates(
    job_offer_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all candidates for a job offer ordered by fit score
    """
    # Verify job offer exists
    job_offer = job_offer_repository.get(db=db, id=job_offer_id)
    if not job_offer:
        raise HTTPException(status_code=404, detail="Job offer not found")
    
    # Get candidates
    return job_offer_candidate_repository.get_candidates_by_job_offer(
        db=db, job_offer_id=job_offer_id, skip=skip, limit=limit
    )


@router.post("/", response_model=JobOfferCandidateDetail, status_code=status.HTTP_201_CREATED)
async def add_candidate_to_job_offer(
    job_offer_id: int,
    name: str = Form(...),
    document: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Add a new candidate to a job offer
    """
    # Verify job offer exists
    job_offer = job_offer_repository.get(db=db, id=job_offer_id)
    if not job_offer:
        raise HTTPException(status_code=404, detail="Job offer not found")
    
    # Upload document to storage
    storage_path = await storage_service.upload_file(document, "candidates")
    
    # Extract document content
    file_content, content_type = await storage_service.get_file(storage_path)
    text = document_processor.extract_text(file_content, content_type)
    
    # Extract skills and generate summary
    skills = document_processor.extract_skills(text)
    summary = document_processor.generate_summary(text)
    
    # Create candidate
    candidate_in = CandidateCreate(
        name=name,
        summary=summary,
        skills=[{
            "name": skill["name"],
            "type": "technical" if skill["name"] in document_processor.common_skills else "soft",
            "expertise_level": skill["level"],
            "years_experience": skill["years_experience"]
        } for skill in skills]
    )
    
    candidate = candidate_repository.create_with_skills(
        db=db, 
        obj_in=candidate_in,
        storage_url=storage_path
    )
    
    # Calculate match score
    fit_score = await matching_service.match_candidate_to_job(
        db=db, job_offer_id=job_offer_id, candidate_id=candidate.id
    )
    
    # Link candidate to job offer
    job_offer_candidate_in = JobOfferCandidateCreate(
        job_offer_id=job_offer_id,
        candidate_id=candidate.id,
        fit_score=fit_score
    )
    
    job_offer_candidate = job_offer_candidate_repository.create(
        db=db, obj_in=job_offer_candidate_in
    )
    
    # Return full detail
    result = db.query(JobOfferCandidateDetail).filter(
        JobOfferCandidateDetail.id == job_offer_candidate.id
    ).first()
    
    return result


@router.put("/{candidate_id}", response_model=JobOfferCandidateDetail)
async def link_candidate_to_job_offer(
    job_offer_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Link an existing candidate to a job offer
    """
    # Verify job offer exists
    job_offer = job_offer_repository.get(db=db, id=job_offer_id)
    if not job_offer:
        raise HTTPException(status_code=404, detail="Job offer not found")
    
    # Verify candidate exists
    candidate = candidate_repository.get(db=db, id=candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check if already linked
    existing = (
        db.query(JobOfferCandidateDetail)
        .filter(
            JobOfferCandidateDetail.job_offer_id == job_offer_id,
            JobOfferCandidateDetail.candidate_id == candidate_id
        )
        .first()
    )
    
    if existing:
        # Recalculate match score
        fit_score = await matching_service.match_candidate_to_job(
            db=db, job_offer_id=job_offer_id, candidate_id=candidate_id
        )
        
        # Update score if changed
        if existing.fit_score != fit_score:
            existing.fit_score = fit_score
            db.add(existing)
            db.commit()
            db.refresh(existing)
            
        return existing
    
    # Calculate match score
    fit_score = await matching_service.match_candidate_to_job(
        db=db, job_offer_id=job_offer_id, candidate_id=candidate_id
    )
    
    # Link candidate to job offer
    job_offer_candidate_in = JobOfferCandidateCreate(
        job_offer_id=job_offer_id,
        candidate_id=candidate_id,
        fit_score=fit_score
    )
    
    job_offer_candidate = job_offer_candidate_repository.create(
        db=db, obj_in=job_offer_candidate_in
    )
    
    # Return full detail
    result = (
        db.query(JobOfferCandidateDetail)
        .filter(JobOfferCandidateDetail.id == job_offer_candidate.id)
        .first()
    )
    
    return result


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_candidate_from_job_offer(
    job_offer_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Remove a candidate from a job offer
    """
    # Verify job offer exists
    job_offer = job_offer_repository.get(db=db, id=job_offer_id)
    if not job_offer:
        raise HTTPException(status_code=404, detail="Job offer not found")
    
    # Verify candidate exists
    candidate = candidate_repository.get(db=db, id=candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Remove the link
    job_offer_candidate_repository.remove_candidate_from_job_offer(
        db=db, job_offer_id=job_offer_id, candidate_id=candidate_id
    )
    
    return None