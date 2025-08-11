"""
Tests for prompt_builder.py - Prompt generation and formatting functionality.

These tests validate the PromptBuilder class and command prompt generation,
including system prompt preferences integration and template formatting.
"""

import unittest

from codedjinn.core.prompt_builder import PromptBuilder, build_command_prompt


class TestPromptBuilder(unittest.TestCase):
    """Test cases for PromptBuilder class."""

    def test_prompt_builder_basic_functionality(self):
        """Test basic PromptBuilder template formatting."""
        template = "Hello $name, you are $age years old."
        input_variables = ["name", "age"]

        builder = PromptBuilder(template, input_variables)

        # Test successful formatting
        result = builder.format(name="Alice", age="25")
        self.assertEqual(result, "Hello Alice, you are 25 years old.")

    def test_prompt_builder_missing_variables(self):
        """Test PromptBuilder error handling for missing variables."""
        template = "Hello $name, you are $age years old."
        input_variables = ["name", "age"]

        builder = PromptBuilder(template, input_variables)

        # Test missing required variable
        with self.assertRaises(KeyError) as context:
            builder.format(name="Alice")  # Missing 'age'

        self.assertIn("Missing required variables", str(context.exception))
        self.assertIn("age", str(context.exception))

    def test_prompt_builder_extra_variables(self):
        """Test PromptBuilder with extra variables (should be safe)."""
        template = "Hello $name!"
        input_variables = ["name"]

        builder = PromptBuilder(template, input_variables)

        # Extra variables should be ignored safely
        result = builder.format(name="Alice", extra="ignored")
        self.assertEqual(result, "Hello Alice!")

    def test_prompt_builder_get_methods(self):
        """Test PromptBuilder getter methods."""
        template = "Test template with $variable"
        input_variables = ["variable"]

        builder = PromptBuilder(template, input_variables)

        # Test getters
        self.assertEqual(builder.get_template(), template)
        self.assertEqual(builder.get_input_variables(), input_variables)

        # Ensure returned list is a copy (not reference)
        returned_vars = builder.get_input_variables()
        returned_vars.append("new_var")
        self.assertEqual(len(builder.get_input_variables()), 1)  # Original unchanged

    def test_build_command_prompt_basic(self):
        """Test basic command prompt building without system preferences."""
        builder = build_command_prompt("macOS 15.5", "fish", explain=False)

        # Verify it's a PromptBuilder instance
        self.assertIsInstance(builder, PromptBuilder)

        # Test formatting with a sample wish
        prompt = builder.format(wish="list files")

        # Check that basic elements are present
        self.assertIn("macOS 15.5", prompt)
        self.assertIn("fish", prompt)
        self.assertIn("list files", prompt)
        self.assertIn("CLI command expert", prompt)
        self.assertIn("<command>", prompt)

        # Should not contain explanation request when explain=False
        self.assertIn("<explain>no</explain>", prompt)

    def test_build_command_prompt_with_explanation(self):
        """Test command prompt building with explanation enabled."""
        builder = build_command_prompt("Ubuntu 22.04", "bash", explain=True)

        prompt = builder.format(wish="find large files")

        # Check explanation elements
        self.assertIn("<explain>yes</explain>", prompt)
        self.assertIn("<description>", prompt)
        self.assertIn("Ubuntu 22.04", prompt)
        self.assertIn("bash", prompt)

    def test_build_command_prompt_with_system_preferences(self):
        """Test command prompt building with system prompt preferences."""
        system_prefs = (
            "Use colorful command-line tools like lsd, bat, etc. when available"
        )

        builder = build_command_prompt(
            "macOS 15.5", "fish", explain=False, system_prompt_preferences=system_prefs
        )

        prompt = builder.format(wish="list files with details")

        # Check that system preferences are included
        self.assertIn("<user_preferences>", prompt)
        self.assertIn(system_prefs, prompt)
        self.assertIn("Follow the user preferences specified above", prompt)

    def test_build_command_prompt_without_system_preferences(self):
        """Test command prompt building without system prompt preferences."""
        builder = build_command_prompt(
            "macOS 15.5", "fish", explain=False, system_prompt_preferences=""
        )

        prompt = builder.format(wish="list files")

        # Should not contain user preferences section
        self.assertNotIn("<user_preferences>", prompt)
        self.assertNotIn("Follow the user preferences specified above", prompt)

    def test_build_command_prompt_empty_system_preferences(self):
        """Test command prompt building with empty/whitespace system preferences."""
        # Test with empty string
        builder1 = build_command_prompt(
            "macOS 15.5", "fish", system_prompt_preferences=""
        )
        prompt1 = builder1.format(wish="test")
        self.assertNotIn("<user_preferences>", prompt1)

        # Test with whitespace only
        builder2 = build_command_prompt(
            "macOS 15.5", "fish", system_prompt_preferences="   \n  "
        )
        prompt2 = builder2.format(wish="test")
        self.assertNotIn("<user_preferences>", prompt2)

    def test_build_command_prompt_system_preferences_with_whitespace(self):
        """Test command prompt building with system preferences that have leading/trailing whitespace."""
        system_prefs = "  Use modern tools when possible  \n"

        builder = build_command_prompt(
            "Linux", "zsh", system_prompt_preferences=system_prefs
        )

        prompt = builder.format(wish="test command")

        # Should strip whitespace and include preferences
        self.assertIn("<user_preferences>", prompt)
        self.assertIn("Use modern tools when possible", prompt)
        # Should not include the extra whitespace
        self.assertNotIn("  Use modern tools when possible  ", prompt)

    def test_build_command_prompt_xml_structure(self):
        """Test that command prompt has proper XML structure."""
        builder = build_command_prompt("Windows 11", "cmd", explain=True)
        prompt = builder.format(wish="show directory contents")

        # Check for required XML tags
        required_tags = [
            "<context>",
            "</context>",
            "<operating_system>",
            "</operating_system>",
            "<shell>",
            "</shell>",
            "<request>",
            "</request>",
            "<explain>",
            "</explain>",
            "<guidelines>",
            "</guidelines>",
            "<examples>",
            "</examples>",
            "<response>",
            "</response>",
            "<command>",
            "</command>",
            "<description>",
            "</description>",
        ]

        for tag in required_tags:
            self.assertIn(tag, prompt, f"Missing required XML tag: {tag}")

    def test_prompt_builder_template_formatting_error(self):
        """Test PromptBuilder error handling for template formatting issues."""
        # Create a template that might cause formatting issues
        template = "Hello $name, your score is ${score:.2f}"
        input_variables = ["name", "score"]

        builder = PromptBuilder(template, input_variables)

        # This should work fine with safe_substitute
        result = builder.format(name="Alice", score="95.567")
        self.assertIn("Alice", result)


if __name__ == "__main__":
    unittest.main()
