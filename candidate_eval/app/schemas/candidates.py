from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CandidateSkillBase(BaseModel):
    skill: str
    expertise_level: Optional[int] = None

class CandidateSkillCreate(CandidateSkillBase):
    pass

class CandidateSkill(CandidateSkillBase):
    id: int
    candidate_id: int
    
    model_config = {
        "from_attributes": True
    }

class CandidateBase(BaseModel):
    name: str
    summary: Optional[str] = None
    storage_url: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    summary: Optional[str] = None
    storage_url: Optional[str] = None

class CandidateSkillUpdate(BaseModel):
    skill: Optional[str] = None
    expertise_level: Optional[str] = None

class CandidateInDB(CandidateBase):
    id: int
    
    model_config = {
        "from_attributes": True
    }

class CandidateResponse(BaseModel):
    id: int
    name: str
    summary: Optional[str] = None
    storage_url: Optional[str] = None
    skills: List[Dict[str, Any]] = []