from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .chat_agent import ChatAgent, ChatMessage
from .config import get_settings
from .jd_agent import JDAgent, JDRequest
from .reference_store import GCSReferenceStore
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
_CHAT_HTML = (Path(__file__).parent / "chat.html").read_text(encoding="utf-8")
_GALLERY_HTML = (Path(__file__).parent / "gallery.html").read_text(encoding="utf-8")


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
            # Extract job title and business unit from message or use defaults
            role_title = "Generated Role"
            business_unit = "Globe Telecom"
            location = "Manila, Philippines"
            
            # Simple heuristic: look for role/title mentions in user message
            message_lower = payload.message.lower()
            if "database" in message_lower:
                role_title = "Database Administrator"
            elif "engineer" in message_lower or "developer" in message_lower:
                if "senior" in message_lower:
                    role_title = "Senior Engineer"
                elif "junior" in message_lower:
                    role_title = "Junior Engineer"
                else:
                    role_title = "Software Engineer"
            elif "data" in message_lower:
                role_title = "Data Specialist"
            elif "network" in message_lower:
                role_title = "Network Engineer"
            elif "manager" in message_lower or "lead" in message_lower:
                role_title = "Team Lead"
            
            # Extract from reply if available
            for line in reply_text.split("\n")[:5]:
                if "job title" in line.lower() or "position" in line.lower():
                    role_title = line.split(":")[-1].strip().strip("#").strip()
                    break
            
            jd_store.save_jd(
                content=reply_text,
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


@app.get("/api/jds", response_model=list[JDListItem])
def list_jds() -> list[JDListItem]:
    """
    Get list of all generated JDs
    
    Returns:
        List of JD metadata (sorted by most recent first)
    """
    jds = jd_store.list_jds()
    return [
        JDListItem(
            jd_id=jd.jd_id,
            role_title=jd.role_title,
            business_unit=jd.business_unit,
            location=jd.location,
            created_at=jd.created_at,
            tags=jd.tags,
        )
        for jd in jds
    ]


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
    
    return JDDetailResponse(
        jd_id=metadata.jd_id,
        role_title=metadata.role_title,
        business_unit=metadata.business_unit,
        location=metadata.location,
        created_at=metadata.created_at,
        tags=metadata.tags,
        content=content,
    )
