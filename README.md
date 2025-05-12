# Candidate Eval
In this use case the system performs a comprehensive assessment of the suitability of several candidates in relation to one or more job vacancies. To do so, it shall analyze in detail the job description, considering the technical requirements, experience and competencies needed, and compare this information with the candidates' profiles through the analysis of their resumes.

As a result of this process, the system will assign a score that reflects the degree of suitability of each candidate for the vacancy. In addition, it will identify the skills or requirements that are not covered in each profile, establishing an order of priority based on their relevance to the position.

## Project Structure

This project is fully containerized. It uses **Docker Compose** to spin up the following services:

- `candidate-eval`: The FastAPI backend
- `postgres`: PostgreSQL database (shared with Langflow)
- `minio`: S3-compatible object storage

## 🐳 Quick Start

### 1. Clone the repository
```
git clone https://your-repo-url
cd candidate_eval
```

### 2. Start the services
```
docker compose up --build
```

This will:

- Start the backend API
- Launch PostgreSQL with pre-configured users:
    - langflow
    - recruiter
- Launch a MinIO server for storing documents like resumes and job descriptions

⚠️ Make sure these services are running before you launch Langflow, as Langflow relies on the shared database defined here.

## 🧪 Scripts
Inside candidate_eval/scripts/:

- apply_migration.py: Apply DB migrations using Alembic
- generate_migration.py: Generate new DB migration scripts
- init-langflow-db.sh: Initialize Langflow database schema
- test_flows.py: Script for testing flow-based evaluations

## 📌 Notes
This backend must be started before Langflow.

Langflow will connect to the PostgreSQL instance and use the langflow user for its data.

The recruiter user is intended for candidate evaluation purposes.