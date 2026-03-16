from pathlib import Path


class TemplateStore:
    def __init__(self, template_dir: str) -> None:
        self.template_dir = Path(template_dir)

    def get_template(self, template_name: str) -> str:
        template_path = self.template_dir / f"{template_name}.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")
