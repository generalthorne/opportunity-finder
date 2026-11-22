
from unittest.mock import patch, MagicMock

from opportunity_intelligence.extraction.ollama_client import (
    generate_response
)


def test_generate_response():
    mock_response = MagicMock()
    mock_response.message.content = "This is a test response."

    with patch(
        "opportunity_intelligence.extraction.ollama_client.ollama.chat",
        return_value=mock_response
    ) as mock_chat:

        result = generate_response("Test prompt")

    assert result == "This is a test response."

    mock_chat.assert_called_once_with(
        model="gemma4:12b",
        messages=[
            {
                "role": "user",
                "content": "Test prompt"
            }
        ],
        think=False
    )


def test_generate_response_with_json_schema():
    mock_response = MagicMock()
    mock_response.message.content = '{"is_opportunity": true}'

    schema = {
        "type": "object",
        "properties": {
            "is_opportunity": {
                "type": "boolean"
            }
        }
    }

    with patch(
        "opportunity_intelligence.extraction.ollama_client.ollama.chat",
        return_value=mock_response
    ) as mock_chat:

        result = generate_response(
            "Extract opportunity information.",
            response_format=schema
        )

    assert result == '{"is_opportunity": true}'

    mock_chat.assert_called_once_with(
        model="gemma4:12b",
        messages=[
            {
                "role": "user",
                "content": "Extract opportunity information."
            }
        ],
        think=False,
        format=schema
    )
