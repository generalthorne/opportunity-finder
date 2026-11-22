
from opportunity_intelligence.extraction.extraction_cache import (
    ExtractionCache,
    calculate_content_hash,
    normalize_cache_url,
)
from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult,
)


def create_result(is_opportunity_page=True):
    return PageExtractionResult(
        is_opportunity_page=is_opportunity_page,
        confidence=0.95,
        opportunities=[],
        reasoning="Test extraction result",
    )


def test_cache_stores_and_retrieves_result(tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")

    result = create_result()
    content_hash = calculate_content_hash("Research internship")

    cache.set(
        url="https://example.com/research",
        content_hash=content_hash,
        model="qwen3:8b",
        result=result,
    )

    cache.save()

    loaded_cache = ExtractionCache(tmp_path / "cache.json")

    cached_result = loaded_cache.get(
        url="https://example.com/research",
        content_hash=content_hash,
        model="qwen3:8b",
    )

    assert cached_result == result


def test_cache_rejects_changed_content(tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")

    result = create_result()

    cache.set(
        url="https://example.com/research",
        content_hash=calculate_content_hash("Original content"),
        model="qwen3:8b",
        result=result,
    )

    cached_result = cache.get(
        url="https://example.com/research",
        content_hash=calculate_content_hash("Updated content"),
        model="qwen3:8b",
    )

    assert cached_result is None


def test_cache_rejects_different_model(tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")

    result = create_result()
    content_hash = calculate_content_hash("Research internship")

    cache.set(
        url="https://example.com/research",
        content_hash=content_hash,
        model="qwen3:4b",
        result=result,
    )

    cached_result = cache.get(
        url="https://example.com/research",
        content_hash=content_hash,
        model="qwen3:8b",
    )

    assert cached_result is None


def test_cache_stores_negative_classifications(tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")

    result = create_result(is_opportunity_page=False)
    content_hash = calculate_content_hash("General career information")

    cache.set(
        url="https://example.com/careers",
        content_hash=content_hash,
        model="qwen3:8b",
        result=result,
    )

    cached_result = cache.get(
        url="https://example.com/careers",
        content_hash=content_hash,
        model="qwen3:8b",
    )

    assert cached_result is not None
    assert cached_result.is_opportunity_page is False


def test_cache_normalizes_urls(tmp_path):
    cache = ExtractionCache(tmp_path / "cache.json")

    result = create_result()
    content_hash = calculate_content_hash("Research internship")

    cache.set(
        url="HTTPS://EXAMPLE.COM/research/",
        content_hash=content_hash,
        model="qwen3:8b",
        result=result,
    )

    cached_result = cache.get(
        url="https://example.com/research",
        content_hash=content_hash,
        model="qwen3:8b",
    )

    assert cached_result == result


def test_normalize_cache_url_removes_fragments():
    assert normalize_cache_url(
        "https://example.com/research#section"
    ) == "https://example.com/research"
