import httpx
import pytest

from ru_de_translator.translator import TranslationError, Translator


@pytest.mark.asyncio
async def test_rejects_unknown_provider():
    translator = Translator({"translation_provider": "unknown"})
    with pytest.raises(TranslationError, match="Unknown translation provider"):
        await translator.translate("Привет")


@pytest.mark.asyncio
async def test_ollama_strips_reasoning_and_reuses_client():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": "<think>internal</think> Guten Tag"}},
        )

    translator = Translator(
        {
            "translation_provider": "ollama",
            "ollama_url": "http://localhost:11434/",
            "ollama_model": "test-model",
        }
    )
    translator._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        assert await translator.translate("Добрый день") == "Guten Tag"
        assert await translator.translate("Добрый день") == "Guten Tag"
        assert len(requests) == 2
        assert requests[0].url == "http://localhost:11434/api/chat"
    finally:
        await translator.close()


@pytest.mark.asyncio
async def test_gemini_uses_header_instead_of_leaking_key_in_url():
    seen = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen
        seen = request
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Hallo"}]}}]},
        )

    translator = Translator(
        {
            "translation_provider": "gemini",
            "gemini_api_key": "top-secret",
            "gemini_model": "model",
        }
    )
    translator._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        assert await translator.translate("Привет") == "Hallo"
        assert "top-secret" not in str(seen.url)
        assert seen.headers["x-goog-api-key"] == "top-secret"
    finally:
        await translator.close()


@pytest.mark.asyncio
async def test_http_error_is_bounded_and_readable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    translator = Translator(
        {"translation_provider": "ollama", "ollama_url": "http://localhost:11434"}
    )
    translator._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(TranslationError, match="429.*rate limited"):
            await translator.translate("Привет")
    finally:
        await translator.close()
