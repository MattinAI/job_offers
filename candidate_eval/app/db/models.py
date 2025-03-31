# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, create_engine, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class JobOffer(Base):
    __tablename__ = 'job_offers'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    storage_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    skills = relationship("JobOfferSkill", back_populates="job_offer")
    candidates = relationship("JobOfferCandidate", back_populates="job_offer")

class JobOfferSkill(Base):
    __tablename__ = 'job_offers_skills'
    
    id = Column(Integer, primary_key=True)
    job_offer_id = Column(Integer, ForeignKey('job_offers.id', ondelete='CASCADE'))
    skill = Column(String(255), nullable=False)
    expertise_level = Column(String(50))
    priority = Column(String(50))
    
    job_offer = relationship("JobOffer", back_populates="skills")

class Candidate(Base):
    __tablename__ = 'candidates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    summary = Column(Text)
    storage_url = Column(String(255))
    
    skills = relationship("CandidateSkill", back_populates="candidate")
    job_offers = relationship("JobOfferCandidate", back_populates="candidate")

class CandidateSkill(Base):
    __tablename__ = 'candidate_skills'
    
    id = Column(Integer, primary_key=True)
    job_candidate_id = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'))
    type = Column(String(50))
    name = Column(String(255), nullable=False)
    expertise_level = Column(String(50))
    
    candidate = relationship("Candidate", back_populates="skills")

class JobOfferCandidate(Base):
    __tablename__ = 'job_offer_candidates'
    
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'))
    job_offer_id = Column(Integer, ForeignKey('job_offers.id', ondelete='CASCADE'))
    fit_score = Column(Float)
    
    candidate = relationship("Candidate", back_populates="job_offers")
    job_offer = relationship("JobOffer", back_populates="candidates")
    