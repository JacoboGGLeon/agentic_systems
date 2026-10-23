import agentic_systems as toolkit

@toolkit.tool
def normalize_input(text: str) -> dict:
    """Normalize the external input at a deterministic boundary."""
    return {"text": str(text).strip(), "length": len(str(text).strip())}

@toolkit.tool
def record_note(note: str) -> dict:
    """Preserve an evidence note emitted by a reasoning agent."""
    return {"note": note.strip()}
