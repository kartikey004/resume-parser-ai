AI Resume Parser - System Architecture

This document outlines the high-level architecture of the AI Resume Parser application, built for the hackathon.

1. Core Technology Stack

The application is built using a modern, scalable, and containerized Python stack:

Backend Framework: FastAPI

Asynchronous Tasks: Celery

Message Broker: Redis

Database: PostgreSQL

AI/LLM: Google Gemini API (gemini-2.5-flash)

Containerization: Docker & Docker Compose

Text Extraction: pdfplumber, python-docx, pytesseract (OCR)

Testing: pytest & httpx

2. System Design: Asynchronous & Scalable

The entire system is designed around an asynchronous, event-driven architecture to handle time-consuming tasks (like OCR and AI calls) without blocking the user.

The application is split into four main containerized services managed by docker-compose.yml:

api (FastAPI Server):

Handles all incoming HTTP requests (e.g., POST /upload).

Performs initial validation (like file size).

Creates initial records in the PostgreSQL database.

Delegates all heavy lifting to the worker service by dispatching a Celery task.

Instantly returns a 200 or 202 response to the user with a task ID.

worker (Celery Worker):

This is the "brain" of the operation. It runs in the background and listens for tasks from the api service via the Redis queue.

It performs the multi-stage processing pipeline on a separate CPU core, ensuring the api service stays fast and responsive.

It has its own database connection to update the status and save the results as it works.

db (PostgreSQL Database):

The central "source of truth".

Stores all file metadata, processing status, extracted text, and the final structured JSON data from the AI.

Using JSONB columns allows for efficient storage and querying of the AI's complex JSON output.

redis (Broker & Backend):

Acts as the communication highway between the api and worker services.

Broker: Holds the queue of tasks (e.g., "process this resume") that the api sends.

Backend: (Optional) Stores the results of tasks, though we are saving our primary results in PostgreSQL.

3. Data Flow: The Multi-Stage AI Pipeline

When a user uploads a resume, it kicks off a sophisticated, chained pipeline:

HTTP Request (POST /upload): The api service receives the file.

Save & Queue: The api saves the file to a shared Docker volume (/app/uploads) and creates a Resume record in PostgreSQL with status: "processing". It then sends a process_resume_task message to Celery (via Redis).

Task 1: Text Extraction: The worker picks up the task, reads the file from the shared volume, and uses the parser.py library to extract the raw_text (using OCR if necessary). It saves this text to the database and updates the status to status: "ai_processing".

Task 1 (Chain): At the end of its run, process_resume_task chains a new task: extract_structured_data_task.

Task 2: AI Enrichment (Multi-Call): The worker picks up this second task and performs a series of sequential AI calls using the raw_text:

Call 1 (Parsing): Generates the core structured JSON (experience, skills, etc.).

Call 2 (Bias): Generates the biasReport.

Call 3 (Anonymization): Generates the anonymizedData.

Call 4 (Salary): Generates the salaryEstimate.

Call 5 (Career): Generates the careerProgression.

Final Update: The worker merges all these JSON objects and saves the complete result to the structured_data and ai_enhancements columns in the database, setting the final status to status: "completed".

HTTP Request (GET /status): The user polls the status endpoint.

HTTP Request (GET /resumes/{id}): Once the status is "completed", the user can retrieve the final, validated, and properly formatted JSON response.

This architecture is highly scalable. To handle more requests, we would simply run docker compose up --scale worker=5 to spin up five workers, all processing the task queue in parallel.
