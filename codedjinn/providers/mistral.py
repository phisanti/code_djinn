from agno.models.mistral import MistralChat


def build_mistral_model(
    model_id: str,
    api_key: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: int = 30,
) -> MistralChat:
    """
    Return a configured MistralChat model.

    Note: The Mistral SDK expects timeout_ms (milliseconds), but Agno's
    MistralChat has a bug where it passes 'timeout' instead. We work around
    this by using client_params to pass timeout_ms directly.
    """
    return MistralChat(
        id=model_id,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        # Work around Agno bug: pass timeout_ms via client_params
        client_params={"timeout_ms": timeout * 1000},  # Convert seconds to milliseconds
    )
