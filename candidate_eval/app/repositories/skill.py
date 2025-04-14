# app/repositories/skill.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import Skill
from schemas.skill import SkillCreate, SkillUpdate
from repositories.base import BaseRepository

class SkillRepository(BaseRepository[Skill, SkillCreate, SkillUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Skill]:
        """Get skill by exact name match"""
        return db.query(Skill).filter(func.lower(Skill.name) == func.lower(name)).first()
    
    def get_or_create(self, db: Session, *, name: str, type: str = None) -> Skill:
        """Get an existing skill or create a new one if it doesn't exist"""
        skill = self.get_by_name(db, name=name)
        if not skill:
            skill_data = {"name": name}
            if type:
    
                skill_data["type"] = type
            skill = self.create(db, obj_in=SkillCreate(**skill_data))
        return skill

skill_repository = SkillRepository(Skill)