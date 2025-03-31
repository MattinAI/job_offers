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
    
    def get_recent(self, db: Session, *, limit: int = 10) -> List[JobOffer]:
        """Get the most recently created job offers"""
        return db.query(JobOffer).order_by(desc(JobOffer.created_at)).limit(limit).all()
    
    def search(self, db: Session, *, query: str, skip: int = 0, limit: int = 100) -> List[JobOffer]:
        """Search job offers by title or summary"""
        return db.query(JobOffer).filter(
            (JobOffer.title.contains(query)) | 
            (JobOffer.summary.contains(query))
        ).offset(skip).limit(limit).all()
    
    def get_stats(self, db: Session) -> Dict[str, Any]:
        """Get statistics about job offers"""
        total = db.query(JobOffer).count()
        return {
            "total": total
        }
        
    def update_storage_url(self, db: Session, *, job_offer_id: int, storage_url: str) -> Optional[JobOffer]:
        """Update a job offer's storage URL"""
        job_offer = self.get(db, id=job_offer_id)
        if job_offer:
            job_offer.storage_url = storage_url
            db.add(job_offer)
            db.commit()
            db.refresh(job_offer)
        return job_offer
        
    def add_skill(self, db: Session, *, job_offer_id: int, skill: str) -> JobOfferSkill:
        """Add a skill to a job offer"""
        job_offer_skill = JobOfferSkill(job_offer_id=job_offer_id, skill=skill)
        db.add(job_offer_skill)
        db.commit()
        db.refresh(job_offer_skill)
        return job_offer_skill
        
    def remove_skill(self, db: Session, *, skill_id: int) -> None:
        """Remove a skill from a job offer"""
        skill = db.query(JobOfferSkill).filter(JobOfferSkill.id == skill_id).first()
        if skill:
            db.delete(skill)
            db.commit()
            
    def get_with_skills(self, db: Session, *, job_offer_id: int) -> Optional[JobOffer]:
        """Get a job offer with all its skills"""
        return db.query(JobOffer).filter(JobOffer.id == job_offer_id).first()

job_offer_repository = JobOfferRepository(JobOffer)