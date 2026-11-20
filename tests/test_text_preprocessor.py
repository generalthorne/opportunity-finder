from opportunity_intelligence.extraction.text_preprocessor import (
    clean_page_text
)


def test_clean_page_text_removes_extra_spaces():
    text = "Research    opportunities\t for students"

    result = clean_page_text(text)

    assert result == "Research opportunities for students"


def test_clean_page_text_reduces_blank_lines():
    text = "First paragraph\n\n\n\nSecond paragraph"

    result = clean_page_text(text)

    assert result == "First paragraph\n\nSecond paragraph"


def test_clean_page_text_strips_outer_whitespace():
    text = "   Research opportunities   "

    result = clean_page_text(text)

    assert result == "Research opportunities"


def test_clean_page_text_preserves_paragraphs():
    text = "First paragraph\n\nSecond paragraph"

    result = clean_page_text(text)

    assert result == "First paragraph\n\nSecond paragraph"


def test_clean_page_text_handles_empty_string():
    assert clean_page_text("") == ""