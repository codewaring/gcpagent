from dataclasses import dataclass
from textwrap import dedent

from google import genai


@dataclass
class JDRequest:
    company_name: str
    business_unit: str
    role_title: str
    location: str
    employment_type: str
    seniority: str
    key_skills: list[str]
    responsibilities: list[str]
    requirements: list[str]
    language: str = "English"


class JDAgent:
    def __init__(self, model_name: str) -> None:
        self.client = genai.Client()
        self.model_name = model_name

    def _build_prompt(self, request: JDRequest, template_text: str, reference_context: str) -> str:
        reference_block = reference_context.strip() or "No external reference documents provided."
        return dedent(
            f"""
            You are a senior technical recruiter writing polished job descriptions for Globe Telecom.

            Follow the template format exactly. Keep section order and heading style aligned with the template.
            Output only the final job description in Markdown.

            Template reference:
            {template_text}

            Reference documents from the configured GCS directory:
            {reference_block}

            Input details:
            - Company: {request.company_name}
            - Business Unit: {request.business_unit}
            - Role Title: {request.role_title}
            - Location: {request.location}
            - Employment Type: {request.employment_type}
            - Seniority: {request.seniority}
            - Language: {request.language}
            - Key Skills: {", ".join(request.key_skills)}
            - Responsibilities: {"; ".join(request.responsibilities)}
            - Requirements: {"; ".join(request.requirements)}

            Writing constraints:
            - Keep tone professional and inclusive.
            - Make it specific to telecom and digital services context.
            - Avoid vague filler text.
            - Use measurable language where possible.
            - Treat references as guidance and inspiration. Do not copy chunks verbatim.
            """
        ).strip()

    def generate(self, request: JDRequest, template_text: str, reference_context: str) -> str:
        prompt = self._build_prompt(request, template_text, reference_context)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text or ""
