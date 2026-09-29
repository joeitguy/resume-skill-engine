import re
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
import models
from database import engine, get_db
from llm_service import (
    extract_and_infer_skills, 
    extract_jd_skills, 
    match_and_weight_skills,
    generate_cover_letter,
    generate_resume_tailoring
)

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Resume Skill Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_raw_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
    text = text.replace('–', '-').replace('—', '-')
    text = text.replace('\xa0', ' ').replace('\u200b', '').replace('\t', ' ')
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

class ResumeUpload(BaseModel):
    user_id: int
    resume_text: str
    @field_validator('resume_text')
    @classmethod
    def sanitize_resume(cls, v: str) -> str:
        return clean_raw_text(v)

class MatchRequest(BaseModel):
    user_id: int
    jd_text: str
    @field_validator('jd_text')
    @classmethod
    def sanitize_match_jd(cls, v: str) -> str:
        return clean_raw_text(v)

class DocumentGeneratorRequest(BaseModel):
    resume_text: str
    jd_text: str
    matched_skills: List[str]
    all_skills: List[str]
    @field_validator('resume_text', 'jd_text')
    @classmethod
    def sanitize_texts(cls, v: str) -> str:
        return clean_raw_text(v)

@app.post("/api/resume/ingest")
def ingest_resume(data: ResumeUpload, db: Session = Depends(get_db)):
    ai_skills = extract_and_infer_skills(data.resume_text)
    if not ai_skills:
        raise HTTPException(status_code=503, detail="AI service is busy. Try again.")
    new_skills = []
    for skill_name in ai_skills.get("explicit_skills", []):
        db_skill = models.Skill(user_id=data.user_id, name=skill_name, is_explicit=True, is_inferred=False, is_verified=False)
        db.add(db_skill)
        new_skills.append(db_skill)
    for skill_name in ai_skills.get("inferred_skills", []):
        db_skill = models.Skill(user_id=data.user_id, name=skill_name, is_explicit=False, is_inferred=True, is_verified=False)
        db.add(db_skill)
        new_skills.append(db_skill)
    db.commit()
    return {"message": f"Successfully ingested {len(new_skills)} skills.", "skills_found": ai_skills}

@app.post("/api/jobs/match")
def analyze_and_match_job(data: MatchRequest, db: Session = Depends(get_db)):
    jd_requirements = extract_jd_skills(data.jd_text)
    if not jd_requirements:
        raise HTTPException(status_code=503, detail="AI service busy (Job Extraction failed).")
    user_skills_db = db.query(models.Skill).filter(models.Skill.user_id == data.user_id).all()
    candidate_skills_list = [skill.name for skill in user_skills_db]
    match_results = match_and_weight_skills(candidate_skills_list, jd_requirements)
    if not match_results:
        raise HTTPException(status_code=503, detail="AI service busy (Matching failed).")
    return {
        "message": "Job successfully analyzed and matched!",
        "job_requirements": jd_requirements,
        "matches": match_results.get("matches", [])
    }

@app.post("/api/documents/generate")
def generate_application_documents(data: DocumentGeneratorRequest):
    cover_letter_data = generate_cover_letter(data.resume_text, data.jd_text, data.matched_skills)
    if not cover_letter_data:
        raise HTTPException(status_code=503, detail="AI Service busy (Cover Letter). Please try again.")
    resume_data = generate_resume_tailoring(data.matched_skills, data.all_skills)
    if not resume_data:
        raise HTTPException(status_code=503, detail="AI Service busy (Resume Tailoring). Please try again.")
    return {
        "message": "Documents generated successfully!",
        "cover_letter": cover_letter_data.get("cover_letter", ""),
        "executive_summary": resume_data.get("executive_summary", ""),
        "ordered_skills": resume_data.get("ordered_skills", [])
    }