from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from .database import Base

class Resume(Base):
    """
    Database model for the 'resumes' table.
    This defines the columns and their data types.
    """
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    processing_status = Column(String(50), default='pending', index=True)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    raw_text = Column(Text, nullable=True)
    structured_data = Column(JSONB, nullable=True)
    ai_enhancements = Column(JSONB, nullable=True)
    
    resume_metadata = Column("metadata", JSONB, nullable=True)

    def __repr__(self):
        return f"<Resume(id={self.id}, file_name='{self.file_name}', status='{self.processing_status}')>"


class JobMatch(Base):
    """
    Database model for the 'job_matches' table.
    Stores the status and result of an asynchronous match request.
    """
    __tablename__ = "job_matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False, index=True)
    
    status = Column(String(50), default='pending', index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    job_description = Column(JSONB, nullable=True) 
    match_result = Column(JSONB, nullable=True) 
    
    def __repr__(self):
        return f"<JobMatch(id={self.id}, resume_id={self.resume_id}, status='{self.status}')>"