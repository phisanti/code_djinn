"""
Tests for response_parser.py - LLM response parsing functionality.

These tests validate the ResponseParser class which handles parsing of LLM responses
in both XML format and fallback formats to extract commands and descriptions.
"""

import unittest

from codedjinn.core.response_parser import ResponseParser


class TestResponseParser(unittest.TestCase):
    """Test cases for ResponseParser class."""

    def test_parse_xml_response_with_command_and_description(self):
        """Test parsing XML response with both command and description."""
        xml_response = """
        <response>
        <command>ls -la</command>
        <description>Lists all files in the current directory with detailed information</description>
        </response>
        """

        command, description = ResponseParser.parse_command_response(xml_response)

        self.assertEqual(command, "ls -la")
        self.assertEqual(
            description,
            "Lists all files in the current directory with detailed information",
        )

    def test_parse_xml_response_command_only(self):
        """Test parsing XML response with command only (no description)."""
        xml_response = """
        <response>
        <command>pwd</command>
        </response>
        """

        command, description = ResponseParser.parse_command_response(xml_response)

        self.assertEqual(command, "pwd")
        self.assertIsNone(description)

    def test_parse_xml_response_multiline_command(self):
        """Test parsing XML response with multiline command."""
        xml_response = """
        <response>
        <command>find . -name "*.py" \\
        | grep -v __pycache__ \\
        | head -10</command>
        <description>Find Python files, exclude cache, show first 10</description>
        </response>
        """

        command, description = ResponseParser.parse_command_response(xml_response)

        expected_command = 'find . -name "*.py" \\\n        | grep -v __pycache__ \\\n        | head -10'
        self.assertEqual(command, expected_command)
        self.assertEqual(description, "Find Python files, exclude cache, show first 10")

    def test_parse_xml_response_with_extra_whitespace(self):
        """Test parsing XML response with extra whitespace."""
        xml_response = """
        <response>
        <command>   git status   </command>
        <description>   Show the status of the git repository   </description>
        </response>
        """

        command, description = ResponseParser.parse_command_response(xml_response)

        # Should strip whitespace
        self.assertEqual(command, "git status")
        self.assertEqual(description, "Show the status of the git repository")

    def test_parse_fallback_response_basic(self):
        """Test parsing fallback response format."""
        fallback_response = """
        Here's the command you need:
        Command: docker ps -a
        Description: Show all Docker containers
        """

        command, description = ResponseParser.parse_command_response(fallback_response)

        self.assertEqual(command, "docker ps -a")
        self.assertEqual(description, "Show all Docker containers")

    def test_parse_fallback_response_case_insensitive(self):
        """Test parsing fallback response with different cases."""
        fallback_response = """
        command: grep -r "pattern" .
        DESCRIPTION: Search for pattern in all files
        """

        command, description = ResponseParser.parse_command_response(fallback_response)

        self.assertEqual(command, 'grep -r "pattern" .')
        # The fallback parser doesn't strip the "DESCRIPTION:" prefix in uppercase
        self.assertEqual(description, "DESCRIPTION: Search for pattern in all files")

    def test_parse_fallback_response_command_only(self):
        """Test parsing fallback response with command only."""
        fallback_response = """
        The command you need is:
        Command: uname -a
        """

        command, description = ResponseParser.parse_command_response(fallback_response)

        self.assertEqual(command, "uname -a")
        self.assertIsNone(description)

    def test_parse_fallback_response_description_only(self):
        """Test parsing fallback response with description only (should fail)."""
        fallback_response = """
        This will show system information.
        Description: Display system information
        """

        with self.assertRaises(ValueError) as context:
            ResponseParser.parse_command_response(fallback_response)

        self.assertIn("Failed to extract command", str(context.exception))

    def test_parse_xml_response_malformed(self):
        """Test parsing malformed XML response falls back to line parsing."""
        malformed_xml = """
        <response>
        <command>ls -la
        <description>List files</description>
        </response>
        """

        # Should fail XML parsing and fall back to line-by-line
        # Since there's no "Command:" or "command:" line, it should fail entirely
        with self.assertRaises(ValueError):
            ResponseParser.parse_command_response(malformed_xml)

    def test_parse_complex_mixed_content(self):
        """Test parsing response with mixed content that should use XML."""
        mixed_response = """
        I'll help you with that task. Here's what you need:
        
        <response>
        <command>tar -czf backup.tar.gz /home/user/documents</command>
        <description>Create a compressed tar archive of the documents folder</description>
        </response>
        
        This command will create a gzipped tar file.
        """

        command, description = ResponseParser.parse_command_response(mixed_response)

        self.assertEqual(command, "tar -czf backup.tar.gz /home/user/documents")
        self.assertEqual(
            description, "Create a compressed tar archive of the documents folder"
        )

    def test_parse_response_empty_input(self):
        """Test parsing empty or whitespace-only input."""
        empty_inputs = ["", "   ", "\n\n\n", "\t\t"]

        for empty_input in empty_inputs:
            with self.assertRaises(ValueError):
                ResponseParser.parse_command_response(empty_input)

    def test_parse_response_no_command_found(self):
        """Test parsing response where no command can be extracted."""
        no_command_response = """
        I'm sorry, I cannot help with that request.
        This is just explanatory text with no actual command.
        Please try a different approach.
        """

        with self.assertRaises(ValueError) as context:
            ResponseParser.parse_command_response(no_command_response)

        self.assertIn("Failed to extract command", str(context.exception))

    def test_parse_xml_response_empty_command_tag(self):
        """Test parsing XML response with empty command tag."""
        xml_with_empty_command = """
        <response>
        <command></command>
        <description>This has no actual command</description>
        </response>
        """

        with self.assertRaises(ValueError):
            ResponseParser.parse_command_response(xml_with_empty_command)

    def test_parse_xml_response_whitespace_only_command(self):
        """Test parsing XML response with whitespace-only command."""
        xml_with_whitespace_command = """
        <response>
        <command>   </command>
        <description>Command is just whitespace</description>
        </response>
        """

        with self.assertRaises(ValueError):
            ResponseParser.parse_command_response(xml_with_whitespace_command)

    def test_parse_direct_xml_methods(self):
        """Test the direct XML parsing method."""
        xml_response = """
        <response>
        <command>echo "hello world"</command>
        <description>Print hello world</description>
        </response>
        """

        command, description = ResponseParser._parse_xml_response(xml_response)

        self.assertEqual(command, 'echo "hello world"')
        self.assertEqual(description, "Print hello world")

    def test_parse_direct_fallback_methods(self):
        """Test the direct fallback parsing method."""
        fallback_response = """
        command: python --version
        description: Show Python version
        """

        command, description = ResponseParser._parse_fallback_response(
            fallback_response
        )

        self.assertEqual(command, "python --version")
        self.assertEqual(description, "Show Python version")

    def test_parse_xml_response_with_special_characters(self):
        """Test parsing XML response with special characters in command."""
        xml_response = """
        <response>
        <command>grep -E "^[A-Z].*[!?.]$" file.txt</command>
        <description>Find lines starting with capital letter and ending with punctuation</description>
        </response>
        """

        command, description = ResponseParser.parse_command_response(xml_response)

        self.assertEqual(command, 'grep -E "^[A-Z].*[!?.]$" file.txt')
        self.assertEqual(
            description,
            "Find lines starting with capital letter and ending with punctuation",
        )


if __name__ == "__main__":
    unittest.main()
