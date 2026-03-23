"""Teacher persona extraction from ingested documents."""

from __future__ import annotations

from pathlib import Path

from eduagent.llm import LLMClient
from eduagent.models import AppConfig, Document, TeacherPersona


PROMPT_PATH = Path(__file__).parent / "prompts" / "persona_extract.txt"


def _build_document_block(documents: list[Document]) -> str:
    """Format documents for insertion into the prompt."""
    parts: list[str] = []
    for i, doc in enumerate(documents, 1):
        parts.append(
            f"--- Document {i}: {doc.title} ({doc.doc_type.value}) ---\n"
            f"{doc.content[:3000]}\n"  # Cap per-doc length to stay within context
        )
    return "\n".join(parts)


async def extract_persona(
    documents: list[Document],
    config: AppConfig | None = None,
) -> TeacherPersona:
    """Analyze teaching documents and extract a structured persona.

    Sends document excerpts to the configured LLM and parses the returned
    JSON into a TeacherPersona model.
    """
    if not documents:
        raise ValueError("No documents provided for persona extraction.")

    prompt_template = PROMPT_PATH.read_text()
    doc_block = _build_document_block(documents)
    prompt = prompt_template.replace("{documents}", doc_block)

    client = LLMClient(config)
    data = await client.generate_json(
        prompt=prompt,
        system="You are an educational analysis assistant. Respond only with valid JSON.",
        temperature=0.3,
    )

    return TeacherPersona.model_validate(data)


def save_persona(persona: TeacherPersona, output_dir: Path) -> Path:
    """Save a persona to disk as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "persona.json"
    path.write_text(persona.model_dump_json(indent=2))
    return path


def load_persona(path: Path) -> TeacherPersona:
    """Load a persona from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")
    return TeacherPersona.model_validate_json(path.read_text())
