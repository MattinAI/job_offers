from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CandidateBase(BaseModel):
    name: str
    summary: Optional[str] = None
    storage_url: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    job_offer_id: Optional[int] = None
    cv_path: Optional[str] = None

class CandidateInDB(CandidateBase):
    id: int
    cv_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True