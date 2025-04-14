# app/schemas/job_offer_skill.py
from typing import Optional
from pydantic import BaseModel

# Shared properties
class JobOfferSkillBase(BaseModel):
    job_offer_id: int
    skill_id: int
    expertise_level: Optional[str] = None
    priority: Optional[str] = None

# Properties to receive on job offer skill creation
class JobOfferSkillCreate(JobOfferSkillBase):
    pass

# Properties to receive on job offer skill update
class JobOfferSkillUpdate(JobOfferSkillBase):
    job_offer_id: Optional[int] = None

# Properties shared by models stored in DB
class JobOfferSkillInDBBase(JobOfferSkillBase):
    id: int

    class Config:
        orm_mode = True

# Properties to return to client
class JobOfferSkill(JobOfferSkillInDBBase):
    pass

# Properties stored in DB
class JobOfferSkillInDB(JobOfferSkillInDBBase):
    pass