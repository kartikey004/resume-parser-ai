# AI-Powered Resume Parser

**Hackathon Submission for: `tarindersingh-gemini/resume-parser-hackathon`**

This project is a complete, AI-powered resume parsing and analysis engine built for the hackathon. It features a fully asynchronous pipeline that can extract, structure, and analyze resume data, and an advanced AI matching system to score resumes against job descriptions.

## 1. Core Technology Stack

This application is built as a scalable, multi-service system using modern best practices.

- **Backend Framework**: **FastAPI**
- **Asynchronous Tasks**: **Celery**
- **Message Broker**: **Redis**
- **Database**: **PostgreSQL (with JSONB)**
- **AI/LLM**: **Google Gemini API (`gemini-2.5-flash`)**
- **Containerization**: **Docker** & **Docker Compose**
- **Document Parsing**: `pdfplumber`, `python-docx`, `pytesseract` (for OCR)
- **Automated Testing**: `pytest` & `httpx`

## 2. Features Implemented

This project successfully implements all **Core Features** and nearly all **Advanced Features** from the hackathon specification.

### Core Features

- **Full Document Support**: Handles `.pdf` (text & scanned), `.docx`, `.txt`, and image (`.jpg`, `.png`) files using a hybrid parsing and OCR engine.
- **Asynchronous Pipeline**: Uploads are processed in the background using Celery, keeping the API fast and responsive.
- **AI-Powered Data Extraction**: A multi-stage AI pipeline uses Google Gemini to extract all required fields, including:
  - `personalInfo` (Name, Contact, Address)
  - `summary` (Text, Career Level, Industry)
  - `experience` (Roles, Companies, Durations)
  - `education` (Degrees, Institutions, Dates)
  - `skills` (Technical, Soft, Languages)
  - `certifications`
- **File Size Validation**: Rejects files larger than 10MB with a `413` error.
- **Full API Implementation**: All specified RESTful endpoints are implemented.

### Advanced Features

- **Resume-to-Job Matching**: A `POST /resumes/{id}/match` endpoint provides a deep, AI-powered analysis, scoring a resume against a job description. This is also fully asynchronous.
- **Bias Detection**: A dedicated AI call analyzes the resume for potential gender, age, or ethnicity bias and includes a report.
- **Anonymization**: A separate AI-generated `anonymizedData` block is created, redacting all PII.
- **Salary Estimation**: The AI provides a market-based salary estimation (`salaryEstimate`) based on the candidate's skills and experience.
- **Career Progression**: The AI suggests potential future roles and skill development areas (`careerProgression`).
- **Analytics Endpoint**: A `GET /analytics/resume/{id}` endpoint provides a lightweight way to fetch just the `aiEnhancements` block.

## 3. How to Run

This project is fully containerized with Docker. All you need is **Docker Desktop** running.

### Step 1: Clone the Repository

```bash
git clone [https://github.com/tarindersingh-gemini/resume-parser-hackathon.git](https://github.com/tarindersingh-gemini/resume-parser-hackathon.git)
cd resume-parser-hackathon
```
