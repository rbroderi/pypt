"""Template loading and rendering utilities."""

import importlib.resources


def load_template(relative_path: str) -> str:
    """Load a template file from the bundled templates directory."""
    resource = importlib.resources.files("pyptmpl") / "templates"
    for part in relative_path.split("/"):
        resource = resource / part
    return resource.read_text(encoding="utf-8")


def render_template(template: str, **kwargs: str) -> str:
    """Replace {{KEY}} placeholders in template with provided values."""
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", value)
    return template
