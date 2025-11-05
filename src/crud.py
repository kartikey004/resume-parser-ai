from sqlalchemy.orm import Session
from sqlalchemy import func, select
from . import models, schemas, ai_schemas
import uuid
from datetime import datetime 
from typing import Optional, Dict, Any
from pathlib import Path
import os
from .config import settings 

def create_resume(db: Session, file_name: str, file_size: int, content_type: str) -> models.Resume:
    """
    Creates a new resume entry in the database with 'processing' status.
    """
    db_resume = models.Resume(
        file_name=file_name,
        file_size=file_size,
        file_type=content_type, 
        processing_status="processing" 
    )
    
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume

def get_resume_status(db: Session, resume_id: uuid.UUID) -> Optional[schemas.ResumeStatus]:
    """
    Gets the processing status of a resume by its ID.
    """
    db_resume = db.get(models.Resume, resume_id)
    if db_resume:
        return schemas.ResumeStatus.model_validate(db_resume)
    return None

def update_resume_text_and_status(db: Session, resume_id: uuid.UUID, raw_text: str, status: str) -> Optional[models.Resume]:
    """
    Updates the raw_text, status, and processed_at timestamp of a resume.
    """
    db_resume = db.get(models.Resume, resume_id)
    if db_resume:
        db_resume.raw_text = raw_text
        db_resume.processing_status = status
        db_resume.processed_at = datetime.utcnow() # Set the processed time
        db.commit()
        db.refresh(db_resume)
        return db_resume
    return None

def update_resume_status(db: Session, resume_id: uuid.UUID, status: str) -> Optional[models.Resume]:
    """
    Updates *only* the status and processed_at timestamp.
    This is used for logging failures.
    """
    db_resume = db.get(models.Resume, resume_id)
    if db_resume:
        db_resume.processing_status = status
        db_resume.processed_at = datetime.utcnow() # Set the processed time
        db.commit()
        db.refresh(db_resume)
        return db_resume
    return None

def update_resume_structured_data(db: Session, resume_id: uuid.UUID, data: dict) -> Optional[models.Resume]:
    """
    Updates the structured_data, ai_enhancements, status, and processed_at
    timestamp after the AI has successfully parsed the data.
    """
    db_resume = db.get(models.Resume, resume_id)
    if db_resume:
        ai_data = data.pop('aiEnhancements', None)
        
        db_resume.structured_data = data
        db_resume.ai_enhancements = ai_data
        
        db_resume.processing_status = "completed"
        db_resume.processed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_resume)
        return db_resume
    return None

def get_resume_by_id(db: Session, resume_id: uuid.UUID) -> Optional[models.Resume]:
    """
    Gets the full resume object by its ID.
    """
    return db.get(models.Resume, resume_id)

def get_resume_analytics(db: Session, resume_id: uuid.UUID) -> Optional[Any]:
    """
    Gets only the analytics-related data for a resume.
    This is more efficient than get_resume_by_id if we only need this blob.
    """
    stmt = (
        select(
            models.Resume.processing_status,
            models.Resume.ai_enhancements
        )
        .where(models.Resume.id == resume_id)
    )
    result = db.execute(stmt).first()
    return result

def delete_resume_by_id(db: Session, resume_id: uuid.UUID) -> Optional[models.Resume]:
    """
    Deletes a resume from the database and its corresponding file from disk.
    """
    db_resume = db.get(models.Resume, resume_id)
    if db_resume:
        try:
            file_extension = Path(db_resume.file_name).suffix
            file_path = Path(settings.UPLOADS_DIR) / f"{db_resume.id}{file_extension}"
            
            if file_path.exists():
                os.remove(file_path)
                print(f"Successfully deleted file: {file_path}")
            else:
                print(f"File not found, skipping delete: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

        db.delete(db_resume)
        db.commit()
        
        return db_resume # Return the deleted object
    
    return None

def manually_update_resume_data(db: Session, resume_id: uuid.UUID, data: ai_schemas.AIParsedData) -> models.Resume | None:
    """
    Manually overwrites the structured_data and ai_enhancements for a resume.
    """
    db_resume = db.get(models.Resume, resume_id)
    if db_resume:
        data_dict = data.model_dump(by_alias=True)
        
        ai_data = data_dict.pop('aiEnhancements', None)
        
        db_resume.structured_data = data_dict
        db_resume.ai_enhancements = ai_data
        
        db_resume.processing_status = "completed" 
        db_resume.processed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_resume)
        return db_resume
    return None


def create_job_match(
    db: Session, 
    resume_id: uuid.UUID, 
    job_description: Dict[str, Any]
) -> models.JobMatch:
    """
    Creates a new job_match entry in the database with 'pending' status.
    """
    db_match = models.JobMatch(
        resume_id=resume_id,
        job_description=job_description,
        status="pending"
    )
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match

def update_job_match_result(
    db: Session, 
    match_id: uuid.UUID, 
    status: str, 
    match_data: Optional[Dict[str, Any]] = None
):
    """
    Updates the status and final result of a job match task.
    """
    db_match = db.get(models.JobMatch, match_id)
    if db_match:
        db_match.status = status
        db_match.match_result = match_data
        db_match.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_match)
        return db_match
    return None

def get_job_match_by_id(db: Session, match_id: uuid.UUID) -> Optional[models.JobMatch]:
    """
    Gets the full job_match object by its ID.
    """
    return db.get(models.JobMatch, match_id)

def get_match_status_by_id(db: Session, match_id: uuid.UUID) -> Optional[Any]:
    """
    Gets only the status of a job match by its ID.
    """
    stmt = select(models.JobMatch.status).where(models.JobMatch.id == match_id)
    result = db.execute(stmt).first()
    return result