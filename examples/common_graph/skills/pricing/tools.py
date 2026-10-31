import agentic_systems as toolkit


@toolkit.tool
def quote(subtotal: int, *, context: toolkit.Context) -> dict:
    """Apply an integer percentage from the explicit policy snapshot."""
    if subtotal < 0:
        raise ValueError("subtotal must be nonnegative")
    return {
        "total": subtotal * (100 + context.data["tax_percent"]) // 100,
        "currency": context.data["currency"],
        "policy_source": context.sources[0],
        "previous_episodes": len(context.episodes),
        "preceding_events": len(context.lineage),
    }
