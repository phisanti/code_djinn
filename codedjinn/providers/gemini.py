"""Legacy Gemini provider implementation.

Factory function for building Gemini models via Agno
Note: This is a legacy provider - Mistral is now the primary provider
"""

from agno.models.google import Gemini


def build_gemini_model(
    model_id: str,
    api_key: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: int = 30,
) -> Gemini:
    """
    Return a configured Gemini model.

    Note: the Gemini constructor does not accept max_tokens/timeout,
    so we only pass supported parameters for now.
    """
    return Gemini(
        id=model_id,
        api_key=api_key,
        temperature=temperature,
    )
