from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobOfferSkillBase(BaseModel):
    skill: str
    expertise_level: Optional[int] = None
    priority: Optional[str] = None

class JobOfferSkillCreate(JobOfferSkillBase):
    pass

class JobOfferSkill(JobOfferSkillBase):
    id: int
    job_offer_id: int
    
    model_config = {
        "from_attributes": True
    }

class JobOfferBase(BaseModel):
    title: str
    summary: Optional[str] = None
    storage_url: Optional[str] = None

class JobOfferCreate(JobOfferBase):
    pass

class JobOfferUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    storage_url: Optional[str] = None

class JobOfferSkillUpdate(BaseModel):
    skill: Optional[str] = None
    expertise_level: Optional[str] = None
    priority: Optional[str] = None

class JobOfferInDB(JobOfferBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

class JobOfferResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    storage_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    skills: List[Dict[str, Any]] = []