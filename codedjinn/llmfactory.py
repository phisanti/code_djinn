from typing import Dict, List, Optional
from langchain_community.llms import DeepInfra
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMFactory:
    """
    Factory class to create different LLM instances based on provider and model.
    Supports DeepInfra, MistralAI, and Gemini.
    """

    def __init__(self):
        """Initialize the factory with available providers and models"""
        self.providers = {
            "deepinfra": {
                "models": [
                    "Qwen/QwQ-32B",
                    "Qwen/Qwen2.5-Coder-32B-Instruct",
                    "mistralai/Mistral-Small-24B-Instruct-2501",
                ]
            },
            "mistralai": {"models": ["codestral-2501", "mistral-small-2503"]},
            "gemini": {"models": ["gemini-2.0-flash"]},
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

        if provider == "deepinfra":
            if model not in self.providers[provider]["models"]:
                raise ValueError(
                    f"Model {model} not available for {provider}. Available models: {', '.join(self.providers[provider]['models'])}"
                )
            return DeepInfra(model_id=model, deepinfra_api_token=api_key, **kwargs)

        elif provider == "mistralai":
            if model not in self.providers[provider]["models"]:
                raise ValueError(
                    f"Model {model} not available for {provider}. Available models: {', '.join(self.providers[provider]['models'])}"
                )
            return ChatMistralAI(model=model, mistral_api_key=api_key, **kwargs)

        elif provider == "gemini":
            if model not in self.providers[provider]["models"]:
                raise ValueError(
                    f"Model {model} not available for {provider}. Available models: {', '.join(self.providers[provider]['models'])}"
                )
            return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, **kwargs)

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

    # Test creating an LLM (this would need a valid API key to fully test)
    try:
        # This will fail without a valid API key, but we can test the validation
        llm = factory.create_llm("deepinfra", "Qwen/QwQ-32B", "fake_api_key")
        print("LLM created successfully")
    except Exception as e:
        print(f"Error creating LLM (expected without valid API key): {e}")
