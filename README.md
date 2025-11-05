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
git clone https://github.com/kartikey004/resume-parser-ai.git
cd resume-parser-ai
```

### Step 2: Set Up Your Environment
A setup.sh script is provided to automate the entire setup.
First, make the script executable:

```bash
# On macOS/Linux. (On Windows, use 'git bash' or 'wsl' to run .sh files)
chmod +x setup.sh
```
Next, run the script. The first time you run it, it will create your .env file and ask you to add your Google API key.
```bash
./setup.sh
```

### Step 3: Add Your API Key

The setup script successfully created a new configuration file for you. This step is critical to activate the AI features by providing your key.

1.  Open the newly created **`.env`** file in your project root.
2.  Locate the `GOOGLE_API_KEY` line (it will be blank if you haven't edited it).
3.  Paste your Google AI Studio API key after the equals sign.

### Content to Verify in your .env file:

```text
# .env (Example content)
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=resume_parser_db
DATABASE_URL=postgresql://myuser:mypassword@db:5432/resume_parser_db

REDIS_URL=redis://redis:6379/0
GOOGLE_API_KEY=AIzaSy...your-key-here...  <-- PASTE KEY HERE
```
Once you have saved your key in the .env file, you are ready to proceed to the final step (Step 4: Run the Application).

### Step 4: Run the Application

Now that your Google API key is saved in the `.env` file, run the setup script one last time. This command will build the final Docker images (integrating all Python packages and source code) and start the entire service stack (`api`, `worker`, `redis`, `db`).

```bash
./setup.sh
```
### Final Verification:

Once the script finishes and reports "SUCCESS! The AI Resume Parser is running.", your project is fully deployed.

* **API URL (FastAPI):** http://localhost:8000
* **Interactive Docs (Swagger UI):** http://localhost:8000/docs

You can confirm the application is operational by visiting the Swagger UI and testing the **Health Check** endpoint.
