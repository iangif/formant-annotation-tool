"""
Script utils
"""

def empty_to_none(value):
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    value = value.strip()

    return value if value else None