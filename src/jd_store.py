"""
JD Storage Layer - Manage job description persistence in GCS
"""

import json
import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict
from google.cloud import storage
import subprocess


@dataclass
class JDMetadata:
    """JD metadata for indexing and display"""
    jd_id: str
    role_title: str
    business_unit: str
    location: str
    created_at: str
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class JDStore:
    """Store and retrieve job descriptions in GCS"""

    def __init__(self, bucket_name: str, prefix: str = "generated-jds"):
        """
        Initialize JD Store
        
        Args:
            bucket_name: GCS bucket name (e.g., 'jackytest007')
            prefix: GCS prefix for storing JDs (default: 'generated-jds')
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.index_path = f"{prefix}/.index.json"
        self.storage_client = None
        self._init_storage()

    def _init_storage(self):
        """Initialize GCS client"""
        try:
            self.storage_client = storage.Client()
        except Exception as e:
            print(f"Warning: Could not initialize GCS client: {e}")
            self.storage_client = None

    def _save_via_gcloud(self, blob_path: str, content: str) -> bool:
        """Fallback: save via gcloud CLI"""
        try:
            gcs_path = f"gs://{self.bucket_name}/{blob_path}"
            result = subprocess.run(
                ["gcloud", "storage", "cp", "-", gcs_path],
                input=content.encode(),
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error saving via gcloud: {e}")
            return False

    def _load_via_gcloud(self, blob_path: str) -> Optional[str]:
        """Fallback: load via gcloud CLI"""
        try:
            gcs_path = f"gs://{self.bucket_name}/{blob_path}"
            result = subprocess.run(
                ["gcloud", "storage", "cat", gcs_path],
                capture_output=True,
                timeout=30,
                text=True
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            print(f"Error loading via gcloud: {e}")
            return None

    def save_jd(
        self,
        content: str,
        role_title: str,
        business_unit: str,
        location: str,
        tags: List[str] = None
    ) -> Optional[str]:
        """
        Save a JD to GCS and update index
        
        Args:
            content: JD markdown content
            role_title: Job role title
            business_unit: Business unit
            location: Job location
            tags: Optional tags for categorization
            
        Returns:
            JD ID if successful, None otherwise
        """
        jd_id = str(uuid.uuid4())[:8]
        blob_path = f"{self.prefix}/jd-{jd_id}.md"
        
        try:
            # Save JD content
            if self.storage_client:
                bucket = self.storage_client.bucket(self.bucket_name)
                blob = bucket.blob(blob_path)
                blob.upload_from_string(content, content_type="text/markdown")
            else:
                # Fallback to gcloud CLI
                if not self._save_via_gcloud(blob_path, content):
                    return None
            
            # Update index
            metadata = JDMetadata(
                jd_id=jd_id,
                role_title=role_title,
                business_unit=business_unit,
                location=location,
                created_at=datetime.utcnow().isoformat(),
                tags=tags or []
            )
            self._update_index(metadata)
            
            return jd_id
            
        except Exception as e:
            print(f"Error saving JD: {e}")
            return None

    def get_jd(self, jd_id: str) -> Optional[str]:
        """
        Retrieve a JD from GCS
        
        Args:
            jd_id: JD ID
            
        Returns:
            JD markdown content if found, None otherwise
        """
        blob_path = f"{self.prefix}/jd-{jd_id}.md"
        
        try:
            if self.storage_client:
                bucket = self.storage_client.bucket(self.bucket_name)
                blob = bucket.blob(blob_path)
                if blob.exists():
                    return blob.download_as_string().decode()
            else:
                # Fallback to gcloud CLI
                return self._load_via_gcloud(blob_path)
                
            return None
        except Exception as e:
            print(f"Error getting JD: {e}")
            return None

    def _update_index(self, metadata: JDMetadata):
        """Update the central JD index"""
        try:
            # Load existing index
            index = {}
            if self.storage_client:
                bucket = self.storage_client.bucket(self.bucket_name)
                index_blob = bucket.blob(self.index_path)
                if index_blob.exists():
                    index = json.loads(index_blob.download_as_string())
            else:
                # Fallback
                index_content = self._load_via_gcloud(self.index_path)
                if index_content:
                    index = json.loads(index_content)
            
            # Add/update entry
            index[metadata.jd_id] = asdict(metadata)
            
            # Save updated index
            index_json = json.dumps(index, indent=2, ensure_ascii=False)
            if self.storage_client:
                bucket = self.storage_client.bucket(self.bucket_name)
                index_blob = bucket.blob(self.index_path)
                index_blob.upload_from_string(index_json, content_type="application/json")
            else:
                self._save_via_gcloud(self.index_path, index_json)
                
        except Exception as e:
            print(f"Warning: Could not update index: {e}")

    def list_jds(self) -> List[JDMetadata]:
        """
        List all JDs with metadata
        
        Returns:
            List of JDMetadata objects
        """
        try:
            # Load index
            index = {}
            if self.storage_client:
                bucket = self.storage_client.bucket(self.bucket_name)
                index_blob = bucket.blob(self.index_path)
                if index_blob.exists():
                    index = json.loads(index_blob.download_as_string())
            else:
                # Fallback
                index_content = self._load_via_gcloud(self.index_path)
                if index_content:
                    index = json.loads(index_content)
            
            # Convert to metadata objects, sorted by created_at (most recent first)
            jds = [JDMetadata(**data) for data in index.values()]
            jds.sort(key=lambda x: x.created_at, reverse=True)
            return jds
            
        except Exception as e:
            print(f"Error listing JDs: {e}")
            return []
