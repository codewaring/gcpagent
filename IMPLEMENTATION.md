# Implementation Guide: Globe Telecom JD + Hiring Demo

This document explains how the system works end-to-end, which files are responsible for each capability, and exactly where Google Cloud AI is used.

## 1. End-to-End Architecture

```text
Browser (chat/gallery/recruiter)
  -> FastAPI (src/main.py)
    -> Gemini generation modules (src/chat_agent.py, src/jd_agent.py)
    -> GCS reference loader (src/reference_store.py)
    -> JD persistence (src/jd_store.py)
    -> Application persistence + dedup (src/application_store.py)
    -> Resume parsing (src/resume_parser.py)
  -> Google Cloud services
    - Vertex AI Gemini
    - Cloud Storage
```

## 2. Where Google Cloud AI Is Used

### 2.1 Vertex AI Gemini calls

- `src/chat_agent.py`
  - `ChatAgent.__init__()` initializes `genai.Client()`
  - `ChatAgent.reply()` calls `self.client.models.generate_content(...)`
  - Used by `POST /chat` in `src/main.py`

- `src/jd_agent.py`
  - `JDAgent.__init__()` initializes `genai.Client()`
  - `JDAgent.generate()` calls `self.client.models.generate_content(...)`
  - Used by `POST /generate` in `src/main.py`

### 2.2 Vertex AI environment wiring

- `src/config.py` -> `get_settings()`
  - Reads `GOOGLE_CLOUD_PROJECT`
  - Reads `GOOGLE_CLOUD_LOCATION`
  - Reads `MODEL_NAME`
  - Runtime depends on `GOOGLE_GENAI_USE_VERTEXAI=true`

## 3. Where Google Cloud Storage Is Used

- `src/reference_store.py`
  - `build_reference_context()` loads reference docs from GCS for prompt grounding
  - SDK path via `google.cloud.storage`
  - Fallback path via `gcloud storage` CLI

- `src/jd_store.py`
  - `save_jd()`, `get_jd()`, `list_jds()`
  - Maintains `generated-jds/.index.json`

- `src/application_store.py`
  - `save_application()` stores `application.json` + resume file
  - `list_applications()`, `get_resume_bytes()` for recruiter APIs
  - `find_duplicate_application()` checks for duplicates by resume fingerprint and email

## 4. Request Flows

### 4.1 JD generation flow (`POST /chat`)

1. `src/main.py:chat()` receives message/history
2. Loads reference context via `GCSReferenceStore.build_reference_context()`
3. Loads template via `TemplateStore.get_template()`
4. Calls Gemini via `ChatAgent.reply()`
5. Cleans output and persists JD via `JDStore.save_jd()`
6. Returns response + updated history

### 4.2 Candidate apply flow (`POST /api/jds/{jd_id}/apply`)

1. `src/main.py:apply_to_jd()` validates file type/size
2. Parses resume via `ResumeParser.parse()`
3. Dedup check via `ApplicationStore.find_duplicate_application()`
4. If duplicate: returns existing `application_id` and `is_duplicate=true`
5. Else: stores application via `ApplicationStore.save_application()`

### 4.3 Recruiter ranking flow (`GET /api/jds/{jd_id}/applications`)

1. Loads applications from GCS metadata
2. Backfills missing historical parse fields from source resume if needed
3. Computes `match_score`, `matched_skills`, and `strengths_summary`
4. Returns sorted candidate list (highest score first)

## 5. Backend File Responsibilities

- `src/main.py`
  - API contracts, orchestration, ranking heuristics, backfill logic
- `src/chat_agent.py`
  - Multi-turn Gemini prompt assembly and generation
- `src/jd_agent.py`
  - Structured generation path for API clients
- `src/reference_store.py`
  - GCS-based reference ingestion and text extraction
- `src/jd_store.py`
  - JD object and index persistence in GCS
- `src/application_store.py`
  - Application metadata/resume persistence + dedup checks
- `src/resume_parser.py`
  - Resume extraction/parsing logic
- `src/config.py`
  - Environment settings
- `src/template_store.py`
  - Template loading

## 6. Frontend File Responsibilities

- `src/chat.html`: JD chat client
- `src/gallery.html`: public JD browsing + apply modal
- `src/recruiter.html`: recruiter review dashboard with ranking

## 7. Buckets and Data Model

- JD content bucket (example): `gs://jackytest007/generated-jds/`
- Application bucket (example): `gs://jackytest008/job-applications/...`

Application metadata includes:
- applicant identity/contact
- parsed profile fields
- strengths summary inputs
- resume fingerprint (SHA-256) for dedup

## 8. Current Functional Scope

Implemented:
- JD generation with Gemini
- Reference-grounded prompting from GCS
- JD storage + gallery
- Resume upload + parsing
- Recruiter ranking + strengths summary
- Duplicate prevention

Not implemented:
- authentication/authorization
- human-in-the-loop approval workflow
- model-based semantic candidate reranking (current scoring is deterministic heuristic)

## 9. Operational Notes

- For local runs, ensure:
  - valid ADC (`gcloud auth application-default login`)
  - correct env vars for project/location/model/buckets
- If SDK auth has issues, stores can fall back to `gcloud` CLI paths.

## 10. API Index

- `GET /`
- `GET /gallery`
- `GET /recruiter`
- `POST /chat`
- `POST /generate`
- `GET /api/jds`
- `GET /api/jds/{jd_id}`
- `POST /api/jds/{jd_id}/apply`
- `GET /api/jds/{jd_id}/applications`
- `GET /api/applications`
- `GET /api/jds/{jd_id}/applications/{application_id}/resume`
- `GET /health`
