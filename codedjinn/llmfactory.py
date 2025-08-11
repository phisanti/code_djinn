import importlib
from typing import Dict, List, Optional, Any


class LazyLoader:
    """Lazily import modules only when they are first used."""

    def __init__(self, import_path: str, module_name: str):
        self.import_path = import_path
        self.module_name = module_name
        self._module = None

    def __call__(self):
        if self._module is None:
            try:
                self._module = importlib.import_module(self.import_path)
                return self._module
            except ImportError as e:
                raise
        return self._module


class LLMFactory:
    """
    Factory class to create different LLM instances based on provider and model.
    Supports DeepInfra, MistralAI, and Gemini.
    """

    def __init__(self):
        """Initialize the factory with available providers and models"""
        # Create lazy loaders for each provider
        self._deepinfra_loader = LazyLoader(
            "langchain_community.llms", "langchain_community.llms"
        )
        self._mistralai_loader = LazyLoader(
            "langchain_mistralai", "langchain_mistralai"
        )
        self._gemini_loader = LazyLoader(
            "langchain_google_genai", "langchain_google_genai"
        )

        self.providers = {
            "deepinfra": {
                "models": [
                    "Qwen/QwQ-32B",
                    "Qwen/Qwen2.5-Coder-32B-Instruct",
                    "mistralai/Mistral-Small-24B-Instruct-2501",
                ],
                "loader": self._deepinfra_loader,
                "class_name": "DeepInfra",
                "api_param": "deepinfra_api_token",
            },
            "mistralai": {
                "models": ["codestral-latest", "mistral-small-latest"],
                "loader": self._mistralai_loader,
                "class_name": "ChatMistralAI",
                "api_param": "mistral_api_key",
            },
            "gemini": {
                "models": ["gemini-2.0-flash"],
                "loader": self._gemini_loader,
                "class_name": "ChatGoogleGenerativeAI",
                "api_param": "google_api_key",
            },
        }

    def create_llm(self, provider: str, model: str, api_key: str, **kwargs):
        """
        Create and return an LLM instance based on provider and model

        Args:
            provider: The LLM provider (deepinfra, mistralai, gemini)
            model: The model name
            api_key: API key for the provider
            **kwargs: Additional arguments for the LLM

        Returns:
            An LLM instance
        """
        provider = provider.lower()

        if provider not in self.providers:
            raise ValueError(
                f"Provider {provider} not supported. Available providers: {', '.join(self.providers.keys())}"
            )

        provider_info = self.providers[provider]

        if model not in provider_info["models"]:
            raise ValueError(
                f"Model {model} not available for {provider}. Available models: {', '.join(provider_info['models'])}"
            )

        module = provider_info["loader"]()
        llm_class = getattr(module, provider_info["class_name"])
        params = {provider_info["api_param"]: api_key}

        # For DeepInfra, use model_id instead of model
        if provider == "deepinfra":
            return llm_class(model_id=model, **params, **kwargs)
        else:
            return llm_class(model=model, **params, **kwargs)

    def get_available_providers(self) -> List[str]:
        """Return a list of available LLM providers"""
        return list(self.providers.keys())

    def get_available_models(self, provider: str) -> List[str]:
        """Return a list of available models for a given provider"""
        provider = provider.lower()
        if provider not in self.providers:
            raise ValueError(
                f"Provider {provider} not supported. Available providers: {', '.join(self.providers.keys())}"
            )
        return self.providers[provider]["models"]


if __name__ == "__main__":
    # Simple test
    factory = LLMFactory()

    # Print available providers
    print("Available providers:", factory.get_available_providers())

    # Print available models for each provider
    for provider in factory.get_available_providers():
        print(f"Models for {provider}:", factory.get_available_models(provider))
