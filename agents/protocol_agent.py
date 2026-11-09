from datetime import datetime, timezone
from pathlib import Path
import json


def generate_protocol(topic: str, research_question: str = "", inclusion_criteria=None,
                      exclusion_criteria=None, year_from=None, year_to=None,
                      language=None, document_types=None) -> dict:
    """Create a topic-agnostic, editable review protocol draft."""
    topic = topic.strip()
    if not topic:
        raise ValueError("Research topic cannot be empty")
    protocol = {
        "topic": topic,
        "research_question": research_question.strip() or f"What does the scientific literature report about {topic}?",
        "objective": f"Identify, collect and screen scientific studies relevant to: {topic}.",
        "methodology": "Systematic literature review; protocol is a draft and must be validated by the research team.",
        "guideline": "PRISMA 2020",
        "sources": ["OpenAlex"],
        "inclusion_criteria": inclusion_criteria or [],
        "exclusion_criteria": exclusion_criteria or [],
        "date_range": {"from": year_from, "to": year_to},
        "language": language,
        "document_types": document_types or [],
        "screening_policy": "Automated screening is preliminary; uncertain decisions require human review.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0"
    }
    return protocol


def save_protocol(protocol: dict, path="data/research_protocol/research_protocol.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(protocol, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
