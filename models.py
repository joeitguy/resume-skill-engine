from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    skills = relationship("Skill", back_populates="user")
    jobs = relationship("JobApplication", back_populates="user")

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    is_explicit = Column(Boolean, default=False)
    is_inferred = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True) 
    user = relationship("User", back_populates="skills")

class JobApplication(Base):
    __tablename__ = "job_applications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_name = Column(String, index=True, nullable=True) 
    job_title = Column(String, index=True, nullable=True)
    jd_text = Column(Text) 
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="jobs")
    requirements = relationship("JobRequirement", back_populates="job")

class JobRequirement(Base):
    __tablename__ = "job_requirements"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_applications.id"))
    name = Column(String, index=True)
    is_explicit = Column(Boolean, default=False)
    is_inferred = Column(Boolean, default=False)
    is_matched = Column(Boolean, default=False)
    matched_skill_id = Column(Integer, ForeignKey("skills.id"), nullable=True) 
    job = relationship("JobApplication", back_populates="requirements")
    matched_skill = relationship("Skill")