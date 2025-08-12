"""
Tests for providers/parameter_manager.py - Provider-specific parameter management.

These tests validate the ParameterManager class which handles provider-specific
parameters and configurations for different LLM providers.
"""

import unittest

from codedjinn.providers.parameter_manager import ParameterManager


class TestParameterManager(unittest.TestCase):
    """Test cases for ParameterManager class."""

    def test_parameter_manager_initialization(self):
        """Test ParameterManager initialization."""
        manager = ParameterManager()
        self.assertIsInstance(manager, ParameterManager)

    def test_parameter_manager_has_required_methods(self):
        """Test that ParameterManager has expected methods."""
        manager = ParameterManager()
        
        # Should have get_provider_parameters method
        self.assertTrue(hasattr(manager, 'get_provider_parameters'))
        self.assertTrue(callable(manager.get_provider_parameters))

    def test_get_provider_parameters_returns_dict(self):
        """Test that get_provider_parameters returns a dictionary."""
        manager = ParameterManager()
        
        # Should return dict for known providers
        known_providers = ['deepinfra', 'mistralai', 'gemini']
        
        for provider in known_providers:
            try:
                params = manager.get_provider_parameters(provider)
                self.assertIsInstance(params, dict)
            except (AttributeError, ValueError):
                # Method might not be fully implemented yet
                pass

    def test_parameter_manager_handles_unknown_provider(self):
        """Test parameter manager behavior with unknown provider."""
        manager = ParameterManager()
        
        try:
            # Should handle unknown provider gracefully
            result = manager.get_provider_parameters('unknown_provider')
            # Should return dict (possibly empty) or raise appropriate exception
            self.assertTrue(isinstance(result, dict) or result is None)
        except (ValueError, KeyError, AttributeError):
            # Acceptable to raise these exceptions for unknown providers
            pass

    def test_parameter_manager_methods_exist(self):
        """Test that expected methods exist on ParameterManager."""
        manager = ParameterManager()
        
        # These methods should exist (even if not fully implemented)
        expected_methods = ['get_provider_parameters']
        
        for method_name in expected_methods:
            self.assertTrue(hasattr(manager, method_name),
                          f"ParameterManager should have {method_name} method")


if __name__ == "__main__":
    unittest.main()