
"""Clean and prioritize webpage text before opportunity extraction."""

import re


MAX_PAGE_CHARACTERS = 16000

BOILERPLATE_PATTERNS = (
    r"^skip to (main )?content$",
    r"^toggle (navigation|menu)$",
    r"^(main )?menu$",
    r"^search$",
    r"^home$",
    r"^back to top$",
    r"^accept all cookies$",
    r"^manage cookies$",
    r"^cookie settings$",
    r"^privacy policy$",
    r"^terms (of use|and conditions)$",
    r"^accessibility$",
    r"^all rights reserved\.?$",
    r"^follow us$",
    r"^share this page$",
)

IMPORTANT_TERMS = {
    "eligibility": (
        "eligibility", "eligible", "who can apply", "open to",
        "applicants must", "must be enrolled", "currently enrolled",
        "undergraduate", "graduate student", "student status",
    ),
    "deadline": (
        "deadline", "application deadline", "apply by",
        "applications close", "closing date", "due date",
        "submit your application", "applications are accepted until",
    ),
    "requirements": (
        "requirements", "qualifications", "minimum qualifications",
        "required qualifications", "must have", "prerequisites",
        "required skills", "experience required",
    ),
    "compensation": (
        "compensation", "salary", "hourly rate", "pay rate",
        "stipend", "funding", "paid position", "remuneration",
    ),
    "application": (
        "how to apply", "application process", "apply now",
        "application instructions", "submit an application",
        "application materials", "cover letter", "resume",
    ),
    "opportunity": (
        "research assistant", "research position", "research opportunity",
        "internship", "co-op", "coop", "fellowship",
        "student position", "student employment", "job posting",
        "summer program", "undergraduate research",
    ),
    "description": (
        "responsibilities", "what you will do", "role overview",
        "position overview", "about the position", "program overview",
        "position description", "research project",
    ),
}

HEADING_TERMS = {
    term
    for terms in IMPORTANT_TERMS.values()
    for term in terms
} | {
    "overview",
    "about the program",
    "about the role",
    "position details",
    "program details",
    "responsibilities",
    "qualifications",
    "application information",
}


def clean_page_text(text: str) -> str:
    """Normalize whitespace and remove obvious webpage boilerplate."""

    if not isinstance(text, str):
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)

    lines = []
    seen_lines = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue

        normalized = line.lower().strip(" :|-\t")

        if any(
            re.match(pattern, normalized)
            for pattern in BOILERPLATE_PATTERNS
        ):
            continue

        # Remove repeated short navigation labels and duplicate lines.
        if len(line) <= 100 and normalized in seen_lines:
            continue

        if len(line) <= 100:
            seen_lines.add(normalized)

        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def _split_into_blocks(text: str) -> list[str]:
    """Split cleaned text into paragraphs or content sections."""

    return [
        block.strip()
        for block in re.split(r"\n\s*\n", text)
        if block.strip()
    ]


def _score_block(block: str) -> int:
    """Estimate how useful a text block is for opportunity extraction."""

    lowered = block.lower()
    score = 0

    for category, terms in IMPORTANT_TERMS.items():
        if any(term in lowered for term in terms):
            score += {
                "eligibility": 7,
                "deadline": 7,
                "requirements": 6,
                "compensation": 5,
                "application": 5,
                "opportunity": 5,
                "description": 3,
            }[category]

    # Short, heading-like blocks help identify the sections that follow.
    if len(block) <= 100:
        if any(term in lowered for term in HEADING_TERMS):
            score += 4
        elif not re.search(r"[.!?]", block):
            score += 1

    # Date-like and contact/application details can be useful evidence.
    if re.search(
        r"\b(january|february|march|april|may|june|july|"
        r"august|september|october|november|december)\b",
        lowered,
    ):
        score += 2

    if re.search(r"\b20\d{2}\b", lowered):
        score += 1

    return score


def prepare_page_text(
    text: str,
    max_characters: int = MAX_PAGE_CHARACTERS,
) -> str:
    """Clean text and prioritize useful sections within a character limit."""

    cleaned = clean_page_text(text)

    if len(cleaned) <= max_characters:
        return cleaned

    blocks = _split_into_blocks(cleaned)

    if not blocks:
        return ""

    # Keep the opening context, then prioritize the most relevant blocks.
    selected_indices = set(range(min(2, len(blocks))))
    used_characters = sum(
        len(blocks[index]) + 2
        for index in selected_indices
    )

    ranked_indices = sorted(
        range(len(blocks)),
        key=lambda index: (
            _score_block(blocks[index]),
            -index,
        ),
        reverse=True,
    )

    for index in ranked_indices:
        if index in selected_indices:
            continue

        block_length = len(blocks[index]) + 2

        if used_characters + block_length <= max_characters:
            selected_indices.add(index)
            used_characters += block_length

    # Restore the original page order after selecting useful sections.
    selected_blocks = [
        blocks[index]
        for index in sorted(selected_indices)
    ]

    result = "\n\n".join(selected_blocks)

    # Final safety limit in case the opening blocks alone exceed the limit.
    return result[:max_characters].rstrip()
