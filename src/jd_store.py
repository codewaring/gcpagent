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
        """Get demo JD content for testing/demo purposes"""
        demo_content = {
            "demo001": """# Software Engineer - Platform Engineering

We are seeking a talented Software Engineer to join our Platform Engineering team. You will work on building scalable infrastructure and tools that enable our organization to deliver exceptional products.

## Key Responsibilities
- Design and develop robust software solutions
- Collaborate with cross-functional teams on infrastructure
- Build and maintain scalable systems
- Participate in architectural decisions
- Contribute to open source initiatives

## Required Qualifications
- 3+ years of software development experience
- Proficiency in at least one programming language (Python, Go, Java)
- Understanding of distributed systems
- Strong problem-solving skills
- Excellent communication abilities

## Preferred Qualifications
- Experience with Kubernetes and containerization
- Knowledge of cloud platforms (GCP, AWS)
- Familiarity with microservices architecture
- Open source contributions experience

## Compensation & Benefits
- Competitive salary and benefits package
- Professional development opportunities
- Flexible work arrangements
- Health insurance coverage
- Technology allowance
""",
            "demo002": """# Senior Database Administrator - Cloud Infrastructure

Join our Cloud Infrastructure team as a Senior DBA. You will manage critical database systems and optimize performance across our cloud infrastructure. This is a leadership position where you'll mentor junior DBAs and drive database excellence.

## Key Responsibilities
- Design and optimize database architectures
- Manage and maintain multi-cloud database systems
- Implement backup and disaster recovery strategies
- Monitor system health and performance
- Lead database security initiatives
- Mentor junior database administrators

## Required Qualifications
- 7+ years of database administration experience
- Strong expertise in SQL and relational databases
- Experience with cloud-managed databases
- Deep knowledge of database security
- Proven problem-solving and analytical skills

## Preferred Qualifications
- PostgreSQL/MySQL expertise
- Cloud platform database certifications (GCP, AWS)
- Automation and scripting skills  
- Performance tuning expertise
- High availability architecture knowledge

## Compensation & Benefits
- Highly competitive compensation package
- Healthcare and wellness benefits
- Career advancement opportunities
- Technical training and certification support
- Flexible remote work options
""",
            "demo003": """# DevOps Engineer - Operations

Help us build and maintain the infrastructure that powers our operations. As a DevOps Engineer, you'll work on CI/CD pipelines, containerization, and cloud infrastructure. You'll play a critical role in enabling development teams to ship code reliably and safely.

## Key Responsibilities
- Design and implement comprehensive CI/CD pipelines
- Manage containerized applications and orchestration
- Implement infrastructure as code across cloud platforms
- Monitor and troubleshoot production systems
- Establish SLOs and reliability practices
- Collaborate with development and security teams

## Required Qualifications
- 4+ years of DevOps/SRE/Infrastructure Engineering experience
- Hands-on experience with Docker and Kubernetes
- Knowledge of cloud platforms (GCP, AWS, Azure)
- Strong scripting and automation skills
- Linux system administration expertise

## Preferred Qualifications
- Terraform or CloudFormation infrastructure as code
- Prometheus/Grafana monitoring and observability
- GitLab CI or GitHub Actions experience
- Security and compliance best practices
- Distributed systems troubleshooting

## Compensation & Benefits
- Competitive salary and stock options
- Comprehensive health and wellness programs
- Technology allowance and training budget
- Remote work flexibility
- Collaborative and innovative team culture
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
        """Get demo JD data for testing/demo purposes"""
        return {
            "demo001": {
                "jd_id": "demo001",
                "role_title": "Software Engineer",
                "business_unit": "Platform Engineering",
                "location": "Manila, Philippines",
                "created_at": "2026-03-18T12:00:00.000000",
                "tags": ["demo", "engineering"]
            },
            "demo002": {
                "jd_id": "demo002",
                "role_title": "Senior Database Administrator",
                "business_unit": "Cloud Infrastructure",
                "location": "Manila, Philippines",
                "created_at": "2026-03-18T12:05:00.000000",
                "tags": ["demo", "database"]
            },
            "demo003": {
                "jd_id": "demo003",
                "role_title": "DevOps Engineer",
                "business_unit": "Operations",
                "location": "Manila, Philippines",
                "created_at": "2026-03-18T12:10:00.000000",
                "tags": ["demo", "devops"]
            }
        }
