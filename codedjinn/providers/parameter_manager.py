from typing import Dict, Any
from abc import ABC, abstractmethod


class ParameterManager:
    """
    Manages provider-specific parameters for LLM requests.
    """

    def __init__(self):
        """Initialize the parameter manager with provider configurations."""
        self.provider_configs = {
            "deepinfra": {
                "temperature": 0.2,
                "repetition_penalty": 1.2,
                "top_p": 0.9,
                "max_tokens_key": "max_new_tokens",
            },
            "mistralai": {"temperature": 0.2, "max_tokens_key": "max_tokens"},
            "gemini": {"temperature": 0.2, "max_tokens_key": "max_output_tokens"},
        }

    def get_parameters(self, provider: str, explain: bool = False) -> Dict[str, Any]:
        """
        Get provider-specific parameters for LLM requests.

        Args:
            provider: The LLM provider name
            explain: Whether the request includes explanation (affects token limit)

        Returns:
            Dict of parameters for the provider

        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()

        if provider not in self.provider_configs:
            raise ValueError(f"Provider {provider} not supported")

        config = self.provider_configs[provider].copy()

        # Set max tokens based on explain flag
        max_tokens = 1000 if explain else 250
        max_tokens_key = config.pop("max_tokens_key")
        config[max_tokens_key] = max_tokens

        return config

    def apply_parameters(
        self, llm_instance, provider: str, explain: bool = False
    ) -> None:
        """
        Apply provider-specific parameters to an LLM instance.

        Args:
            llm_instance: The LLM instance to configure
            provider: The LLM provider name
            explain: Whether the request includes explanation
        """
        parameters = self.get_parameters(provider, explain)

        # Apply parameters to the LLM instance
        if hasattr(llm_instance, "model_kwargs"):
            llm_instance.model_kwargs = parameters
        else:
            # If model_kwargs doesn't exist, set individual attributes
            for key, value in parameters.items():
                if hasattr(llm_instance, key):
                    setattr(llm_instance, key, value)
