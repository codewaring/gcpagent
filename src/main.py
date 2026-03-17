from pathlib import Path
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .application_store import ApplicationStore
from .chat_agent import ChatAgent, ChatMessage
from .config import get_settings
from .jd_agent import JDAgent, JDRequest
from .reference_store import GCSReferenceStore
from .resume_parser import ResumeParser
from .template_store import TemplateStore
from .jd_store import JDStore, JDMetadata


class GenerateJDRequest(BaseModel):
    company_name: str = "Globe Telecom"
    business_unit: str
    role_title: str
    location: str
    employment_type: str
    seniority: str
    key_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    language: str = "English"
    template_name: str = "globe_telecom_default"
    use_reference_docs: bool = True
    reference_bucket: str | None = None
    reference_prefix: str | None = None


class GenerateJDResponse(BaseModel):
    job_description: str
    reference_sources_used: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)
    reference_bucket: str | None = None
    reference_prefix: str | None = None


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]


class JDListItem(BaseModel):
    jd_id: str
    role_title: str
    business_unit: str
    location: str
    created_at: str
    tags: list[str]


class JDDetailResponse(BaseModel):
    jd_id: str
    role_title: str
    business_unit: str
    location: str
    created_at: str
    tags: list[str]
    content: str


class ApplicationResponse(BaseModel):
    application_id: str
    message: str


class ApplicationListItem(BaseModel):
    application_id: str
    jd_id: str
    applicant_name: str
    applicant_email: str
    applicant_phone: str
    match_score: int
    matched_skills: list[str]
    strengths_summary: str
    current_title: str
    years_experience: str
    skills: list[str]
    profile_summary: str
    resume_filename: str
    resume_content_type: str
    uploaded_at: str
    resume_download_url: str


settings = get_settings()
app = FastAPI(title="Globe Telecom JD Agent", version="0.1.0")
store = TemplateStore(settings.template_dir)
agent = JDAgent(settings.model_name)
reference_store = GCSReferenceStore(
    max_files=settings.reference_max_files,
    max_chars_per_file=settings.reference_max_chars_per_file,
)
chat_agent = ChatAgent(settings.model_name)
jd_store = JDStore(bucket_name=settings.reference_bucket, prefix="generated-jds")
resume_parser = ResumeParser()
application_store = ApplicationStore(
    bucket_name=settings.application_bucket,
    prefix=settings.application_prefix,
)
_CHAT_HTML = (Path(__file__).parent / "chat.html").read_text(encoding="utf-8")
_GALLERY_HTML = (Path(__file__).parent / "gallery.html").read_text(encoding="utf-8")
_RECRUITER_HTML = (Path(__file__).parent / "recruiter.html").read_text(encoding="utf-8")

_ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
_ALLOWED_RESUME_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _clean_jd_content(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            return "\n".join(lines[index:]).strip()
    return text.strip()


def _extract_role_title(message: str, jd_content: str) -> str:
    cleaned_content = _clean_jd_content(jd_content)
    for line in cleaned_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()

    patterns = [
        r"(?:for|as|role of|position of)\s+a?n?\s+([A-Za-z][A-Za-z /&-]+)",
        r"(?:generate|create|write)\s+(?:a\s+jd\s+for\s+)?([A-Za-z][A-Za-z /&-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(".")

    return "Generated Role"


def _validate_resume_upload(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Resume must be a PDF, DOC, or DOCX file")

    if file.content_type and file.content_type not in _ALLOWED_RESUME_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported resume content type")


def _extract_years(text: str) -> int | None:
    match = re.search(r"(\d{1,2})\s*\+?\s*years?", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _clean_display_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_low_quality_summary(summary: str) -> bool:
    normalized = _clean_display_text(summary).lower()
    if not normalized or len(normalized) < 45:
        return True
    noise_tokens = ["location:", "phone:", "email:"]
    return any(token in normalized for token in noise_tokens)


def _resolve_application_profile(record) -> tuple[str, str, str, str, str, list[str]]:
    name = _clean_display_text(record.applicant_name)
    email = _clean_display_text(record.applicant_email)
    phone = _clean_display_text(record.applicant_phone)
    title = _clean_display_text(record.current_title)
    years = _clean_display_text(record.years_experience)
    skills = list(record.skills or [])
    summary = _clean_display_text(record.profile_summary)

    needs_backfill = (
        not title
        or not years
        or not skills
        or _is_low_quality_summary(summary)
        or not email
        or name.lower() in {"candidate", "test candidate"}
    )

    if not needs_backfill:
        return name, email, phone, title, years, skills, summary

    payload = application_store.get_resume_bytes(record.jd_id, record.application_id)
    if payload is None:
        return name, email, phone, title, years, skills, summary

    resume_bytes, _, filename = payload
    insights = resume_parser.parse(filename, resume_bytes)

    resolved_name = name
    if not resolved_name or resolved_name.lower() in {"candidate", "test candidate"}:
        resolved_name = insights.applicant_name or resolved_name

    resolved_email = email or insights.applicant_email
    resolved_phone = phone or insights.applicant_phone
    resolved_title = title or insights.current_title
    resolved_years = years or insights.years_experience
    resolved_skills = skills or insights.skills
    resolved_summary = summary
    if _is_low_quality_summary(summary):
        resolved_summary = _clean_display_text(insights.profile_summary)

    return (
        resolved_name,
        resolved_email,
        resolved_phone,
        resolved_title,
        resolved_years,
        resolved_skills,
        resolved_summary,
    )


def _calculate_match(
    jd_content: str,
    role_title: str,
    current_title: str,
    years_experience: str,
    skills: list[str],
    profile_summary: str,
) -> tuple[int, list[str], str]:
    jd_lower = jd_content.lower()
    matched_skills = [skill for skill in skills if skill.lower() in jd_lower]

    skill_score = min(60, len(matched_skills) * 12)

    required_years = _extract_years(jd_content) or 0
    candidate_years = _extract_years(years_experience) or 0
    if required_years > 0 and candidate_years > 0:
        if candidate_years >= required_years:
            experience_score = 20
        elif candidate_years >= max(1, required_years - 2):
            experience_score = 12
        else:
            experience_score = 6
    elif candidate_years > 0:
        experience_score = 10
    else:
        experience_score = 0

    title_score = 0
    role_tokens = {token for token in re.findall(r"[a-zA-Z]+", role_title.lower()) if len(token) >= 4}
    current_title_lower = current_title.lower()
    if current_title and any(token in current_title_lower for token in role_tokens):
        title_score = 15
    elif current_title:
        title_score = 6

    summary_bonus = 5 if profile_summary else 0
    total_score = min(100, skill_score + experience_score + title_score + summary_bonus)

    if matched_skills:
        top_skills = ", ".join(matched_skills[:3])
        sentence_one = f"Strong overlap with this JD on {top_skills}."
    elif skills:
        sentence_one = "Has transferable skills that can support core responsibilities for this role."
    else:
        sentence_one = "Profile has limited detectable skill keywords from the resume text."

    if candidate_years > 0 and required_years > 0:
        if candidate_years >= required_years:
            sentence_two = f"Experience level appears aligned ({candidate_years} years vs {required_years}+ years expected)."
        else:
            sentence_two = f"Experience appears slightly below target ({candidate_years} years vs {required_years}+ years expected)."
    elif current_title:
        sentence_two = f"Current role as {current_title} indicates relevant practical context."
    else:
        sentence_two = "Recommend manual review for deeper fit validation."

    strengths_summary = f"{sentence_one} {sentence_two}"
    return total_score, matched_skills, strengths_summary


@app.get("/", response_class=HTMLResponse)
def chat_ui() -> str:
    return _CHAT_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    # Load reference documents from GCS directory
    reference_context = ""
    if settings.reference_enabled:
        bucket_name = payload.reference_bucket or settings.reference_bucket
        prefix = payload.reference_prefix if payload.reference_prefix is not None else settings.reference_prefix
        if bucket_name:
            try:
                reference_context, _ = reference_store.build_reference_context(
                    bucket_name=bucket_name,
                    prefix=prefix,
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to load reference docs: {exc}") from exc

    # Load JD format template
    try:
        template_text = store.get_template("globe_telecom_default")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Rebuild typed history from the raw dicts the client sent back
    typed_history = [
        ChatMessage(role=m["role"], text=m["text"])
        for m in payload.history
        if m.get("role") in ("user", "model") and m.get("text")
    ]

    try:
        reply_text = chat_agent.reply(
            user_message=payload.message,
            history=typed_history,
            template_text=template_text,
            reference_context=reference_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat generation failed: {exc}") from exc

    # Try to save JD to GCS (if it looks like a JD was generated)
    if len(reply_text) > 200 and "##" in reply_text:  # Likely a generated JD
        try:
            cleaned_jd_content = _clean_jd_content(reply_text)
            role_title = _extract_role_title(payload.message, cleaned_jd_content)
            business_unit = "Globe Telecom"
            location = "Manila, Philippines"

            jd_store.save_jd(
                content=cleaned_jd_content,
                role_title=role_title,
                business_unit=business_unit,
                location=location,
                tags=["generated", "chat"]
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Warning: Could not save JD: {e}")

    updated_history = list(payload.history) + [
        {"role": "user",  "text": payload.message},
        {"role": "model", "text": reply_text},
    ]
    return ChatResponse(reply=reply_text, history=updated_history)


@app.post("/generate", response_model=GenerateJDResponse)
def generate_jd(payload: GenerateJDRequest) -> GenerateJDResponse:
    reference_context = ""
    reference_sources_used: list[str] = []
    if settings.reference_enabled and payload.use_reference_docs:
        bucket_name = payload.reference_bucket or settings.reference_bucket
        prefix = payload.reference_prefix if payload.reference_prefix is not None else settings.reference_prefix
        if bucket_name:
            try:
                reference_context, reference_sources_used = reference_store.build_reference_context(
                    bucket_name=bucket_name,
                    prefix=prefix,
                )
            except Exception as exc:  # pragma: no cover
                raise HTTPException(status_code=500, detail=f"Failed to load reference docs: {exc}") from exc

    try:
        template_text = store.get_template(payload.template_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    request = JDRequest(
        company_name=payload.company_name,
        business_unit=payload.business_unit,
        role_title=payload.role_title,
        location=payload.location,
        employment_type=payload.employment_type,
        seniority=payload.seniority,
        key_skills=payload.key_skills,
        responsibilities=payload.responsibilities,
        requirements=payload.requirements,
        language=payload.language,
    )
    try:
        jd_text = agent.generate(
            request=request,
            template_text=template_text,
            reference_context=reference_context,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"JD generation failed: {exc}") from exc

    return GenerateJDResponse(
        job_description=jd_text,
        reference_sources_used=reference_sources_used,
    )


@app.get("/gallery", response_class=HTMLResponse)
def gallery_ui() -> str:
    """Public gallery for viewing generated JDs"""
    return _GALLERY_HTML


@app.get("/recruiter", response_class=HTMLResponse)
def recruiter_ui() -> str:
    return _RECRUITER_HTML


@app.get("/api/jds", response_model=list[JDListItem])
def list_jds() -> list[JDListItem]:
    """
    Get list of all generated JDs
    
    Returns:
        List of JD metadata (sorted by most recent first)
    """
    jds = jd_store.list_jds()
    items: list[JDListItem] = []
    for jd in jds:
        content = jd_store.get_jd(jd.jd_id) or ""
        cleaned_content = _clean_jd_content(content)
        resolved_title = _extract_role_title(jd.role_title, cleaned_content) if cleaned_content else jd.role_title
        items.append(
            JDListItem(
                jd_id=jd.jd_id,
                role_title=resolved_title,
                business_unit=jd.business_unit,
                location=jd.location,
                created_at=jd.created_at,
                tags=jd.tags,
            )
        )
    return items


@app.get("/api/jds/{jd_id}", response_model=JDDetailResponse)
def get_jd_detail(jd_id: str) -> JDDetailResponse:
    """
    Get a specific JD by ID
    
    Args:
        jd_id: JD ID
        
    Returns:
        Full JD details including content
    """
    # Get metadata
    jds = jd_store.list_jds()
    metadata = next((jd for jd in jds if jd.jd_id == jd_id), None)
    
    if not metadata:
        raise HTTPException(status_code=404, detail=f"JD {jd_id} not found")
    
    # Get content
    content = jd_store.get_jd(jd_id)
    if not content:
        raise HTTPException(status_code=404, detail=f"JD {jd_id} content not found")

    cleaned_content = _clean_jd_content(content)
    resolved_title = _extract_role_title(metadata.role_title, cleaned_content)
    
    return JDDetailResponse(
        jd_id=metadata.jd_id,
        role_title=resolved_title,
        business_unit=metadata.business_unit,
        location=metadata.location,
        created_at=metadata.created_at,
        tags=metadata.tags,
        content=cleaned_content,
    )


@app.post("/api/jds/{jd_id}/apply", response_model=ApplicationResponse)
async def apply_to_jd(
    jd_id: str,
    applicant_name: str = Form(""),
    applicant_email: str = Form(""),
    applicant_phone: str = Form(""),
    resume_file: UploadFile = File(...),
) -> ApplicationResponse:
    jds = jd_store.list_jds()
    if not any(jd.jd_id == jd_id for jd in jds):
        raise HTTPException(status_code=404, detail=f"JD {jd_id} not found")

    _validate_resume_upload(resume_file)
    resume_bytes = await resume_file.read()
    if not resume_bytes:
        raise HTTPException(status_code=400, detail="Uploaded resume file is empty")

    if len(resume_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file must be 10MB or smaller")

    try:
        insights = resume_parser.parse(resume_file.filename or "resume.pdf", resume_bytes)
        resolved_name = applicant_name.strip() or insights.applicant_name or "Candidate"
        resolved_email = applicant_email.strip() or insights.applicant_email
        resolved_phone = applicant_phone.strip() or insights.applicant_phone

        record = application_store.save_application(
            jd_id=jd_id,
            applicant_name=resolved_name,
            applicant_email=resolved_email,
            applicant_phone=resolved_phone,
            current_title=insights.current_title,
            years_experience=insights.years_experience,
            skills=insights.skills,
            profile_summary=insights.profile_summary,
            resume_filename=resume_file.filename or "resume.pdf",
            resume_content_type=resume_file.content_type or "application/octet-stream",
            resume_bytes=resume_bytes,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload application: {exc}") from exc

    return ApplicationResponse(
        application_id=record.application_id,
        message="Application submitted successfully",
    )


@app.get("/api/jds/{jd_id}/applications", response_model=list[ApplicationListItem])
def list_applications_for_jd(jd_id: str) -> list[ApplicationListItem]:
    jds = jd_store.list_jds()
    if not any(jd.jd_id == jd_id for jd in jds):
        raise HTTPException(status_code=404, detail=f"JD {jd_id} not found")

    records = application_store.list_applications(jd_id)
    jd_content = jd_store.get_jd(jd_id) or ""
    metadata = next((jd for jd in jds if jd.jd_id == jd_id), None)
    role_title = metadata.role_title
    enriched = []
    for record in records:
        (
            applicant_name,
            applicant_email,
            applicant_phone,
            current_title,
            years_experience,
            skills,
            profile_summary,
        ) = _resolve_application_profile(record)

        match_score, matched_skills, strengths_summary = _calculate_match(
            jd_content=jd_content,
            role_title=role_title,
            current_title=current_title,
            years_experience=years_experience,
            skills=skills,
            profile_summary=profile_summary,
        )
        enriched.append(
            ApplicationListItem(
                application_id=record.application_id,
                jd_id=record.jd_id,
                applicant_name=applicant_name,
                applicant_email=applicant_email,
                applicant_phone=applicant_phone,
                match_score=match_score,
                matched_skills=matched_skills,
                strengths_summary=strengths_summary,
                current_title=current_title,
                years_experience=years_experience,
                skills=skills,
                profile_summary=profile_summary,
                resume_filename=record.resume_filename,
                resume_content_type=record.resume_content_type,
                uploaded_at=record.uploaded_at,
                resume_download_url=f"/api/jds/{record.jd_id}/applications/{record.application_id}/resume",
            )
        )

    enriched.sort(key=lambda item: (item.match_score, item.uploaded_at), reverse=True)
    return enriched


@app.get("/api/applications", response_model=list[ApplicationListItem])
def list_all_applications() -> list[ApplicationListItem]:
    records = application_store.list_applications()
    jd_metadata = {jd.jd_id: jd for jd in jd_store.list_jds()}
    jd_content_cache: dict[str, str] = {}

    items: list[ApplicationListItem] = []
    for record in records:
        (
            applicant_name,
            applicant_email,
            applicant_phone,
            current_title,
            years_experience,
            skills,
            profile_summary,
        ) = _resolve_application_profile(record)

        jd_content = jd_content_cache.get(record.jd_id)
        if jd_content is None:
            jd_content = jd_store.get_jd(record.jd_id) or ""
            jd_content_cache[record.jd_id] = jd_content

        role_title = jd_metadata.get(record.jd_id).role_title if jd_metadata.get(record.jd_id) else ""
        match_score, matched_skills, strengths_summary = _calculate_match(
            jd_content=jd_content,
            role_title=role_title,
            current_title=current_title,
            years_experience=years_experience,
            skills=skills,
            profile_summary=profile_summary,
        )
        items.append(
            ApplicationListItem(
                application_id=record.application_id,
                jd_id=record.jd_id,
                applicant_name=applicant_name,
                applicant_email=applicant_email,
                applicant_phone=applicant_phone,
                match_score=match_score,
                matched_skills=matched_skills,
                strengths_summary=strengths_summary,
                current_title=current_title,
                years_experience=years_experience,
                skills=skills,
                profile_summary=profile_summary,
                resume_filename=record.resume_filename,
                resume_content_type=record.resume_content_type,
                uploaded_at=record.uploaded_at,
                resume_download_url=f"/api/jds/{record.jd_id}/applications/{record.application_id}/resume",
            )
        )

    items.sort(key=lambda item: (item.match_score, item.uploaded_at), reverse=True)
    return items


@app.get("/api/jds/{jd_id}/applications/{application_id}/resume")
def download_application_resume(jd_id: str, application_id: str) -> StreamingResponse:
    payload = application_store.get_resume_bytes(jd_id, application_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Resume file not found")

    content, content_type, filename = payload
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([content]), media_type=content_type, headers=headers)
