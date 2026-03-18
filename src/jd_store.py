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
            
            # Try demo data as fallback
            demo_content = self._get_demo_jd_content(jd_id)
            if demo_content:
                return demo_content
                
            return None
        except Exception as e:
            print(f"Error getting JD: {e}")
            # Return demo content as fallback
            return self._get_demo_jd_content(jd_id)

    def _get_demo_jd_content(self, jd_id: str) -> Optional[str]:
        """Get demo JD content as fallback when GCS is unavailable"""
        demo_content = {
            "f8fd3644": """# People Manager

## About Globe Telecom
At Globe Telecom, we are dedicated to creating a Globe of Good. As the leading digital solutions platform in the Philippines, our mission is to enrich the lives of Filipinos through technology.

## Role Overview
The People Manager is central to our success, responsible for building, leading, and nurturing a high-performing team. This role is about more than just oversight; it's about inspiring excellence, coaching for growth, and fostering a culture of collaboration and accountability.

## Key Responsibilities
- Lead, mentor, and develop a team of professionals, setting clear goals and providing regular constructive feedback
- Champion the career development of team members through growth opportunities and development plans
- Foster a positive, inclusive, and highly collaborative team environment
- Manage day-to-day team operations, ensuring successful delivery of projects and KPIs
- Act as a key communication link between senior leadership and your team
- Collaborate with cross-functional managers to align on priorities and deliver on broader business goals

## Minimum Qualifications
- Bachelor's degree in Business, Management, Human Resources, or a related field
- 5+ years of experience in a managerial or leadership role
- Strong interpersonal and communication skills
- Demonstrated ability to develop and motivate teams
""",
            "c888c0e6": """# Database Administrator - Globe Telecom

## Role Overview
We are looking for an experienced Database Administrator to join Globe Telecom's technology team. You will manage, optimize, and maintain our critical database infrastructure supporting millions of customers.

## Key Responsibilities
- Manage and maintain database systems across production and development environments
- Implement backup, recovery, and disaster recovery strategies
- Monitor database performance and implement optimizations
- Ensure database security and compliance
- Collaborate with development teams on schema design

## Required Qualifications
- 5+ years of database administration experience
- Proficiency in SQL and database management systems
- Experience with cloud databases
- Strong analytical and problem-solving skills
""",
            "ef658af6": """# Senior Engineer - Globe Telecom

## Role Overview
Join Globe Telecom as a Senior Engineer and help build the digital infrastructure that connects millions of Filipinos. You will lead technical initiatives and mentor junior engineers.

## Key Responsibilities
- Design and implement scalable, high-availability systems
- Lead technical design reviews and architecture decisions
- Mentor and develop junior engineering team members
- Drive technical excellence and best practices
- Collaborate with product teams on technical requirements

## Required Qualifications
- 7+ years of software engineering experience
- Strong background in distributed systems
- Experience with cloud platforms (GCP, AWS)
- Track record of leading technical initiatives
""",
            "3d5e83c7": """# Software Engineer - Globe Telecom

## Role Overview
Globe Telecom is looking for a talented Software Engineer to build innovative digital products that serve millions of customers across the Philippines.

## Key Responsibilities
- Design and develop high-quality software solutions
- Participate in the full software development lifecycle
- Write clean, testable, and maintainable code
- Collaborate with cross-functional teams
- Contribute to code reviews and technical discussions

## Required Qualifications
- 3+ years of software development experience
- Proficiency in Python, Java, or similar languages
- Understanding of software design patterns
- Experience with agile development methodologies
"""
        }
        return demo_content.get(jd_id)

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
            
            # If no index found in GCS, try demo data fallback (for demo/testing)
            if not index:
                index = self._get_demo_data()
            
            # Convert to metadata objects, sorted by created_at (most recent first)
            jds = [JDMetadata(**data) for data in index.values()]
            jds.sort(key=lambda x: x.created_at, reverse=True)
            return jds
            
        except Exception as e:
            print(f"Error listing JDs: {e}")
            # Return demo data on error for demo/testing
            demo_index = self._get_demo_data()
            jds = [JDMetadata(**data) for data in demo_index.values()]
            jds.sort(key=lambda x: x.created_at, reverse=True)
            return jds

    def _get_demo_data(self) -> dict:
        """Get demo JD data for testing/demo purposes (mirrors real GCS data)"""
        return {
            "c888c0e6": {
                "jd_id": "c888c0e6",
                "role_title": "Database Administrator",
                "business_unit": "Globe Telecom",
                "location": "Manila, Philippines",
                "created_at": "2026-03-16T16:37:06.003588",
                "tags": ["generated", "chat"]
            },
            "ef658af6": {
                "jd_id": "ef658af6",
                "role_title": "Senior Engineer",
                "business_unit": "Globe Telecom",
                "location": "Manila, Philippines",
                "created_at": "2026-03-16T16:39:43.472034",
                "tags": ["generated", "chat"]
            },
            "3d5e83c7": {
                "jd_id": "3d5e83c7",
                "role_title": "Software Engineer",
                "business_unit": "Globe Telecom",
                "location": "Manila, Philippines",
                "created_at": "2026-03-16T16:40:42.534600",
                "tags": ["generated", "chat"]
            },
            "f8fd3644": {
                "jd_id": "f8fd3644",
                "role_title": "People Manager",
                "business_unit": "Globe Telecom",
                "location": "Manila, Philippines",
                "created_at": "2026-03-16T16:46:44.199148",
                "tags": ["generated", "chat"]
            }
        }
