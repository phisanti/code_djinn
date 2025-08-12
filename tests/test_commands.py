"""
Tests for commands.py - CLI command handlers.

These tests validate the command handling functions for different CLI operations
like run, chat, init, and utility commands.
"""

import unittest

from codedjinn.commands import handle_clear_cache, handle_list_models, handle_run, handle_chat


class TestCommands(unittest.TestCase):
    """Test cases for command handlers."""

    def test_handle_run_signature(self):
        """Test that handle_run has the expected signature."""
        import inspect
        
        sig = inspect.signature(handle_run)
        params = list(sig.parameters.keys())
        
        expected_params = ['wish', 'explain', 'verbose', 'no_confirm']
        for param in expected_params:
            self.assertIn(param, params)

    def test_handle_chat_signature(self):
        """Test that handle_chat has the expected signature."""
        import inspect
        
        sig = inspect.signature(handle_chat)
        params = list(sig.parameters.keys())
        
        # Should have session_id parameter
        self.assertIn('session_id', params)

    def test_handle_clear_cache_exists(self):
        """Test that handle_clear_cache function exists and is callable."""
        self.assertTrue(callable(handle_clear_cache))

    def test_handle_list_models_exists(self):
        """Test that handle_list_models function exists and is callable."""
        self.assertTrue(callable(handle_list_models))

    def test_command_functions_have_docstrings(self):
        """Test that all command handler functions have docstrings."""
        functions = [handle_run, handle_chat, handle_clear_cache, handle_list_models]
        
        for func in functions:
            self.assertIsNotNone(func.__doc__, f"{func.__name__} should have a docstring")
            self.assertTrue(len(func.__doc__.strip()) > 0, f"{func.__name__} docstring should not be empty")


if __name__ == "__main__":
    unittest.main()