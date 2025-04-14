# app/schemas/candidate_skill.py
from typing import Optional
from pydantic import BaseModel

# Shared properties
class CandidateSkillBase(BaseModel):
    candidate_id: int
    skill_id: int
    expertise_level: Optional[str] = None

# Properties to receive on candidate skill creation
class CandidateSkillCreate(CandidateSkillBase):
    pass

# Properties to receive on candidate skill update
class CandidateSkillUpdate(BaseModel):
    expertise_level: Optional[str] = None

# Properties shared by models stored in DB
class CandidateSkillInDBBase(CandidateSkillBase):
    id: int

    model_config = {
        "from_attributes": True
    }

# Properties to return to client
class CandidateSkill(CandidateSkillInDBBase):
    pass

# Properties stored in DB
class CandidateSkillInDB(CandidateSkillInDBBase):
    pass