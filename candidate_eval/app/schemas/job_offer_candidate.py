# app/schemas/job_offer_candidate.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Shared properties
class JobOfferCandidateBase(BaseModel):
    candidate_id: int
    job_offer_id: int
    fit_score: int
    cot_summary: str

# Properties to receive on creation
class JobOfferCandidateCreate(JobOfferCandidateBase):
    pass

# Properties to receive on update
class JobOfferCandidateUpdate(BaseModel):
    fit_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)

# Properties to return to client
class JobOfferCandidateDetail(BaseModel):
    id: int
    name: str
    summary: str
    document: str
    fit_score: float
    skills: List[Dict[str, str]]

    model_config = {
        "from_attributes": True
    }

# Database
class JobOfferCandidateInDB(JobOfferCandidateBase):
    id: int

    class Config:
        orm_mode = True