# app/repositories/job_offer_skill.py
from typing import List
from sqlalchemy.orm import Session

from db.models import JobOfferSkill
from schemas.job_offer import JobOfferSkillCreate, JobOfferSkillUpdate
from repositories.base import BaseRepository

class JobOfferSkillRepository(BaseRepository[JobOfferSkill, JobOfferSkillCreate, JobOfferSkillUpdate]):
    def get_by_job_offer(self, db: Session, *, job_offer_id: int) -> List[JobOfferSkill]:
        """Get all skills for a specific job offer"""
        return db.query(JobOfferSkill).filter(JobOfferSkill.job_offer_id == job_offer_id).all()
    
    def get_by_skill(self, db: Session, *, skill: str) -> List[JobOfferSkill]:
        """Get all job offers that require a specific skill"""
        return db.query(JobOfferSkill).filter(JobOfferSkill.skill == skill).all()
    
    def bulk_create(self, db: Session, *, job_offer_id: int, skills: List[dict]) -> List[JobOfferSkill]:
        """Create multiple skills for a job offer in one operation"""
        db_skills = []
        for skill_data in skills:
            db_skill = JobOfferSkill(
                job_offer_id=job_offer_id,
                skill=str(skill_data["skill"]),
                expertise_level=str(skill_data["expertise_level"]),
                priority=str(skill_data["priority"])
            )
            db.add(db_skill)
            db_skills.append(db_skill)
        
        db.commit()
        for skill in db_skills:
            db.refresh(skill)
        
        return db_skills

job_offer_skill_repository = JobOfferSkillRepository(JobOfferSkill)