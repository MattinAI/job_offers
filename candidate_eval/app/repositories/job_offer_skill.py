# app/repositories/job_offer_skill.py
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from db.models import JobOfferSkill
from schemas.job_offer_skill import JobOfferSkillCreate, JobOfferSkillUpdate
from repositories.base import BaseRepository
from repositories.skill import skill_repository

class JobOfferSkillRepository(BaseRepository[JobOfferSkill, JobOfferSkillCreate, JobOfferSkillUpdate]):
    def create_with_skill_name(
        self, 
        db: Session, 
        *, 
        job_offer_id: int, 
        skill_name: str,
        expertise_level: Optional[str] = None,
        priority: Optional[str] = None,
        skill_type: str = "job_offer"
    ) -> JobOfferSkill:
        """Create job offer skill with skill name, creating the skill if it doesn't exist"""
        # Get or create the skill
        skill = skill_repository.get_or_create(db, name=skill_name, type=skill_type)
        
        # Create job offer skill
        job_offer_skill_data = {
            "job_offer_id": job_offer_id,
            "skill_id": skill.id
        }
        
        if expertise_level:
            job_offer_skill_data["expertise_level"] = expertise_level
            
        if priority:
            job_offer_skill_data["priority"] = priority
            
        return self.create(db, obj_in=JobOfferSkillCreate(**job_offer_skill_data))
    
    def bulk_create(
        self, 
        db: Session, 
        *, 
        job_offer_id: int, 
        skills: List[Dict[str, Any]],
        skill_type: str = "job_offer"
    ) -> List[JobOfferSkill]:
        """Bulk create job offer skills from a list of skill dictionaries"""
        result = []
        
        for skill_data in skills:
            job_offer_skill = self.create_with_skill_name(
                db,
                job_offer_id=job_offer_id,
                skill_name=skill_data["skill"],
                expertise_level=skill_data.get("expertise_level"),
                priority=skill_data.get("priority"),
                skill_type=skill_type
            )
            result.append(job_offer_skill)

        return result
    
    def get_by_job_offer(self, db: Session, *, job_offer_id: int) -> List[JobOfferSkill]:
        """Get all skills for a job offer"""
        return db.query(JobOfferSkill).filter(JobOfferSkill.job_offer_id == job_offer_id).all()

job_offer_skill_repository = JobOfferSkillRepository(JobOfferSkill)