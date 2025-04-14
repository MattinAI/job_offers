# app/repositories/job_offer.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from db.models import JobOffer, JobOfferSkill
from schemas.job_offer import JobOfferCreate, JobOfferUpdate
from repositories.base import BaseRepository

class JobOfferRepository(BaseRepository[JobOffer, JobOfferCreate, JobOfferUpdate]):
    def get_by_title(self, db: Session, *, title: str) -> List[JobOffer]:
        """Get job offers by title (partial match)"""
        return db.query(JobOffer).filter(
            func.lower(JobOffer.title).contains(func.lower(title))
        ).all()
    
    def search(self, db: Session, *, query: str, skip: int = 0, limit: int = 100) -> List[JobOffer]:
        """Search job offers by title or summary"""
        return db.query(JobOffer).filter(
            (JobOffer.title.contains(query)) | 
            (JobOffer.summary.contains(query))
        ).offset(skip).limit(limit).all()
        
    def update_storage_url(self, db: Session, *, job_offer_id: int, storage_url: str) -> Optional[JobOffer]:
        """Update a job offer's storage URL"""
        job_offer = self.get(db, id=job_offer_id)
        if job_offer:
            job_offer.storage_url = storage_url
            db.add(job_offer)
            db.commit()
            db.refresh(job_offer)
        return job_offer
            
    def get_with_skills(self, db: Session, *, job_offer_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a job offer with all its skills formatted for API response
        Returns a dictionary instead of model object to handle nested skill objects
        """
        job_offer = db.query(JobOffer).filter(JobOffer.id == job_offer_id).first()
        if not job_offer:
            return None
            
        # Format the job offer as a dictionary
        result = {
            "id": job_offer.id,
            "title": job_offer.title,
            "summary": job_offer.summary,
            "storage_url": job_offer.storage_url,
            "created_at": job_offer.created_at,
            "updated_at": job_offer.updated_at,
            "skills": []
        }
        
        # Format each skill with the name extracted from the skill object
        for job_offer_skill in job_offer.skills:
            skill_data = {
                "id": job_offer_skill.id,
                "skill": job_offer_skill.skill.name,  # Extract name from the skill object
                "expertise_level": job_offer_skill.expertise_level,
                "priority": job_offer_skill.priority,
                "job_offer_id": job_offer_skill.job_offer_id
            }
            result["skills"].append(skill_data)
            
        return result

job_offer_repository = JobOfferRepository(JobOffer)