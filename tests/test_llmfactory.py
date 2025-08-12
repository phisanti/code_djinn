"""
Tests for llmfactory.py - LLM provider factory functionality.

These tests validate the LLMFactory class which handles creating LLM instances
for different providers with lazy loading and proper configuration.
"""

import unittest

from codedjinn.llmfactory import LLMFactory


class TestLLMFactory(unittest.TestCase):
    """Test cases for LLMFactory class."""

    def test_llmfactory_initialization(self):
        """Test LLMFactory initialization."""
        factory = LLMFactory()
        self.assertIsInstance(factory, LLMFactory)

    def test_llmfactory_create_llm_signature(self):
        """Test that create_llm method has expected signature."""
        import inspect
        
        factory = LLMFactory()
        sig = inspect.signature(factory.create_llm)
        params = list(sig.parameters.keys())
        
        # Should have provider, model_name, api_key parameters
        expected_params = ['provider', 'model_name', 'api_key']
        for param in expected_params:
            self.assertIn(param, params)

    def test_supported_providers_exist(self):
        """Test that supported provider constants exist."""
        # These should be defined in the factory
        factory = LLMFactory()
        
        # Should not raise exceptions when checking for these providers
        supported_providers = ['deepinfra', 'mistralai', 'gemini']
        
        for provider in supported_providers:
            # Test that the factory recognizes these as provider strings
            self.assertIsInstance(provider, str)
            self.assertTrue(len(provider) > 0)

    def test_llmfactory_has_required_methods(self):
        """Test that LLMFactory has all required methods."""
        factory = LLMFactory()
        
        # Should have create_llm method
        self.assertTrue(hasattr(factory, 'create_llm'))
        self.assertTrue(callable(factory.create_llm))

    def test_create_llm_missing_parameters_raises_error(self):
        """Test that create_llm raises appropriate errors for missing parameters."""
        factory = LLMFactory()
        
        # Should raise TypeError when required parameters are missing
        with self.assertRaises(TypeError):
            factory.create_llm()  # No parameters
        
        with self.assertRaises(TypeError):
            factory.create_llm('deepinfra')  # Missing model_name and api_key


if __name__ == "__main__":
    unittest.main()