"""
Tests for modes/chat_mode.py - Interactive chat mode functionality.

These tests validate the ChatMode class which handles conversational
interactions for command generation and execution.
"""

import unittest

from codedjinn.modes.chat_mode import ChatMode


class TestChatMode(unittest.TestCase):
    """Test cases for ChatMode class."""

    def test_chat_mode_class_exists(self):
        """Test that ChatMode class can be imported."""
        self.assertTrue(ChatMode)

    def test_chat_mode_has_expected_methods(self):
        """Test that ChatMode has expected methods."""
        # Check class methods without instantiating
        expected_methods = ['start', '_process_input']
        
        for method_name in expected_methods:
            self.assertTrue(hasattr(ChatMode, method_name),
                          f"ChatMode should have {method_name} method")

    def test_chat_mode_initialization_signature(self):
        """Test ChatMode initialization signature."""
        import inspect
        
        sig = inspect.signature(ChatMode.__init__)
        params = list(sig.parameters.keys())
        
        # Should have basic parameters
        expected_params = ['self', 'llm', 'provider', 'os_fullname', 'shell']
        for param in expected_params:
            self.assertIn(param, params)

    def test_chat_mode_inherits_from_base(self):
        """Test that ChatMode inherits from base mode."""
        from codedjinn.modes.base_mode import BaseMode
        
        # Should be a subclass of BaseMode
        self.assertTrue(issubclass(ChatMode, BaseMode))

    def test_chat_mode_start_method_exists(self):
        """Test that start method exists and is callable."""
        self.assertTrue(hasattr(ChatMode, 'start'))
        self.assertTrue(callable(ChatMode.start))


if __name__ == "__main__":
    unittest.main()