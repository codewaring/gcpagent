from dataclasses import dataclass
from textwrap import dedent

from google import genai
from google.genai import types


@dataclass
class ChatMessage:
    role: str  # "user" or "model"
    text: str


class ChatAgent:
    def __init__(self, model_name: str) -> None:
        self.client = None
        self.model_name = model_name

    def _client(self) -> genai.Client:
        if self.client is None:
            self.client = genai.Client()
        return self.client

    def _system_instruction(self, template_text: str, reference_context: str) -> str:
        return dedent(
            f"""
            You are a professional Job Description (JD) generation assistant for Globe Telecom.

            Your capabilities:
            - Generate complete, polished job descriptions in Markdown when the user names a role.
            - Ask ONE focused clarifying question only if the role title itself is completely absent.
            - Refine or adjust a previously generated JD based on user feedback in the same conversation.
            - Answer general questions about JD writing best practices.

            JD template — always follow this exact section order and heading style:
            {template_text}

            Reference documents loaded from Globe Telecom's GCS document library
            (use these for tone, structure and style inspiration — do NOT copy verbatim):
            {reference_context or "No reference documents loaded."}

            Behaviour rules:
            - If the user provides a job title, generate the full JD immediately.
            - Infer reasonable defaults for missing fields (location → Manila, Philippines;
              employment type → Full-time) rather than asking.
            - Always respond in English unless the user explicitly writes in another language.
            - Always output the final JD in Markdown inside the same reply.
                        - Start the reply directly with the JD title as a Markdown heading.
                        - Do not add any preface such as "Of course" or "Here is the JD" before the first heading.
            - Keep tone professional, inclusive, and specific to telecom and digital services.
            """
        ).strip()

    def reply(
        self,
        user_message: str,
        history: list[ChatMessage],
        template_text: str,
        reference_context: str,
    ) -> str:
        contents: list[types.Content] = [
            types.Content(role=msg.role, parts=[types.Part(text=msg.text)])
            for msg in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

        response = self._client().models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=self._system_instruction(template_text, reference_context),
            ),
        )
        return response.text or ""
