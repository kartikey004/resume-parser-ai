from pydantic import BaseModel, Field, model_validator
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from . import ai_schemas

class HealthCheck(BaseModel):
    """
    Response model for the health check endpoint.
    """
    api_status: str
    db_status: str

class ResumeStatus(BaseModel):
    """
    Response model for checking the status of a resume.
    """
    id: uuid.UUID
    
    status: str = Field(validation_alias="processing_status")

    class Config:
        from_attributes = True

class ResumeUploadResponse(BaseModel):
    """
    Response model sent back immediately after a successful upload.
    """
    id: uuid.UUID
    file_name: str
    
    content_type: str = Field(validation_alias="file_type")
    file_size: int
    status: str = Field(validation_alias="processing_status")
    uploaded_at: datetime

    class Config:
        from_attributes = True


class Metadata(BaseModel):
    """
    A sub-model for the 'metadata' block in the final response.
    """
    file_name: str
    file_size: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

class ResumeDataResponse(BaseModel):
    """
    Response model for the GET /api/v1/resumes/{id} endpoint.
    This model constructs the final, nested JSON from the flat DB record.
    """
    id: uuid.UUID
    
    metadata: Metadata
    personalInfo: Optional[ai_schemas.PersonalInfo] = None
    summary: Optional[ai_schemas.Summary] = None
    experience: List[ai_schemas.WorkExperience] = []
    education: List[ai_schemas.Education] = []
    skills: Optional[ai_schemas.Skills] = None
    certifications: List[ai_schemas.Certification] = []
    aiEnhancements: Optional[ai_schemas.AIEnhancements] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True 

    @model_validator(mode='before')
    @classmethod
    def build_nested_response(cls, db_resume):
        """
        This validator takes the flat 'db_resume' (our database model)
        and builds the complex, nested response model.
        """
        
        metadata = Metadata(
            file_name=db_resume.file_name,
            file_size=db_resume.file_size,
            uploaded_at=db_resume.uploaded_at,
            processed_at=db_resume.processed_at,
        )
        
        structured_data = db_resume.structured_data or {}
        personalInfo = None
        summary = None
        experience = []
        education = []
        skills = None
        certifications = []
        
        if "personalInfo" in structured_data and structured_data.get("personalInfo"):
            personalInfo = ai_schemas.PersonalInfo.model_validate(structured_data["personalInfo"])
        if "summary" in structured_data and structured_data.get("summary"):
            summary = ai_schemas.Summary.model_validate(structured_data["summary"])
        
        if "experience" in structured_data:
            experience = [ai_schemas.WorkExperience.model_validate(exp) for exp in structured_data.get("experience") or []]
        if "education" in structured_data:
            education = [ai_schemas.Education.model_validate(edu) for edu in structured_data.get("education") or []]
        if "skills" in structured_data and structured_data.get("skills"):
            skills = ai_schemas.Skills.model_validate(structured_data["skills"])
        if "certifications" in structured_data:
            certifications = [ai_schemas.Certification.model_validate(cert) for cert in structured_data.get("certifications") or []]

        aiEnhancements = None
        ai_data = db_resume.ai_enhancements
        if ai_data:
            aiEnhancements = ai_schemas.AIEnhancements.model_validate(ai_data)
        
        return {
            "id": db_resume.id,
            "metadata": metadata,
            "personalInfo": personalInfo,
            "summary": summary,
            "experience": experience,
            "education": education,
            "skills": skills,
            "certifications": certifications,
            "aiEnhancements": aiEnhancements,
        }


class ResumeAnalyticsResponse(BaseModel):
    """
    Response model for the GET /api/v1/analytics/resume/{id} endpoint.
    """
    id: uuid.UUID
    status: str = Field(validation_alias="processing_status")
    ai_enhancements: Optional[ai_schemas.AIEnhancements] = Field(default=None, validation_alias="ai_enhancements")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ResumeDeleteResponse(BaseModel):
    """
    Response model for the DELETE /api/v1/resumes/{id} endpoint.
    """
    message: str


class MatchCreateResponse(BaseModel):
    """
    Response model for the *new* async POST /match endpoint.
    """
    match_id: uuid.UUID = Field(validation_alias="id") # Map 'id' from db_match to 'match_id'
    resume_id: uuid.UUID
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True 

class MatchStatusResponse(BaseModel):
    """
    Response model for the GET /matches/{id}/status endpoint.
    """
    match_id: uuid.UUID
    status: str