import json
import os
from pathlib import Path

# Default path to the curated scholarship dataset.
DATA_PATH = Path(__file__).parent / "data" / "scholarships_data.json"


def load_scholarships(path: str | Path | None = None) -> list[dict]:
    """Load the local scholarship knowledge base from JSON."""
    target = Path(path) if path else DATA_PATH
    if not target.exists():
        return []
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("scholarships", [])
    except Exception:
        return []


def _normalize(text: str) -> str:
    return text.lower().strip()


def retrieve_scholarships(query: str, path: str | Path | None = None, top_k: int = 5) -> list[dict]:
    """
    Retrieve the most relevant scholarships from the local KB for the given query.
    Simple keyword-based retrieval over country, level, field, name, and provider.
    """
    scholarships = load_scholarships(path)
    if not scholarships:
        return []

    query_terms = set(_normalize(query).split())
    scored = []

    for item in scholarships:
        score = 0
        text_to_check = " ".join([
            item.get("name", ""),
            item.get("provider", ""),
            " ".join(item.get("countries", [])),
            " ".join(item.get("levels", [])),
            " ".join(item.get("fields", [])),
            item.get("eligibility", ""),
            item.get("next_steps", ""),
        ])
        text_normalized = _normalize(text_to_check)
        text_words = set(text_normalized.split())

        for term in query_terms:
            if len(term) < 2:
                continue
            # Exact word match
            if term in text_words:
                score += 2
            # Substring match in longer phrases
            elif term in text_normalized:
                score += 1

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def format_scholarship_context(scholarships: list[dict]) -> str:
    """Format retrieved scholarships into a context string for the LLM prompt."""
    if not scholarships:
        return "No matching scholarships found in the curated knowledge base."

    lines = ["Retrieved scholarships from curated knowledge base:"]
    for item in scholarships:
        lines.append(f"\n- {item.get('name')} (ID: {item.get('id')})")
        lines.append(f"  Provider: {item.get('provider')}")
        lines.append(f"  Countries: {', '.join(item.get('countries', []))}")
        lines.append(f"  Levels: {', '.join(item.get('levels', []))}")
        lines.append(f"  Fields: {', '.join(item.get('fields', []))}")
        lines.append(f"  Eligibility: {item.get('eligibility')}")
        lines.append(f"  Benefits: {item.get('benefits')}")
        lines.append(f"  Deadline: {item.get('deadline')}")
        lines.append(f"  Next steps: {item.get('next_steps')}")
    return "\n".join(lines)


def get_rag_context_for_query(query: str, top_k: int = 5) -> str:
    """High-level helper: retrieve and format scholarship context for a user query."""
    retrieved = retrieve_scholarships(query, top_k=top_k)
    return format_scholarship_context(retrieved)
