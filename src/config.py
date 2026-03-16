import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project_id: str
    location: str
    model_name: str
    template_dir: str
    reference_bucket: str
    reference_prefix: str
    reference_enabled: bool
    reference_max_files: int
    reference_max_chars_per_file: int


def _as_bool(value: str, default: bool) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def get_settings() -> Settings:
    return Settings(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "asia-southeast1"),
        model_name=os.getenv("MODEL_NAME", "gemini-2.5-pro"),
        template_dir=os.getenv("TEMPLATE_DIR", "templates"),
        reference_bucket=os.getenv("REFERENCE_BUCKET", ""),
        reference_prefix=os.getenv("REFERENCE_PREFIX", ""),
        reference_enabled=_as_bool(os.getenv("REFERENCE_ENABLED", "true"), True),
        reference_max_files=int(os.getenv("REFERENCE_MAX_FILES", "20")),
        reference_max_chars_per_file=int(os.getenv("REFERENCE_MAX_CHARS_PER_FILE", "6000")),
    )
