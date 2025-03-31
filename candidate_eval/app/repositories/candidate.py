from typing import List, Optional
from sqlalchemy.orm import Session

from db.models import Candidate
from schemas.candidates import CandidateCreate, CandidateUpdate
from repositories.base import BaseRepository

class CandidateRepository(BaseRepository[Candidate, CandidateCreate, CandidateUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[Candidate]:
        return db.query(Candidate).filter(Candidate.email == email).first()
    
    def get_by_job_offer_id(self, db: Session, *, job_offer_id: int) -> List[Candidate]:
        return db.query(Candidate).filter(Candidate.job_offer_id == job_offer_id).all()
    
    def update_cv_path(self, db: Session, *, candidate_id: int, cv_path: str) -> Candidate:
        candidate = self.get(db, id=candidate_id)
        if candidate:
            candidate.cv_path = cv_path
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
        return candidate

candidate_repository = CandidateRepository(Candidate)