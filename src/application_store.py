import json
import hashlib
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage


@dataclass(frozen=True)
class ApplicationRecord:
    application_id: str
    jd_id: str
    applicant_name: str
    applicant_email: str
    applicant_phone: str
    current_title: str
    years_experience: str
    skills: list[str]
    profile_summary: str
    resume_fingerprint: str
    resume_filename: str
    resume_content_type: str
    uploaded_at: str
    resume_blob_path: str
    metadata_blob_path: str


class ApplicationStore:
    def __init__(self, bucket_name: str, prefix: str = "job-applications") -> None:
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.storage_client = None
        try:
            self.storage_client = storage.Client()
        except Exception as exc:
            print(f"Warning: Could not initialize application storage client: {exc}")

    def save_application(
        self,
        jd_id: str,
        applicant_name: str,
        applicant_email: str,
        applicant_phone: str,
        current_title: str,
        years_experience: str,
        skills: list[str],
        profile_summary: str,
        resume_filename: str,
        resume_content_type: str,
        resume_bytes: bytes,
    ) -> ApplicationRecord:
        resume_fingerprint = self._compute_fingerprint(resume_bytes)
        application_id = uuid.uuid4().hex[:10]
        uploaded_at = datetime.now(timezone.utc).isoformat()
        safe_name = self._slugify(applicant_name) or "candidate"
        safe_filename = self._safe_filename(resume_filename)
        base_path = f"{self.prefix}/{jd_id}/{uploaded_at[:10]}/{application_id}_{safe_name}"
        resume_path = f"{base_path}/{safe_filename}"
        metadata_path = f"{base_path}/application.json"

        record = ApplicationRecord(
            application_id=application_id,
            jd_id=jd_id,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
            applicant_phone=applicant_phone,
            current_title=current_title,
            years_experience=years_experience,
            skills=skills,
            profile_summary=profile_summary,
            resume_fingerprint=resume_fingerprint,
            resume_filename=safe_filename,
            resume_content_type=resume_content_type,
            uploaded_at=uploaded_at,
            resume_blob_path=resume_path,
            metadata_blob_path=metadata_path,
        )

        metadata_bytes = json.dumps(
            {
                "application_id": record.application_id,
                "jd_id": record.jd_id,
                "applicant_name": record.applicant_name,
                "applicant_email": record.applicant_email,
                "applicant_phone": record.applicant_phone,
                "current_title": record.current_title,
                "years_experience": record.years_experience,
                "skills": record.skills,
                "profile_summary": record.profile_summary,
                "resume_fingerprint": record.resume_fingerprint,
                "resume_filename": record.resume_filename,
                "resume_content_type": record.resume_content_type,
                "uploaded_at": record.uploaded_at,
                "resume_blob_path": record.resume_blob_path,
                "metadata_blob_path": record.metadata_blob_path,
            },
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")

        self._upload_bytes(resume_path, resume_bytes, resume_content_type)
        self._upload_bytes(metadata_path, metadata_bytes, "application/json")
        return record

    def list_applications(self, jd_id: str | None = None) -> list[ApplicationRecord]:
        prefix = self.prefix
        if jd_id:
            prefix = f"{prefix}/{jd_id}"

        metadata_paths = self._list_metadata_paths(prefix)
        records: list[ApplicationRecord] = []
        for metadata_path in metadata_paths:
            payload = self._download_text(metadata_path)
            if not payload:
                continue
            try:
                data = json.loads(payload)
                metadata_blob_path = data.get("metadata_blob_path", metadata_path)
                resume_blob_path = data.get(
                    "resume_blob_path",
                    f"{metadata_path.rsplit('/', 1)[0]}/{data['resume_filename']}",
                )
                records.append(
                    ApplicationRecord(
                        application_id=data["application_id"],
                        jd_id=data["jd_id"],
                        applicant_name=data["applicant_name"],
                        applicant_email=data["applicant_email"],
                        applicant_phone=data.get("applicant_phone", ""),
                        current_title=data.get("current_title", ""),
                        years_experience=data.get("years_experience", ""),
                        skills=data.get("skills", []),
                        profile_summary=data.get("profile_summary", ""),
                        resume_fingerprint=data.get("resume_fingerprint", ""),
                        resume_filename=data["resume_filename"],
                        resume_content_type=data.get("resume_content_type", "application/octet-stream"),
                        uploaded_at=data["uploaded_at"],
                        resume_blob_path=resume_blob_path,
                        metadata_blob_path=metadata_blob_path,
                    )
                )
            except Exception as exc:
                print(f"Warning: Could not parse application metadata {metadata_path}: {exc}")
        records.sort(key=lambda item: item.uploaded_at, reverse=True)
        return records

    def find_duplicate_application(
        self,
        jd_id: str,
        resume_bytes: bytes,
        applicant_email: str,
    ) -> ApplicationRecord | None:
        fingerprint = self._compute_fingerprint(resume_bytes)
        normalized_email = applicant_email.strip().lower()

        for record in self.list_applications(jd_id):
            if record.resume_fingerprint and record.resume_fingerprint == fingerprint:
                return record

            if not record.resume_fingerprint:
                existing_resume = self._download_bytes(record.resume_blob_path)
                if existing_resume and self._compute_fingerprint(existing_resume) == fingerprint:
                    return record

            if normalized_email and record.applicant_email.strip().lower() == normalized_email:
                return record
        return None

    def get_resume_bytes(self, jd_id: str, application_id: str) -> tuple[bytes, str, str] | None:
        record = next(
            (item for item in self.list_applications(jd_id) if item.application_id == application_id),
            None,
        )
        if not record:
            return None
        payload = self._download_bytes(record.resume_blob_path)
        if payload is None:
            return None
        return payload, record.resume_content_type, record.resume_filename

    def _upload_bytes(self, blob_path: str, payload: bytes, content_type: str) -> None:
        if self.storage_client:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(payload, content_type=content_type)
            return

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(payload)
            temp_path = Path(temp_file.name)
        try:
            gcs_path = f"gs://{self.bucket_name}/{blob_path}"
            result = subprocess.run(
                ["gcloud", "storage", "cp", str(temp_path), gcs_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud upload failed")
        finally:
            temp_path.unlink(missing_ok=True)

    def _download_text(self, blob_path: str) -> str | None:
        payload = self._download_bytes(blob_path)
        if payload is None:
            return None
        return payload.decode("utf-8")

    def _download_bytes(self, blob_path: str) -> bytes | None:
        if self.storage_client:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_path)
            if not blob.exists():
                return None
            return blob.download_as_bytes()

        gcs_path = f"gs://{self.bucket_name}/{blob_path}"
        result = subprocess.run(
            ["gcloud", "storage", "cat", gcs_path],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            return None
        return result.stdout

    def _list_metadata_paths(self, prefix: str) -> list[str]:
        if self.storage_client:
            iterator = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
            return sorted(blob.name for blob in iterator if blob.name.endswith("application.json"))

        gcs_path = f"gs://{self.bucket_name}/{prefix}/**"
        result = subprocess.run(
            ["gcloud", "storage", "ls", "--recursive", gcs_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return []
        paths: list[str] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.endswith("application.json") and stripped.startswith(f"gs://{self.bucket_name}/"):
                paths.append(stripped.replace(f"gs://{self.bucket_name}/", "", 1))
        return sorted(paths)

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @staticmethod
    def _safe_filename(filename: str) -> str:
        path = Path(filename)
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._") or "resume"
        suffix = re.sub(r"[^A-Za-z0-9.]", "", path.suffix.lower()) or ".bin"
        return f"{stem}{suffix}"

    @staticmethod
    def _compute_fingerprint(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()