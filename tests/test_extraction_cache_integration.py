
from unittest.mock import patch

from opportunity_intelligence.extraction.extraction_cache import (
    ExtractionCache,
)
from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult,
)
from opportunity_intelligence.extraction.page_extractor import (
    extract_opportunities_from_page,
)


def create_page():
    return {
        "status": "success",
        "url": "https://example.com/research",
        "page_title": "Undergraduate Research Opportunities",
        "page_text": (
            "Undergraduate research assistant positions are available. "
            "Students can apply to work with faculty on research projects. "
            * 10
        ),
    }


def create_result(is_opportunity_page=True):
    return PageExtractionResult(
        is_opportunity_page=is_opportunity_page,
        confidence=0.95,
        opportunities=[],
        reasoning="Test extraction result",
    )


@patch(
    "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
)
def test_cache_hit_skips_llm(mock_llm, tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")
    page = create_page()
    result = create_result()

    from opportunity_intelligence.extraction.text_preprocessor import (
        clean_page_text,
    )
    from opportunity_intelligence.extraction.extraction_cache import (
        calculate_content_hash,
    )

    cleaned_text = clean_page_text(page["page_text"])

    cache.set(
        url=page["url"],
        content_hash=calculate_content_hash(
            cleaned_text,
            page["page_title"],
        ),
        model="gemma4:12b",
        result=result,
    )

    extract_opportunities_from_page(
        page=page,
        cache=cache,
    )

    mock_llm.assert_not_called()


@patch(
    "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
)
def test_cache_miss_calls_llm_and_stores_result(mock_llm, tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")
    page = create_page()
    result = create_result()

    mock_llm.return_value = result

    extract_opportunities_from_page(
        page=page,
        cache=cache,
    )

    mock_llm.assert_called_once()

    from opportunity_intelligence.extraction.text_preprocessor import (
        clean_page_text,
    )
    from opportunity_intelligence.extraction.extraction_cache import (
        calculate_content_hash,
    )

    cached_result = cache.get(
        url=page["url"],
        content_hash=calculate_content_hash(
            clean_page_text(page["page_text"]),
            page["page_title"],
        ),
        model="gemma4:12b",
    )

    assert cached_result == result


@patch(
    "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
)
def test_negative_result_is_reused(mock_llm, tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")
    page = create_page()

    mock_llm.return_value = create_result(
        is_opportunity_page=False
    )

    first_result = extract_opportunities_from_page(
        page=page,
        cache=cache,
    )

    second_result = extract_opportunities_from_page(
        page=page,
        cache=cache,
    )

    assert first_result == []
    assert second_result == []
    mock_llm.assert_called_once()


@patch(
    "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
)
def test_changed_page_content_triggers_new_llm_call(mock_llm, tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")
    page = create_page()

    mock_llm.return_value = create_result()

    extract_opportunities_from_page(
        page=page,
        cache=cache,
    )

    updated_page = create_page()
    updated_page["page_text"] += "Additional research information. " * 10

    extract_opportunities_from_page(
        page=updated_page,
        cache=cache,
    )

    assert mock_llm.call_count == 2


@patch(
    "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
)
def test_same_model_reuses_cached_result(mock_llm, tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")
    page = create_page()

    mock_llm.return_value = create_result()

    extract_opportunities_from_page(
        page=page,
        model="gemma4:12b",
        cache=cache,
    )

    extract_opportunities_from_page(
        page=page,
        model="gemma4:12b",
        cache=cache,
    )

    mock_llm.assert_called_once()