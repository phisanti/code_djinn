from agno.models.mistral import MistralChat


def build_mistral_model(
    model_id: str,
    api_key: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: int = 30,
) -> MistralChat:
    """Return a configured MistralChat model."""
    return MistralChat(
        id=model_id,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
