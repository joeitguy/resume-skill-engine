import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_with_retry(system_prompt: str, contents: str, max_retries: int = 10, wait_seconds: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-flash-lite-latest',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    print(f"Gemini Server Busy (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_seconds}s...")
                    time.sleep(wait_seconds)
                    continue
            print(f"Gemini API Error after {attempt + 1} attempts: {e}")
            return None

def extract_and_infer_skills(resume_text: str) -> dict:
    system_prompt = """
    You are an expert technical recruiter and career coach ATS system.
    Analyze the provided resume text and extract a comprehensive list of skills.
    Categorize into "explicit_skills" and "inferred_skills".
    Output ONLY valid JSON: {"explicit_skills": [], "inferred_skills": []}
    """
    return generate_with_retry(system_prompt, f"Here is the resume:\n\n{resume_text}")

def extract_jd_skills(jd_text: str) -> dict:
    system_prompt = """
    You are an expert technical recruiter analyzing a job description.
    Extract the core skills into "explicit_requirements" and "inferred_requirements".
    Output ONLY valid JSON: {"explicit_requirements": [], "inferred_requirements": []}
    """
    return generate_with_retry(system_prompt, f"Here is the job description:\n\n{jd_text}")

def match_and_weight_skills(candidate_skills: list, job_requirements: dict) -> dict:
    system_prompt = """
    You are an advanced AI recruiting matchmaking engine. 
    Compare the candidate's skills to the requested job requirements.
    Score the match on a scale of 1 to 5. Only output matches of 3, 4, or 5.
    Output ONLY valid JSON:
    {"matches": [{"job_requirement": "...", "candidate_skill": "...", "score": 5, "reasoning": "..."}]}
    """
    return generate_with_retry(system_prompt, f"CANDIDATE SKILLS:\n{candidate_skills}\n\nJOB REQUIREMENTS:\n{job_requirements}")

def generate_cover_letter(resume_text: str, jd_text: str, matched_skills: list) -> dict:
    system_prompt = """
    You are an expert executive recruiter and career coach. 
    Write a professional, compelling, 3-paragraph cover letter.
    Use the provided Resume Text, Job Description, and the list of Matched Skills.
    1. Paragraph 1: Enthusiastic introduction and value proposition.
    2. Paragraph 2: Weave the Matched Skills naturally into a narrative.
    3. Paragraph 3: Strong call to action and closing.
    NEVER hallucinate metrics or skills not in the resume text.
    Output ONLY valid JSON:
    {"cover_letter": "The full text of the cover letter with \\n\\n for paragraph breaks."}
    """
    return generate_with_retry(system_prompt, f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}\n\nMATCHED SKILLS TO HIGHLIGHT:\n{matched_skills}")

def generate_resume_tailoring(matched_skills: list, all_skills: list) -> dict:
    system_prompt = """
    You are an expert resume tailor. 
    1. Write a 3-sentence 'Executive Summary' for the top of the resume highlighting the matched skills.
    2. Reorder the candidate's full skills list. Put the matched skills at the very front.
    Output ONLY valid JSON:
    {"executive_summary": "...", "ordered_skills": ["Skill1", "Skill2"]}
    """
    return generate_with_retry(system_prompt, f"MATCHED SKILLS TO HIGHLIGHT:\n{matched_skills}\n\nALL CANDIDATE SKILLS:\n{all_skills}")