# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, create_engine, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class Skill(Base):
    __tablename__ = 'skills'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(50))
    name = Column(String(255), nullable=False)
    
    job_offer_skills = relationship("JobOfferSkill", back_populates="skill")
    candidate_skills = relationship("CandidateSkill", back_populates="skill")

class JobOffer(Base):
    __tablename__ = 'job_offers'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    storage_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    skills = relationship("JobOfferSkill", back_populates="job_offer", cascade="all, delete-orphan")
    candidates = relationship("JobOfferCandidate", back_populates="job_offer", cascade="all, delete-orphan")

class JobOfferSkill(Base):
    __tablename__ = 'job_offers_skills'
    
    id = Column(Integer, primary_key=True)
    job_offer_id = Column(Integer, ForeignKey('job_offers.id', ondelete='CASCADE'))
    skill_id = Column(Integer, ForeignKey('skills.id', ondelete='CASCADE'))
    expertise_level = Column(String(50))
    priority = Column(String(50))
    
    job_offer = relationship("JobOffer", back_populates="skills")
    skill = relationship("Skill", back_populates="job_offer_skills")

class Candidate(Base):
    __tablename__ = 'candidates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    summary = Column(Text)
    storage_url = Column(String(255))
    
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    job_offers = relationship("JobOfferCandidate", back_populates="candidate", cascade="all, delete-orphan")

class CandidateSkill(Base):
    __tablename__ = 'candidate_skills'
    
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'))
    skill_id = Column(Integer, ForeignKey('skills.id', ondelete='CASCADE'))
    expertise_level = Column(String(50))
    
    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill", back_populates="candidate_skills")

class JobOfferCandidate(Base):
    __tablename__ = 'job_offer_candidates'
    
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'))
    job_offer_id = Column(Integer, ForeignKey('job_offers.id', ondelete='CASCADE'))
    fit_score = Column(Float)
    cot_summary = Column(Text)
    
    candidate = relationship("Candidate", back_populates="job_offers")
    job_offer = relationship("JobOffer", back_populates="candidates")
    