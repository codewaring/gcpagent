from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader


@dataclass(frozen=True)
class ResumeInsights:
    applicant_name: str
    applicant_email: str
    applicant_phone: str
    current_title: str
    years_experience: str
    skills: list[str]
    profile_summary: str


class ResumeParser:
    _SKILL_KEYWORDS = [
        ("python", "Python"),
        ("java", "Java"),
        ("sql", "SQL"),
        ("aws", "AWS"),
        ("gcp", "GCP"),
        ("azure", "Azure"),
        ("docker", "Docker"),
        ("kubernetes", "Kubernetes"),
        ("terraform", "Terraform"),
        ("ansible", "Ansible"),
        ("linux", "Linux"),
        ("networking", "Networking"),
        ("cisco", "Cisco"),
        ("juniper", "Juniper"),
        ("cloud", "Cloud"),
        ("data engineering", "Data Engineering"),
        ("data architecture", "Data Architecture"),
        ("etl", "ETL"),
        ("power bi", "Power BI"),
        ("tableau", "Tableau"),
        ("project management", "Project Management"),
        ("people management", "People Management"),
        ("stakeholder management", "Stakeholder Management"),
        ("agile", "Agile"),
        ("scrum", "Scrum"),
        ("devops", "DevOps"),
        ("cybersecurity", "Cybersecurity"),
        ("incident management", "Incident Management"),
        ("telecommunications", "Telecommunications"),
        ("salesforce", "Salesforce"),
        ("sap", "SAP"),
    ]
    _SECTION_HINTS = {
        "resume",
        "curriculum vitae",
        "summary",
        "profile",
        "experience",
        "employment",
        "education",
        "skills",
        "certifications",
        "projects",
        "references",
        "contact",
    }

    def parse(self, filename: str, payload: bytes) -> ResumeInsights:
        try:
            text = self._extract_text(filename, payload)
        except Exception:
            text = payload.decode("utf-8", errors="ignore") or payload.decode("latin-1", errors="ignore")
        compact_text = self._normalize_text(text)
        email = self._extract_email(compact_text)
        phone = self._extract_phone(compact_text)
        name = self._extract_name(compact_text, filename, email)
        title = self._extract_title(compact_text, name)
        years_experience = self._extract_years_experience(compact_text)
        skills = self._extract_skills(compact_text)
        summary = self._extract_summary(compact_text, name, title)
        return ResumeInsights(
            applicant_name=name,
            applicant_email=email,
            applicant_phone=phone,
            current_title=title,
            years_experience=years_experience,
            skills=skills,
            profile_summary=summary,
        )

    def _extract_text(self, filename: str, payload: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_text(payload)
        if suffix == ".docx":
            return self._extract_docx_text(payload)
        return payload.decode("utf-8", errors="ignore") or payload.decode("latin-1", errors="ignore")

    @staticmethod
    def _extract_pdf_text(payload: bytes) -> str:
        reader = PdfReader(BytesIO(payload))
        pages: list[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)

    @staticmethod
    def _extract_docx_text(payload: bytes) -> str:
        with ZipFile(BytesIO(payload)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"<[^>]+>", " ", text)
        return text

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_email(text: str) -> str:
        match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.IGNORECASE)
        return match.group(0) if match else ""

    @staticmethod
    def _extract_phone(text: str) -> str:
        matches = re.findall(r"(?:\+?\d[\d()\-\s]{7,}\d)", text)
        for match in matches:
            digits = re.sub(r"\D", "", match)
            if 10 <= len(digits) <= 15:
                return match.strip()
        return ""

    def _extract_name(self, text: str, filename: str, email: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:8]:
            lowered = line.lower()
            if any(hint in lowered for hint in self._SECTION_HINTS):
                continue
            if "@" in line or re.search(r"\d", line):
                continue
            words = re.findall(r"[A-Za-z][A-Za-z'\-.]+", line)
            if 2 <= len(words) <= 4 and len(line) <= 60:
                return " ".join(word.capitalize() if word.islower() else word for word in words)

        stem = Path(filename).stem
        if email:
            stem = email.split("@", 1)[0]
        cleaned = re.sub(r"[_\-.]+", " ", stem)
        cleaned = re.sub(r"\bresume\b", "", cleaned, flags=re.IGNORECASE).strip()
        words = [word.capitalize() for word in cleaned.split() if word]
        return " ".join(words[:4]) or "Candidate"

    def _extract_title(self, text: str, applicant_name: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:12]:
            lowered = line.lower()
            if applicant_name and applicant_name.lower() in lowered:
                continue
            if any(hint in lowered for hint in self._SECTION_HINTS):
                continue
            if "@" in line or re.search(r"\d{4}", line):
                continue
            if 2 <= len(line.split()) <= 8 and len(line) <= 80:
                return line
        return ""

    @staticmethod
    def _extract_years_experience(text: str) -> str:
        matches = re.findall(r"(\d{1,2})\+?\s+years?", text, flags=re.IGNORECASE)
        if not matches:
            return ""
        best = max(int(value) for value in matches)
        suffix = "+ years" if f"{best}+ years" in text.lower() else " years"
        return f"{best}{suffix}"

    def _extract_skills(self, text: str) -> list[str]:
        lowered = text.lower()
        skills: list[str] = []
        for needle, label in self._SKILL_KEYWORDS:
            pattern = r"\b" + re.escape(needle) + r"\b"
            if re.search(pattern, lowered):
                skills.append(label)
            if len(skills) == 8:
                break
        return skills

    def _extract_summary(self, text: str, applicant_name: str, title: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        chosen: list[str] = []
        for line in lines[:20]:
            lowered = line.lower()
            if applicant_name and applicant_name.lower() in lowered:
                continue
            if title and line == title:
                continue
            if any(hint == lowered for hint in self._SECTION_HINTS):
                continue
            if "@" in line:
                continue
            if len(line) < 30:
                continue
            chosen.append(line)
            if len(chosen) == 2:
                break
        summary = " ".join(chosen)
        return summary[:320]