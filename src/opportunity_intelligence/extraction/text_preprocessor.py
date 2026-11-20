"""Clean webpage text before opportunity extraction."""

import re


def clean_page_text(text: str) -> str:
    """Normalize whitespace in webpage text."""

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()