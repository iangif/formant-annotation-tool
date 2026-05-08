"""
Script utils
"""

def empty_to_none(value: str | None) -> str | None:
    """
    Helper to convert empty CSV cells into None.
    """

    if value is None:
        return None

    value = value.strip()

    return value if value else None
