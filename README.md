# Globe Telecom JD + Hiring Demo on Google Cloud

Production-style demo that generates job descriptions with Gemini, publishes them in a public gallery, accepts candidate applications, parses resumes, ranks candidates, and exposes a recruiter dashboard.

## What This Demo Can Do

- Generate JD content with Gemini (`/chat`, `/generate`)
- Store JDs in Google Cloud Storage with metadata indexing
- Public gallery for JD browsing and application upload
- Resume upload pipeline (PDF/DOC/DOCX)
- Automatic resume parsing (name, email, phone, title, years, skills, summary)
- Recruiter dashboard with ranking and strengths summary
- Application deduplication by resume fingerprint and email

## Google Cloud AI Capabilities (Critical Demo Mapping)

This project is specifically a Google Cloud AI demo. The AI and cloud capabilities are implemented in the files and symbols below.

| Capability | Google Cloud Service | Where In Code |
|---|---|---|
| Conversational JD generation | Vertex AI Gemini | `src/chat_agent.py` -> `ChatAgent.reply()` using `genai.Client().models.generate_content(...)` |
| Structured JD generation API | Vertex AI Gemini | `src/jd_agent.py` -> `JDAgent.generate()` |
| Model and region configuration | Vertex AI runtime config | `src/config.py` -> `get_settings()` reads `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `MODEL_NAME`, `GOOGLE_GENAI_USE_VERTEXAI` |
| Reference-grounded prompts | Cloud Storage + Gemini prompt context | `src/reference_store.py` -> `build_reference_context()`, consumed by `src/main.py` in `/chat` and `/generate` |
| JD persistence | Cloud Storage | `src/jd_store.py` -> `save_jd()`, `get_jd()`, `list_jds()` |
| Application and resume persistence | Cloud Storage | `src/application_store.py` -> `save_application()`, `list_applications()`, `get_resume_bytes()` |
| Duplicate prevention | Cloud Storage metadata + fingerprinting | `src/application_store.py` -> `find_duplicate_application()`, wired in `src/main.py` -> `apply_to_jd()` |

## API Surface

| Endpoint | Purpose |
|---|---|
| `GET /` | Chat UI |
| `GET /gallery` | Public JD gallery UI |
| `GET /recruiter` | Recruiter dashboard UI |
| `POST /chat` | Conversational JD generation |
| `POST /generate` | Structured JD generation |
| `GET /api/jds` | List JDs |
| `GET /api/jds/{jd_id}` | JD detail |
| `POST /api/jds/{jd_id}/apply` | Upload candidate resume for a JD |
| `GET /api/jds/{jd_id}/applications` | Ranked candidates for one JD |
| `GET /api/applications` | Ranked candidates across all JDs |
| `GET /api/jds/{jd_id}/applications/{application_id}/resume` | Download resume |
| `GET /health` | Health check |

## File-by-File Purpose

### Backend (`src/*.py`)

- `src/main.py`
  - FastAPI entrypoint, route registration, response models
  - Upload validation, resume parsing orchestration, candidate scoring, strengths summary generation
  - Dedup guard in `apply_to_jd()` via `ApplicationStore.find_duplicate_application()`
- `src/chat_agent.py`
  - Multi-turn chat JD generation with Gemini
  - System prompt rules and template/reference injection
- `src/jd_agent.py`
  - Structured prompt-based JD generation path (`/generate`)
- `src/reference_store.py`
  - Reads reference files from GCS (SDK first, gcloud fallback)
  - Extracts text from PDF/TXT/MD for prompt grounding
- `src/jd_store.py`
  - Stores generated JD markdown and maintains `.index.json`
- `src/application_store.py`
  - Stores application metadata + resume files in GCS
  - Handles duplicate detection by SHA-256 fingerprint and email
- `src/resume_parser.py`
  - Resume text extraction and information parsing
  - PDF and DOCX handling, skills extraction, summary extraction
- `src/config.py`
  - Environment-driven runtime settings
- `src/template_store.py`
  - Loads JD template markdown from disk

### Frontend (`src/*.html`)

- `src/chat.html`
  - Chat UX for JD generation
- `src/gallery.html`
  - Public JD list/detail page
  - Bottom-only `Apply` action and upload modal
- `src/recruiter.html`
  - Recruiter-side candidate list
  - Shows score, strengths summary, parsed resume fields, and resume download

### Supporting Files

- `templates/globe_telecom_default.md`: Base JD output format
- `.env.example`: Required runtime variables for Google Cloud + buckets
- `requirements.txt`: Python dependencies
- `IMPLEMENTATION.md`: Deep architecture and flow explanation
- `FEATURES.md`: Feature changelog snapshot

## Storage Layout

### JD bucket (`REFERENCE_BUCKET`, example `jackytest007`)

```text
gs://jackytest007/generated-jds/
  .index.json
  jd-<id>.md
```

### Application bucket (`APPLICATION_BUCKET`, example `jackytest008`)

```text
gs://jackytest008/job-applications/<jd_id>/<yyyy-mm-dd>/<application_id>_<candidate_slug>/
  application.json
  <resume_file>
```

## Quick Start

```bash
cd jd-agent-gcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

gcloud auth application-default login

export PYTHONPATH=$PWD:$PYTHONPATH
export GOOGLE_CLOUD_PROJECT=demo0908
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=true
export MODEL_NAME=gemini-2.5-pro
export TEMPLATE_DIR=templates
export REFERENCE_BUCKET=jackytest007
export APPLICATION_BUCKET=jackytest008
export APPLICATION_PREFIX=job-applications
export REFERENCE_ENABLED=true

uvicorn src.main:app --host 127.0.0.1 --port 8080
```

Open:
- Chat: `http://127.0.0.1:8080/`
- Gallery: `http://127.0.0.1:8080/gallery`
- Recruiter: `http://127.0.0.1:8080/recruiter`

## Deduplication Behavior

On `POST /api/jds/{jd_id}/apply`, backend checks existing applications for that JD:

1. Same resume fingerprint (SHA-256) -> duplicate
2. Same applicant email -> duplicate

If duplicate is found, backend returns existing `application_id` with:

```json
{
  "application_id": "existing-id",
  "message": "Duplicate application detected. Existing submission reused.",
  "is_duplicate": true
}
```

## Demo Notes

- UI is English-only for international demo audiences.
- This is intentionally cloud-native: Gemini + GCS are first-class runtime dependencies.
- Candidate ranking is heuristic and explainable; it is not a final hiring decision system.
