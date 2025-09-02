def format_delta(value: int) -> str:
    """Format a stat delta with plus/minus sign, using 0 for no change."""
    if value > 0:
        return f"+{value}"
    if value < 0:
        return f"{value}"
    return "0"
