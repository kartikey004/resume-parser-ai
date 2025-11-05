import time
import os
import uuid
import json
from celery import Celery, chain
import google.generativeai as genai  
from .database import SessionLocal
from . import crud, models
from .core.parser import extract_text_from_file
from .ai_schemas import (
    AIParsedData, MatchResponse, JobDescription, BiasReport, SalaryEstimate,
    CareerProgression
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)
celery_app.conf.update(task_track_started=True)

try:
    if not GOOGLE_API_KEY:
        print("WARNING: GOOGLE_API_KEY is not set in .env. AI tasks will fail.")
        genai_client = None
    else:
        genai.configure(api_key=GOOGLE_API_KEY)
        genai_client = True 
        print("Google Gemini client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Google Gemini client: {e}")
    genai_client = None


@celery_app.task(name="extract_structured_data_task")
def extract_structured_data_task(resume_id: str):
    """
    Task 2: Takes a resume_id, gets its raw_text, calls the Gemini AI for
    all enhancements, and saves it to the database.
    """
    print(f"Starting AI data extraction for resume_id: {resume_id}")
    db = SessionLocal()
    resume_uuid = uuid.UUID(resume_id)
    
    try:
        resume = db.get(models.Resume, resume_uuid)
        if not resume:
            print(f"AI Task {resume_id}: Resume not found. Aborting.")
            return
        
        if not resume.raw_text:
            print(f"AI Task {resume_id}: Resume has no raw_text. Marking as 'parse_failed'.")
            crud.update_resume_status(db, resume.id, "parse_failed")
            return
        
        if not genai_client:
            raise Exception("Google Gemini client not initialized. Check GOOGLE_API_KEY.")

        ai_schema = AIParsedData.model_json_schema()

        prompt = f"""
        You are an expert resume parser. Your job is to extract information from the
        provided resume text and format it *perfectly* as a JSON object.
        You must adhere strictly to the provided JSON schema. Do not add any extra
        text or explanations outside of the JSON structure.

        Here is the JSON schema you *must* follow:
        {json.dumps(ai_schema)}

        Here is the resume text to parse:
        ---
        {resume.raw_text}
        ---
        """

        print(f"AI Task {resume_id}: Calling Gemini API (model:gemini-2.5-flash) for PARSING...")
        
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = model.generate_content(prompt)
        ai_response_str = response.text.strip().lstrip("```json").rstrip("```")

        print(f"AI Task {resume_id}: AI parsing response received. Validating...")
        
        ai_data_dict = json.loads(ai_response_str)
        validated_data = AIParsedData.model_validate(ai_data_dict)
        save_data_dict = validated_data.model_dump(by_alias=True)
        
        try:
            print(f"AI Task {resume_id}: Calling Gemini API (model:gemini-2.5-flash) for BIAS DETECTION...")
            bias_schema = BiasReport.model_json_schema()
            
            bias_prompt = f"""
            You are an expert, unbiased HR screening assistant. Your job is to analyze
            the provided resume text *only* for potential hiring biases.
            Look for language related to:
            - Gender (e.g., pronouns, names that strongly imply gender)
            - Age (e.g., graduation dates far in the past, age-related terms)
            - Ethnicity or National Origin (e.g., names, locations)
            - Marital or Family Status

            Return your findings *only* as a JSON object adhering to this schema:
            {json.dumps(bias_schema)}
            
            If no biases are found, return:
            {{"biasDetected": false, "findings": []}}

            Here is the resume text to analyze:
            ---
            {resume.raw_text}
            ---
            """
            
            bias_response = model.generate_content(bias_prompt)
            bias_response_str = bias_response.text.strip().lstrip("```json").rstrip("```")
            
            print(f"AI Task {resume_id}: Bias report received. Validating...")
            bias_data_dict = json.loads(bias_response_str)
            validated_bias_report = BiasReport.model_validate(bias_data_dict)
            
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["biasReport"] = validated_bias_report.model_dump(by_alias=True)
            
            print(f"AI Task {resume_id}: Bias report successfully merged.")

        except Exception as bias_e:
            print(f"AI Task {resume_id}: WARNING: Bias detection call failed: {bias_e}. Proceeding without bias report.")
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["biasReport"] = None
        
        anonymized_data_dict = {} 
        try:
            print(f"AI Task {resume_id}: Calling Gemini API (model:gemini-2.5-flash) for ANONYMIZATION...")
            
            anonymize_prompt = f"""
            You are an expert data anonymizer. Your job is to take the provided
            JSON object and remove all Personally Identifiable Information (PII).
            
            You must redact the following fields by replacing them with "[REDACTED]":
            - All fields within 'personalInfo.name' (first, last, full)
            - All fields within 'personalInfo.contact' (email, phone, address, linkedin, website)
            
            Return the *entire*, *original* JSON structure, but with only those
            specific fields redacted.
            
            Here is the JSON schema to follow (the same as the input):
            {json.dumps(ai_schema)}

            Here is the JSON object to anonymize:
            ---
            {json.dumps(save_data_dict)}
            ---
            """
            
            anonymize_response = model.generate_content(anonymize_prompt)
            anonymize_response_str = anonymize_response.text.strip().lstrip("```json").rstrip("```")

            print(f"AI Task {resume_id}: Anonymized JSON received.")
            anonymized_data_dict = json.loads(anonymize_response_str) 
            
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["anonymizedData"] = anonymized_data_dict

            print(f"AI Task {resume_id}: Anonymized data successfully merged.")
            
        except Exception as anon_e:
            print(f"AI Task {resume_id}: WARNING: Anonymization call failed: {anon_e}. Proceeding without anonymized data.")
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["anonymizedData"] = None
            anonymized_data_dict = save_data_dict 
        
        try:
            print(f"AI Task {resume_id}: Calling Gemini API (model:gemini-2.5-flash) for SALARY ESTIMATION...")
            salary_schema = SalaryEstimate.model_json_schema()
            
            data_for_salary_call = anonymized_data_dict if anonymized_data_dict else save_data_dict

            salary_prompt = f"""
            You are an expert financial analyst and HR compensation specialist.
            Your job is to provide a salary estimation for the candidate based
            on their parsed resume data.
            
            Consider their:
            - Experience level (e.g., {data_for_salary_call.get("summary", {}).get("careerLevel")})
            - Industry (e.g., {data_for_salary_call.get("summary", {}).get("industryFocus")})
            - Location (e.g., {data_for_salary_call.get("personalInfo", {}).get("contact", {}).get("address", {}).get("country")})
            - Key skills
            
            Return your estimation *only* as a JSON object adhering to this schema:
            {json.dumps(salary_schema)}
            
            Use the currency appropriate for the candidate's location (e.g., INR, USD, EUR).
            If location is [REDACTED], default to USD.
            Provide brief comments explaining your reasoning.

            Here is the parsed (and anonymized) resume data:
            ---
            {json.dumps(data_for_salary_call)}
            ---
            """
            
            salary_response = model.generate_content(salary_prompt)
            salary_response_str = salary_response.text.strip().lstrip("```json").rstrip("```")
            
            print(f"AI Task {resume_id}: Salary estimation received. Validating...")
            salary_data_dict = json.loads(salary_response_str)
            validated_salary_report = SalaryEstimate.model_validate(salary_data_dict)
            
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["salaryEstimate"] = validated_salary_report.model_dump(by_alias=True)
            
            print(f"AI Task {resume_id}: Salary estimation successfully merged.")

        except Exception as salary_e:
            print(f"AI Task {resume_id}: WARNING: Salary estimation call failed: {salary_e}. Proceeding without estimation.")
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["salaryEstimate"] = None
        
        try:
            print(f"AI Task {resume_id}: Calling Gemini API (model:gemini-2.5-flash) for CAREER PROGRESSION...")
            career_schema = CareerProgression.model_json_schema()
            
            data_for_career_call = anonymized_data_dict if anonymized_data_dict else save_data_dict

            career_prompt = f"""
            You are an expert career coach and industry analyst.
            Your job is to analyze the provided parsed resume and suggest
            a future career path.
            
            Based on the candidate's experience, skills, and industry, provide:
            1. A list of 3-5 realistic 'next-step' job titles.
            2. A list of 2-3 key skills or technologies they should learn to advance.
            3. A brief comment explaining your reasoning.
            
            Return your analysis *only* as a JSON object adhering to this schema:
            {json.dumps(career_schema)}
            
            Here is the parsed (and anonymized) resume data:
            ---
            {json.dumps(data_for_career_call)}
            ---
            """
            
            career_response = model.generate_content(career_prompt)
            career_response_str = career_response.text.strip().lstrip("```json").rstrip("```")
            
            print(f"AI Task {resume_id}: Career progression received. Validating...")
            career_data_dict = json.loads(career_response_str)
            validated_career_report = CareerProgression.model_validate(career_data_dict)
            
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["careerProgression"] = validated_career_report.model_dump(by_alias=True)
            
            print(f"AI Task {resume_id}: Career progression successfully merged.")

        except Exception as career_e:
            print(f"AI Task {resume_id}: WARNING: Career progression call failed: {career_e}. Proceeding without this data.")
            if save_data_dict.get("aiEnhancements") is None:
                save_data_dict["aiEnhancements"] = {}
            save_data_dict["aiEnhancements"]["careerProgression"] = None
       
        crud.update_resume_structured_data(
            db=db,
            resume_id=resume.id,
            data=save_data_dict
        )
        print(f"AI Task {resume_id}: Successfully saved all structured data. Status: completed.")

    except Exception as e:
        print(f"AI Task {resume_id}: FAILED. Error: {e}")
        try:
            crud.update_resume_status(db, resume_uuid, "ai_failed")
        except Exception as db_e:
            print(f"AI Task {resume_id}: FAILED to even update status. Error: {db_e}")
    finally:
        db.close()
    
    return f"AI Task {resume_id} finished."



@celery_app.task(name="process_resume_task")
def process_resume_task(resume_id: str, file_path: str, content_type: str):
    """
    Task 1: Extracts raw text from a file and chains the AI processing task.
    """
    print(f"Starting text extraction task for resume_id: {resume_id}")
    db = SessionLocal()
    resume_uuid = uuid.UUID(resume_id)
    
    try:
        print(f"Task {resume_id}: Parsing file at {file_path}...")
        raw_text = extract_text_from_file(file_path, content_type)
        
        if not raw_text:
            print(f"Task {resume_id}: Parser returned no text. Marking as 'parse_failed'.")
            crud.update_resume_status(db, resume_uuid, "parse_failed")
        else:
            print(f"Task {resume_id}: Parsing complete. Saving {len(raw_text)} chars.")
            crud.update_resume_text_and_status(
                db=db,
                resume_id=resume_uuid,
                raw_text=raw_text,
                status="ai_processing" 
            )
            print(f"Task {resume_id}: Text saved. Chaining AI task...")
            
            extract_structured_data_task.delay(resume_id)

    except Exception as e:
        print(f"Task {resume_id}: FAILED during text extraction. Error: {e}")
        try:
            crud.update_resume_status(db, resume_uuid, "parse_failed")
        except Exception as db_e:
            print(f"Task {resume_id}: FAILED to update status to 'parse_failed'. Error: {db_e}")
    finally:
        db.close()
        
    return f"Task {resume_id} finished text extraction and chained AI task."

@celery_app.task
def test_celery_task():
    """A simple test task."""
    time.sleep(2)
    print("Celery test task executed!")
    return "Test task successful"



@celery_app.task(name="run_matching_task")
def run_matching_task(match_id: str, resume_json: dict, job_json: dict):
    """
    Task 3: (Async Wrapper) Runs the synchronous matching function and
    saves the result to the JobMatch table.
    """
    print(f"Starting async match task for match_id: {match_id}")
    db = SessionLocal()
    match_uuid = uuid.UUID(match_id)
    
    try:
        match_data = call_gemini_for_matching(resume_json, job_json)
        
        crud.update_job_match_result(
            db=db,
            match_id=match_uuid,
            status="completed",
            match_data=match_data # This dict is now JSON serializable
        )
        print(f"Async match task {match_id} completed and saved.")
    
    except Exception as e:
        print(f"Async match task {match_id} FAILED. Error: {e}")
        try:
            db.rollback() 
            crud.update_job_match_result(
                db=db,
                match_id=match_uuid,
                status="failed",
                match_data={"error": str(e)} 
            )
        except Exception as db_e:
            print(f"Async match task {match_id}: FAILED to even update status. Error: {db_e}")
    finally:
        db.close()
        
    return f"Async match task {match_id} finished."



def call_gemini_for_matching(resume_json: dict, job_json: dict) -> dict:
    """
    This is a SYNCHRONOUS function (not a Celery task) that calls Gemini
    to get a job match analysis.
    """
    if not genai_client:
        raise Exception("Google Gemini client not initialized. Check GOOGLE_API_KEY.")

    match_schema = MatchResponse.model_json_schema()

    prompt = f"""
    You are an expert, unbiased HR recruitment analyst.
    Your task is to perform a detailed, quantitative, and qualitative match
    between the provided candidate's resume and the job description.

    You must generate a unique 'matchId' as a UUID string,
    and a 'matchedAt' timestamp in ISO 8601 format.
    The 'resumeId' must be copied from the input resume data 'id' field.
    The 'jobTitle' and 'company' must be copied from the input job description.
    
    Return your analysis *only* as a JSON object adhering strictly to the
    provided JSON schema. Do not include any other text or markdown.

    Here is the JSON schema you *must* follow:
    {json.dumps(match_schema)}

    Here is the candidate's resume data (in JSON format):
    ---
    {json.dumps(resume_json)}
    ---

    Here is the job description (in JSON format):
    ---
    {json.dumps(job_json)}
    ---
    """
    
    print("Calling Gemini API for /match analysis (model: gemini-2.5-flash)...")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash", 
        generation_config={"response_mime_type": "application/json"}
    )
    
    start_time = time.time()
    
    response = model.generate_content(prompt)
    ai_response_str = response.text.strip().lstrip("```json").rstrip("```")

    print("Gemini /match response received. Validating...")
    
    ai_data_dict = json.loads(ai_response_str)
    
    if "metadata" not in ai_data_dict:
        ai_data_dict["metadata"] = {}
    
    ai_data_dict["metadata"]["processingTime"] = time.time() - start_time
    
    ai_data_dict["resumeId"] = resume_json.get("id")
    ai_data_dict["jobTitle"] = job_json.get("title")
    ai_data_dict["company"] = job_json.get("company")
    validated_data = MatchResponse.model_validate(ai_data_dict)
    
    json_string = validated_data.model_dump_json(by_alias=True)
    clean_dict = json.loads(json_string)
    
    return clean_dict 