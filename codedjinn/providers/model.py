from typing import Callable

from codedjinn.providers.gemini import build_gemini_model
from codedjinn.providers.mistral import build_mistral_model

ModelBuilder = Callable[[str, str, float, int, int], object]


def build_model(
    provider: str,
    model_id: str,
    api_key: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: int = 30,
):
    """
    Build a provider-specific Agno model based on configuration.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider = (provider or "").strip().lower()
    builders: dict[str, ModelBuilder] = {
        "mistralai": build_mistral_model,
        "gemini": build_gemini_model,
    }

    builder = builders.get(provider)
    if builder is None:
        supported = ", ".join(sorted(builders))
        raise ValueError(f"Unsupported provider '{provider}'. Supported: {supported}.")

    return builder(model_id, api_key, temperature, max_tokens, timeout)
