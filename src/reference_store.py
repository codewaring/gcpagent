import io
import subprocess
from dataclasses import dataclass

from google.cloud import storage
from pypdf import PdfReader


@dataclass
class ReferenceDoc:
    path: str
    content: str


class GCSReferenceStore:
    def __init__(self, max_files: int, max_chars_per_file: int) -> None:
        self.client = storage.Client()
        self.max_files = max_files
        self.max_chars_per_file = max_chars_per_file

    def _extract_text(self, blob_name: str, payload: bytes) -> str:
        if blob_name.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(payload))
            chunks: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    chunks.append(page_text.strip())
                if sum(len(c) for c in chunks) >= self.max_chars_per_file:
                    break
            return "\n".join(chunks)[: self.max_chars_per_file]

        if blob_name.lower().endswith((".txt", ".md")):
            return payload.decode("utf-8", errors="ignore")[: self.max_chars_per_file]

        # Ignore binary types that are not currently handled.
        return ""

    def _list_blob_names_sdk(self, bucket_name: str, prefix: str) -> list[str]:
        bucket = self.client.bucket(bucket_name)
        blobs = self.client.list_blobs(bucket, prefix=prefix)
        names: list[str] = []
        for blob in blobs:
            if blob.name.endswith("/"):
                continue
            names.append(blob.name)
            if len(names) >= self.max_files:
                break
        return names

    def _list_blob_names_gcloud(self, bucket_name: str, prefix: str) -> list[str]:
        target = f"gs://{bucket_name}/{prefix}" if prefix else f"gs://{bucket_name}"
        result = subprocess.run(
            ["gcloud", "storage", "ls", "--recursive", target],
            check=True,
            capture_output=True,
            text=True,
        )
        names: list[str] = []
        for line in result.stdout.splitlines():
            item = line.strip()
            if not item.startswith(f"gs://{bucket_name}/"):
                continue
            if item.endswith(":"):
                continue
            names.append(item.replace(f"gs://{bucket_name}/", "", 1))
            if len(names) >= self.max_files:
                break
        return names

    def _download_bytes_sdk(self, bucket_name: str, blob_name: str) -> bytes:
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    def _download_bytes_gcloud(self, bucket_name: str, blob_name: str) -> bytes:
        path = f"gs://{bucket_name}/{blob_name}"
        result = subprocess.run(
            ["gcloud", "storage", "cat", path],
            check=True,
            capture_output=True,
            text=False,
        )
        return result.stdout

    def load_references(self, bucket_name: str, prefix: str = "") -> list[ReferenceDoc]:
        try:
            blob_names = self._list_blob_names_sdk(bucket_name=bucket_name, prefix=prefix)
            use_sdk_download = True
        except Exception:
            blob_names = self._list_blob_names_gcloud(bucket_name=bucket_name, prefix=prefix)
            use_sdk_download = False

        docs: list[ReferenceDoc] = []
        for blob_name in blob_names:
            raw = self._download_bytes_sdk(bucket_name, blob_name) if use_sdk_download else self._download_bytes_gcloud(bucket_name, blob_name)
            text = self._extract_text(blob_name, raw).strip()
            if not text:
                continue
            docs.append(ReferenceDoc(path=f"gs://{bucket_name}/{blob_name}", content=text))
            if len(docs) >= self.max_files:
                break

        return docs

    def build_reference_context(self, bucket_name: str, prefix: str = "") -> tuple[str, list[str]]:
        docs = self.load_references(bucket_name=bucket_name, prefix=prefix)
        if not docs:
            return "", []

        context_chunks: list[str] = []
        source_paths: list[str] = []
        for item in docs:
            source_paths.append(item.path)
            context_chunks.append(f"Source: {item.path}\n{item.content}")

        return "\n\n".join(context_chunks), source_paths
