def clamp(value: int, min_value: int, max_value: int) -> int:
    """Clamp an integer between min_value and max_value inclusive."""
    return max(min_value, min(value, max_value))
