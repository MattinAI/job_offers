# app/repositories/job_offer_candidate.py
from typing import List, Optional
from sqlalchemy.orm import Session

from db.models import JobOfferCandidate, Skill, CandidateSkill
from schemas.job_offer_candidate import JobOfferCandidateCreate, JobOfferCandidateUpdate, JobOfferCandidateDetail
from repositories.base import BaseRepository

class JobOfferCandidateRepository(BaseRepository[JobOfferCandidate, JobOfferCandidateCreate, JobOfferCandidateUpdate]):
    def get_by_job_offer(self, db: Session, *, job_offer_id: int) -> List[JobOfferCandidate]:
        """Get all candidates for a job offer"""
        return db.query(JobOfferCandidate).filter(JobOfferCandidate.job_offer_id == job_offer_id).all()
    
    def get_by_candidate(self, db: Session, *, candidate_id: int) -> List[JobOfferCandidate]:
        """Get all job offers for a candidate"""
        return db.query(JobOfferCandidate).filter(JobOfferCandidate.candidate_id == candidate_id).all()
    
    def get_by_job_offer_and_candidate(
        self, db: Session, *, job_offer_id: int, candidate_id: int
    ) -> Optional[JobOfferCandidate]:
        """Get a job offer candidate by job offer and candidate IDs"""
        return db.query(JobOfferCandidate).filter(
            JobOfferCandidate.job_offer_id == job_offer_id,
            JobOfferCandidate.candidate_id == candidate_id
        ).first()
    
    def get_candidates_by_job_offer(
    self, db: Session, *, job_offer_id: int
) -> JobOfferCandidateDetail:
        """Get all candidates for a job offer ordered by descending fit score"""
        job_offer_candidates = db.query(JobOfferCandidate).filter(
            JobOfferCandidate.job_offer_id == job_offer_id
        ).order_by(JobOfferCandidate.fit_score.desc()).all()

        result = []
        for joc in job_offer_candidates:
            # Get candidate's skills with their expertise levels
            candidate_skills = db.query(
                CandidateSkill, Skill
            ).join(
                Skill, CandidateSkill.skill_id == Skill.id
            ).filter(
                CandidateSkill.candidate_id == joc.candidate_id
            ).all()
            
            skills_list = [
                {
                    "name": skill[1].name,
                    "expertise_level": skill[0].expertise_level
                }
                for skill in candidate_skills
            ]
            
            result.append({
                "id": joc.id,
                "name": joc.candidate.name,
                "summary": joc.candidate.summary,
                "document": joc.candidate.storage_url,  # Using storage_url as document
                "fit_score": joc.fit_score,
                "skills": skills_list
            })
        
        return result
    
job_offer_candidate_repository = JobOfferCandidateRepository(JobOfferCandidate)
