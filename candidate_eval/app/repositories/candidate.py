# app/repositories/candidate.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from db.models import Candidate, CandidateSkill
from schemas.candidates import CandidateCreate, CandidateUpdate
from repositories.base import BaseRepository

class CandidateRepository(BaseRepository[Candidate, CandidateCreate, CandidateUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> List[Candidate]:
        """Get candidates by name (partial match)"""
        return db.query(Candidate).filter(
            func.lower(Candidate.name).contains(func.lower(name))
        ).all()
    
    def search(self, db: Session, *, query: str, skip: int = 0, limit: int = 100) -> List[Candidate]:
        """Search candidates by name or summary"""
        return db.query(Candidate).filter(
            (Candidate.name.contains(query)) | 
            (Candidate.summary.contains(query))
        ).offset(skip).limit(limit).all()
        
    def update_storage_url(self, db: Session, *, candidate_id: int, storage_url: str) -> Optional[Candidate]:
        """Update a candidate's storage URL"""
        candidate = self.get(db, id=candidate_id)
        if candidate:
            candidate.storage_url = storage_url
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
        return candidate
    
    def get_by_job_offer_id(self, db: Session, *, job_offer_id: int) -> List[Candidate]:
        """Get candidates associated with a specific job offer"""
        return db.query(Candidate).join(Candidate.job_offers).filter(
            Candidate.job_offers.any(job_offer_id=job_offer_id)
        ).all()
    
    def get_with_skills(self, db: Session, *, candidate_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a candidate with all their skills formatted for API response
        Returns a dictionary instead of model object to handle nested skill objects
        """
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return None
            
        # Format the candidate as a dictionary
        result = {
            "id": candidate.id,
            "name": candidate.name,
            "summary": candidate.summary,
            "storage_url": candidate.storage_url,
            "skills": []
        }
        
        # Format each skill with the name extracted from the skill object
        for candidate_skill in candidate.skills:
            skill_data = {
                "skill": candidate_skill.skill.name,  # Extract name from the skill object
                "expertise_level": candidate_skill.expertise_level            
                }
            result["skills"].append(skill_data)
            
        return result

candidate_repository = CandidateRepository(Candidate)