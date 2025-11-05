from pydantic import BaseModel, Field, field_validator, model_validator
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Union


class Name(BaseModel):
    """Structured name of the individual."""
    first: Optional[str] = Field(default=None, description="The person's first name.")
    last: Optional[str] = Field(default=None, description="The person's last name.")
    full: str = Field(description="The person's full name.")

class Address(BaseModel):
    """Structured physical address."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None

class Contact(BaseModel):
    """Structured contact information."""
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Address] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None

class PersonalInfo(BaseModel):
    """All personal and contact information."""
    name: Optional[Name] = None
    contact: Optional[Contact] = None


class Summary(BaseModel):
    """The AI's analysis of the resume's summary section."""
    text: Optional[str] = Field(default=None, description="The extracted professional summary text.")
    careerLevel: Optional[str] = Field(default=None, description="AI-inferred career level (e.g., 'entry', 'mid', 'senior').")
    industryFocus: Optional[str] = Field(default=None, description="AI-inferred primary industry (e.g., 'technology', 'finance').")


class WorkExperience(BaseModel):
    """Structured work experience entry."""
    title: str = Field(description="The job title, e.g., 'Senior Software Engineer'.")
    company: str = Field(description="The name of the company.")
    location: Optional[str] = None
    start_date: Optional[str] = Field(default=None, description="Start date, e.g., '2021-03-01' or 'March 2021'.")
    end_date: Optional[str] = Field(default=None, description="End date, e.g., '2025-09-01' or 'Present'.")
    current: Optional[bool] = Field(default=False, description="True if this is the person's current job.")
    duration: Optional[str] = Field(default=None, description="AI-calculated duration, e.g., '4 years 6 months'.")
    description: Optional[str] = Field(default=None, description="Job description and responsibilities.")
    achievements: Optional[List[str]] = Field(default_factory=list, description="List of quantified achievements.")
    technologies: Optional[List[str]] = Field(default_factory=list, description="List of technologies used in this role.")


class Education(BaseModel):
    """Structured education entry."""
    degree: str = Field(description="The degree obtained, e.g., 'Bachelor of Science'.")
    field: Optional[str] = Field(default=None, description="The field of study, e.g., 'Computer Science'.")
    institution: str = Field(description="The name of the educational institution.")
    location: Optional[str] = None
    graduation_date: Optional[str] = Field(default=None, description="Graduation date, e.g., '2018-05-15' or 'May 2018'.")
    gpa: Optional[float] = None
    honors: Optional[List[str]] = Field(default_factory=list)


class TechnicalSkillItem(BaseModel):
    """A specific category of technical skills."""
    category: str = Field(description="The skill category, e.g., 'Programming Languages' or 'Frameworks'.")
    items: List[str] = Field(default_factory=list, description="List of skills in this category.")

class Language(BaseModel):
    """A spoken language and proficiency level."""
    language: str
    proficiency: Optional[str] = Field(default=None, description="e.g., 'Native', 'Conversational'.")

class Skills(BaseModel):
    """A collection of all skill types."""
    technical: Optional[List[TechnicalSkillItem]] = Field(default_factory=list)
    soft: Optional[List[str]] = Field(default_factory=list)
    languages: Optional[List[Language]] = Field(default_factory=list)


class Certification(BaseModel):
    """Structured certification entry."""
    name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = Field(default=None, alias="issueDate")
    expiry_date: Optional[str] = Field(default=None, alias="expiryDate")
    credential_id: Optional[str] = Field(default=None, alias="credentialId")
    
    class Config:
        populate_by_name = True # Allows using aliases like 'issueDate'


class BiasFinding(BaseModel):
    """Details of a single potential bias finding."""
    category: str = Field(description="Type of bias, e.g., 'Gender', 'Age', 'Ethnicity'.")
    finding: str = Field(description="The specific text or element identified as potentially biased.")
    suggestion: str = Field(description="Suggestion for mitigation or review.")

class BiasReport(BaseModel):
    """AI-generated report on potential biases in the resume."""
    biasDetected: bool = Field(default=False, description="Whether any potential biases were detected.")
    findings: List[BiasFinding] = Field(default_factory=list, description="A list of specific bias findings.")
    
    class Config:
        populate_by_name = True

class SalaryEstimate(BaseModel):
    """AI-generated salary estimation."""
    min: Optional[int] = Field(default=None, description="Estimated minimum salary.")
    max: Optional[int] = Field(default=None, description="Estimated maximum salary.")
    currency: str = Field(default="USD", description="Currency of the estimation (e.g., USD, INR).")
    comments: str = Field(description="AI's reasoning for this estimation based on location, experience, and skills.")

    class Config:
        populate_by_name = True

class CareerProgression(BaseModel):
    """AI-generated career progression insights."""
    suggestedNextRoles: List[str] = Field(default_factory=list, description="List of 3-5 suggested next job titles.")
    improvementAreas: List[str] = Field(default_factory=list, description="List of 2-3 skills or areas to develop for advancement.")
    comments: str = Field(description="AI's reasoning for these suggestions based on the candidate's profile.")
    
    class Config:
        populate_by_name = True

class AIEnhancements(BaseModel):
    """AI-generated insights about the resume."""
    qualityScore: Optional[int] = Field(default=None, description="Overall resume quality score (0-100).")
    completenessScore: Optional[int] = Field(default=None, description="Resume completeness score (0-100).")
    suggestions: Optional[List[str]] = Field(default_factory=list, description="AI suggestions for improvement.")
    industryFit: Optional[Dict[str, float]] = Field(default_factory=dict, description="A dictionary of industry names and their relevance score (0.0 to 1.0).")
    biasReport: Optional[BiasReport] = Field(default=None, description="Report on potential biases.")
    salaryEstimate: Optional[SalaryEstimate] = Field(default=None, description="AI-generated salary estimation.") # <-- NEW FIELD
    anonymizedData: Optional[Dict[str, Any]] = Field(default=None, description="Anonymized version of the parsed resume data.")
    careerProgression: Optional[CareerProgression] = Field(default=None, description="AI-suggested career paths and improvements.") # <-- NEW FIELD

    class Config:
        populate_by_name = True


class AIParsedData(BaseModel):
    """
    The main Pydantic schema for structured data extracted by the AI.
    This structure matches the hackathon's desired JSON output for the
    data fields that the AI is responsible for generating.
    """
    personalInfo: Optional[PersonalInfo] = Field(default=None)
    summary: Optional[Summary] = None
    experience: Optional[List[WorkExperience]] = Field(default_factory=list)
    education: Optional[List[Education]] = Field(default_factory=list)
    skills: Optional[Skills] = None
    certifications: Optional[List[Certification]] = Field(default_factory=list)
    aiEnhancements: Optional[AIEnhancements] = Field(default=None)

    class Config:
        from_attributes = True
        populate_by_name = True


class JobExperience(BaseModel):
    minimum: Optional[int] = None
    preferred: Optional[int] = None
    level: Optional[str] = None

class JobRequirements(BaseModel):
    required: List[str] = Field(default_factory=list)
    preferred: List[str] = Field(default_factory=list)

class JobSkills(BaseModel):
    required: List[str] = Field(default_factory=list)
    preferred: List[str] = Field(default_factory=list) 

class JobSalary(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    currency: Optional[str] = None

class JobDescription(BaseModel):
    """
    Pydantic model for the Job Description object provided in the
    /match endpoint request body.
    """
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    experience: Optional[JobExperience] = None
    description: Optional[str] = None
    requirements: Optional[JobRequirements] = None
    skills: Optional[JobSkills] = None
    salary: Optional[JobSalary] = None
    benefits: Optional[List[str]] = Field(default_factory=list)
    industry: Optional[str] = None
    
    class Config:
        populate_by_name = True

class MatchRequestOptions(BaseModel):
    includeExplanation: Optional[bool] = True
    detailedBreakdown: Optional[bool] = True
    suggestImprovements: Optional[bool] = True

class MatchRequest(BaseModel):
    """
    The request body for the POST /api/v1/resumes/{id}/match endpoint.
    """
    jobDescription: JobDescription
    options: Optional[MatchRequestOptions] = None


class SkillsMatchDetails(BaseModel):
    score: int
    weight: int
    details: Dict[str, Any]

class ExperienceMatchDetails(BaseModel):
    score: int
    weight: int
    details: Dict[str, Any]

class EducationMatchDetails(BaseModel):
    score: int
    weight: int
    details: Dict[str, Any]

class RoleAlignmentDetails(BaseModel):
    score: int
    weight: int
    details: Dict[str, Any]

class LocationMatchDetails(BaseModel):
    score: int
    weight: int
    details: Dict[str, Any]

class CategoryScores(BaseModel):
    skillsMatch: SkillsMatchDetails
    experienceMatch: ExperienceMatchDetails
    educationMatch: EducationMatchDetails
    roleAlignment: RoleAlignmentDetails
    locationMatch: LocationMatchDetails

class CriticalGap(BaseModel):
    category: str
    missing: str
    impact: str
    suggestion: str

class ImprovementArea(BaseModel):
    category: str
    missing: Union[str, List[str]]
    impact: str
    suggestion: str

class GapAnalysis(BaseModel):
    criticalGaps: List[CriticalGap] = Field(default_factory=list)
    improvementAreas: List[ImprovementArea] = Field(default_factory=list)

class SalaryAlignment(BaseModel):
    candidateExpectation: str
    jobSalaryRange: str
    marketRate: Optional[str] = None
    alignment: str

class MatchingResults(BaseModel):
    overallScore: int
    confidence: float
    recommendation: str
    categoryScores: CategoryScores
    strengthAreas: List[str] = Field(default_factory=list)
    gapAnalysis: GapAnalysis
    salaryAlignment: SalaryAlignment
    competitiveAdvantages: List[str] = Field(default_factory=list)

class Explanation(BaseModel):
    summary: str
    keyFactors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class MatchMetadata(BaseModel):
    matchedAt: datetime
    processingTime: float
    algorithm: str
    confidenceFactors: Optional[Dict[str, float]] = None

    @field_validator('matchedAt', mode='before')
    @classmethod
    def force_datetime(cls, v):
        if isinstance(v, str):
            try:
                # Handle ISO format with Z
                if v.endswith('Z'):
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                return datetime.fromisoformat(v)
            except ValueError:
                return datetime.now() # Fallback
        return v

class MatchResponse(BaseModel):
    """
    The full response schema for the GET /api/v1/resumes/{id}/match endpoint.
    """
    matchId: uuid.UUID
    resumeId: uuid.UUID
    jobTitle: str
    company: Optional[str] = None
    matchingResults: MatchingResults
    explanation: Explanation
    metadata: MatchMetadata

    class Config:
        populate_by_name = True