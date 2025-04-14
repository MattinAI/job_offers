# app/schemas/skill.py
from typing import Optional
from pydantic import BaseModel

# Shared properties
class SkillBase(BaseModel):
    name: str
    type: Optional[str] = None

# Properties to receive on skill creation
class SkillCreate(SkillBase):
    pass

# Properties to receive on skill update
class SkillUpdate(SkillBase):
    name: Optional[str] = None

# Properties shared by models stored in DB
class SkillInDBBase(SkillBase):
    id: int

    class Config:
        orm_mode = True

# Properties to return to client
class Skill(SkillInDBBase):
    pass

# Properties stored in DB
class SkillInDB(SkillInDBBase):
    pass