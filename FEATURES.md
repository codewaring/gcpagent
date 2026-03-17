# Feature Snapshot

## Current Functional Modules

- JD generation with Gemini (`/chat`, `/generate`)
- GCS-backed JD persistence and metadata indexing
- Public gallery for JD browsing
- Candidate apply flow with resume upload
- Resume parsing for recruiter-ready fields
- Recruiter dashboard with ranking and strengths summary
- Duplicate-application prevention

## Recruiter Pipeline Highlights

- Parsed fields:
  - applicant name
  - applicant email
  - applicant phone
  - current title
  - years of experience
  - detected skills
  - short profile summary
- Ranking outputs:
  - `match_score`
  - `matched_skills`
  - `strengths_summary`

## Google Cloud AI + Data Integration

- Vertex AI Gemini generation:
  - `src/chat_agent.py` (`ChatAgent.reply`)
  - `src/jd_agent.py` (`JDAgent.generate`)
- Reference grounding from GCS:
  - `src/reference_store.py` (`build_reference_context`)
- JD storage in GCS:
  - `src/jd_store.py`
- Application/resume storage in GCS:
  - `src/application_store.py`

## Deduplication Rule

In `POST /api/jds/{jd_id}/apply`:

- If same resume fingerprint (SHA-256) exists for that JD -> duplicate
- If same email exists for that JD -> duplicate
- Duplicate case returns existing `application_id` and does not create a new record
