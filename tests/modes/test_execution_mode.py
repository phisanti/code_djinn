"""
Tests for modes/execution_mode.py - Command execution mode functionality.

These tests validate the ExecutionMode class which handles command generation
and safe execution with user confirmation.
"""

import unittest

from codedjinn.modes.execution_mode import ExecutionMode


class TestExecutionMode(unittest.TestCase):
    """Test cases for ExecutionMode class."""

    def test_execution_mode_class_exists(self):
        """Test that ExecutionMode class can be imported."""
        self.assertTrue(ExecutionMode)

    def test_execution_mode_has_expected_methods(self):
        """Test that ExecutionMode has expected methods."""
        # Check class methods without instantiating
        expected_methods = ['ask_and_execute']
        
        for method_name in expected_methods:
            self.assertTrue(hasattr(ExecutionMode, method_name),
                          f"ExecutionMode should have {method_name} method")

    def test_execution_mode_initialization_signature(self):
        """Test ExecutionMode initialization signature."""
        import inspect
        
        sig = inspect.signature(ExecutionMode.__init__)
        params = list(sig.parameters.keys())
        
        # Should have basic parameters
        expected_params = ['self', 'llm', 'provider', 'os_fullname', 'shell']
        for param in expected_params:
            self.assertIn(param, params)

    def test_execution_mode_inherits_from_base(self):
        """Test that ExecutionMode inherits from base mode."""
        from codedjinn.modes.base_mode import BaseMode
        
        # Should be a subclass of BaseMode
        self.assertTrue(issubclass(ExecutionMode, BaseMode))

    def test_ask_and_execute_method_signature(self):
        """Test ask_and_execute method signature."""
        import inspect
        
        sig = inspect.signature(ExecutionMode.ask_and_execute)
        params = list(sig.parameters.keys())
        
        # Should have wish and verbose parameters
        expected_params = ['self', 'wish', 'verbose']
        for param in expected_params:
            self.assertIn(param, params)

    def test_execution_mode_methods_callable(self):
        """Test that key methods are callable."""
        self.assertTrue(callable(ExecutionMode.ask_and_execute))


if __name__ == "__main__":
    unittest.main()