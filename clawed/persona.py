"""Teacher persona extraction from ingested documents."""

from __future__ import annotations

from pathlib import Path

from clawed.llm import LLMClient
from clawed.models import AppConfig, Document, TeacherPersona

PROMPT_PATH = Path(__file__).parent / "prompts" / "persona_extract.txt"


_MAX_TOTAL_CHARS = 50_000  # ~12k tokens — fits comfortably in any model's context
_MAX_PER_DOC_CHARS = 3_000
_MAX_DOCS = 30  # Sample at most 30 representative documents


def _build_document_block(documents: list[Document]) -> str:
    """Format documents for insertion into the prompt.

    For large corpora (1000+ docs), samples representative documents
    to stay within LLM context limits.
    """
    # Sample if corpus is very large
    sampled = documents
    if len(documents) > _MAX_DOCS:
        import random
        # Deterministic sample for reproducibility
        rng = random.Random(42)
        sampled = rng.sample(documents, _MAX_DOCS)

    parts: list[str] = []
    total = 0
    for i, doc in enumerate(sampled, 1):
        excerpt = doc.content[:_MAX_PER_DOC_CHARS]
        if total + len(excerpt) > _MAX_TOTAL_CHARS:
            break
        parts.append(
            f"--- Document {i}: {doc.title} ({doc.doc_type.value}) ---\n"
            f"{excerpt}\n"
        )
        total += len(excerpt)

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

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
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
    path.write_text(persona.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_persona(path: Path) -> TeacherPersona:
    """Load a persona from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")
    return TeacherPersona.model_validate_json(path.read_text(encoding="utf-8"))
