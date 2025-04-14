# app/repositories/candidate_skill.py
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from db.models import CandidateSkill
from schemas.candidate_skill import CandidateSkillCreate, CandidateSkillUpdate
from repositories.base import BaseRepository
from repositories.skill import skill_repository

class CandidateSkillRepository(BaseRepository[CandidateSkill, CandidateSkillCreate, CandidateSkillUpdate]):
    def create_with_skill_name(
        self, 
        db: Session, 
        *, 
        candidate_id: int, 
        skill_name: str,
        expertise_level: Optional[str] = None,
        skill_type: str = "candidate"
    ) -> CandidateSkill:
        """Create job offer skill with skill name, creating the skill if it doesn't exist"""
        # Get or create the skill
        skill = skill_repository.get_or_create(db, name=skill_name, type=skill_type)
        
        # Create job offer skill
        job_offer_skill_data = {
            "candidate_id": candidate_id,
            "skill_id": skill.id
        }
        
        if expertise_level:
            job_offer_skill_data["expertise_level"] = expertise_level
            
        return self.create(db, obj_in=CandidateSkillCreate(**job_offer_skill_data))
    
    def bulk_create(
        self, 
        db: Session, 
        *, 
        candidate_id: int, 
        skills: List[Dict[str, Any]],
        skill_type: str = "candidate"
    ) -> List[CandidateSkill]:
        """Bulk create job offer skills from a list of skill dictionaries"""
        result = []
        
        for skill_data in skills:
            candidate_skill = self.create_with_skill_name(
                db,
                candidate_id=candidate_id,
                skill_name=skill_data["skill"],
                expertise_level=skill_data.get("expertise_level"),
                skill_type=skill_type
            )
            result.append(candidate_skill)

        return result
    
    def get_by_job_offer(self, db: Session, *, candidate_id: int) -> List[CandidateSkill]:
        """Get all skills for a job offer"""
        return db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).all()

candidate_skill_repository = CandidateSkillRepository(CandidateSkill)