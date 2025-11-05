import time
import asyncio
import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
from . import models, schemas, crud, ai_schemas 
from .database import engine, SessionLocal
from .config import settings
from .tasks import process_resume_task, run_matching_task 


uploads_dir = Path(settings.UPLOADS_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI()


def get_db():
    """
    Dependency to get a new database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """
    On startup, try to connect to the database and create tables.
    """
    print("FastAPI application starting up...")
    
    db_ready = False
    retries = 5
    while not db_ready and retries > 0:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ready = True
            print("Database connection successful.")
        except Exception as e:
            print(f"Database connection failed. Retrying in 3 seconds... ({retries} retries left)")
            retries -= 1
            await asyncio.sleep(3)
            
    if not db_ready:
        print("FATAL: Could not connect to the database. Application startup failed.")
        return

    try:
        print("Creating database tables...")
        models.Base.metadata.create_all(bind=engine)
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")


@app.get("/api/v1/health", response_model=schemas.HealthCheck)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify API and DB connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = "error"
        
    return {"api_status": "ok", "db_status": db_status}

@app.post("/api/v1/resumes/upload", response_model=schemas.ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Uploads a resume file.
    1. Validates file size.
    2. Saves file metadata to the database.
    3. Saves the file to the shared 'uploads' volume.
    4. Triggers an asynchronous processing task.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")
        
    MAX_FILE_SIZE = 10 * 1024 * 1024  
    file_size = file.file.seek(0, 2)
    file.file.seek(0) 
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the 10MB limit. File size: {file_size / (1024 * 1024):.2f} MB"
        )
    
    file_name = file.filename
    content_type = file.content_type
    
    print(f"Received file: {file_name}, size: {file_size}, type: {content_type}")
    
    try:
        db_resume = crud.create_resume(
            db=db,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
        
    file_extension = Path(file_name).suffix
    saved_file_name = f"{db_resume.id}{file_extension}"
    file_path = uploads_dir / saved_file_name
    
    try:
        with file_path.open("wb") as buffer:
            while chunk := await file.read(8192):
                buffer.write(chunk)
        print(f"Successfully saved file to: {file_path}")
    except Exception as e:
        crud.update_resume_status(db, db_resume.id, "save_failed")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        process_resume_task.delay(
            resume_id=str(db_resume.id),
            file_path=str(file_path),
            content_type=content_type
        )
        print(f"Successfully queued task for resume_id: {db_resume.id}")
    except Exception as e:
        print(f"WARNING: Could not queue Celery task: {e}")
        crud.update_resume_status(db, db_resume.id, "queue_failed")

    # 5. Return the response
    return schemas.ResumeUploadResponse.model_validate(db_resume)

@app.get("/api/v1/resumes/{id}/status", response_model=schemas.ResumeStatus)
def get_resume_status(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Checks the processing status of an uploaded resume.
    """
    db_status = crud.get_resume_status(db, id)
    if db_status is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return db_status


@app.get("/api/v1/resumes/{id}", response_model=schemas.ResumeDataResponse)
def get_resume_data(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves the full, structured JSON data for a completed resume.
    """
    db_resume = crud.get_resume_by_id(db, id)
    
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    if db_resume.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"Resume processing is not complete. Current status: '{db_resume.processing_status}'"
        )
    return schemas.ResumeDataResponse.model_validate(db_resume)


@app.put("/api/v1/resumes/{id}", response_model=schemas.ResumeDataResponse)
def update_resume_data(
    id: uuid.UUID, 
    resume_data: ai_schemas.AIParsedData,
    db: Session = Depends(get_db)
):
    """
    Manually updates/overwrites the parsed data for a resume.
    """
    print(f"Received manual update request for resume_id: {id}")
    
    db_resume = crud.get_resume_by_id(db, id)
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    try:
        updated_resume = crud.manually_update_resume_data(
            db=db,
            resume_id=id,
            data=resume_data
        )
        return schemas.ResumeDataResponse.model_validate(updated_resume)
    except Exception as e:
        print(f"Manual update for resume_id {id} FAILED. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update data: {str(e)}")


@app.post("/api/v1/resumes/{id}/match", response_model=schemas.MatchCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def match_resume_with_job(
    id: uuid.UUID, 
    job_request: ai_schemas.MatchRequest,
    response: Response, 
    db: Session = Depends(get_db)
):
    """
    Performs an ASYNCHRONOUS AI-powered match between a processed resume
    and a provided job description.
    """
    print(f"Starting match request for resume_id: {id}")
    
    db_resume = crud.get_resume_by_id(db, id)
    
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if db_resume.processing_status != "completed" or not db_resume.structured_data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resume is not fully processed. Current status: '{db_resume.processing_status}'"
        )
    
    resume_data_model = schemas.ResumeDataResponse.model_validate(db_resume)
    resume_json_for_ai = resume_data_model.model_dump(exclude={"id", "metadata"})
    job_description_data = job_request.jobDescription.model_dump(by_alias=True)
    
    resume_json_for_ai['id'] = str(db_resume.id)
    
    try:
        db_match = crud.create_job_match(
            db=db,
            resume_id=id,
            job_description=job_description_data
        )
        
        run_matching_task.delay(
            match_id=str(db_match.id),
            resume_json=resume_json_for_ai,
            job_json=job_description_data
        )
        
        print(f"Successfully queued matching task. Match ID: {db_match.id}")
        
        response.status_code = status.HTTP_202_ACCEPTED
        return schemas.MatchCreateResponse.model_validate(db_match)
        
    except Exception as e:
        print(f"Match request for resume_id {id} FAILED. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue match task: {str(e)}")



@app.get("/api/v1/matches/{match_id}/status", response_model=schemas.MatchStatusResponse)
def get_match_status(match_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Checks the processing status of an asynchronous job match.
    """
    db_status = crud.get_match_status_by_id(db, match_id)
    
    if db_status is None:
        raise HTTPException(status_code=404, detail="Match job not found")
        
    return {"match_id": match_id, "status": db_status[0]}


@app.get("/api/v1/matches/{match_id}", response_model=ai_schemas.MatchResponse)
def get_match_result(match_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves the full, structured JSON data for a completed job match.
    """
    db_match = crud.get_job_match_by_id(db, match_id)
    
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match job not found")

    if db_match.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"Match processing is not complete. Current status: '{db_match.status}'"
        )
    
    if db_match.match_result is None:
         raise HTTPException(
            status_code=500,
            detail="Match is complete but no result data was found."
        )
        
    return db_match.match_result


@app.get("/api/v1/analytics/resume/{id}", response_model=schemas.ResumeAnalyticsResponse)
def get_resume_analytics(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves just the AI Enhancements block for a completed resume.
    """
    db_resume_analytics = crud.get_resume_analytics(db, id)
    
    if db_resume_analytics is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if db_resume_analytics.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resume processing is not complete. Current status: '{db_resume_analytics.processing_status}'"
        )
    
    analytics_data = {
        "id": id,
        "processing_status": db_resume_analytics.processing_status,
        "ai_enhancements": db_resume_analytics.ai_enhancements
    }
    return schemas.ResumeAnalyticsResponse.model_validate(analytics_data)


@app.delete("/api/v1/resumes/{id}", response_model=schemas.ResumeDeleteResponse)
def delete_resume(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Deletes a resume record from the database and its associated file
    from the file system.
    """
    print(f"Received delete request for resume_id: {id}")
    
    db_resume = crud.delete_resume_by_id(db, id)
    
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    return {"message": "Resume deleted successfully"}