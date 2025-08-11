"""
Tests for utils.py - Utility functions for OS detection, text formatting, and shell operations.

These tests validate utility functions that support the core CodeDjinn functionality,
including OS detection, colored text output, and shell path detection.
"""

import unittest
from unittest.mock import patch, MagicMock
import platform
import io

from codedjinn.utils import (
    get_os_info,
    get_colored_text,
    print_text,
    get_shell_path,
    TEXT_COLOR_MAPPING,
)


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""

    def test_get_os_info_macos(self):
        """Test OS detection for macOS."""
        with patch("platform.system", return_value="Darwin"):
            with patch("platform.platform", return_value="macOS-15.5-arm64"):
                os_family, os_fullname = get_os_info()

                self.assertEqual(os_family, "MacOS")
                self.assertEqual(os_fullname, "macOS-15.5-arm64")

    def test_get_os_info_linux(self):
        """Test OS detection for Linux."""
        with patch("platform.system", return_value="Linux"):
            with patch(
                "platform.freedesktop_os_release",
                return_value={"PRETTY_NAME": "Ubuntu 22.04 LTS"},
            ):
                os_family, os_fullname = get_os_info()

                self.assertEqual(os_family, "Linux")
                self.assertEqual(os_fullname, "Ubuntu 22.04 LTS")

    def test_get_os_info_linux_fallback(self):
        """Test OS detection for Linux when freedesktop_os_release fails."""
        with patch("platform.system", return_value="Linux"):
            with patch("platform.freedesktop_os_release", side_effect=AttributeError):
                with patch("platform.platform", return_value="Linux-5.15.0-generic"):
                    os_family, os_fullname = get_os_info()

                    self.assertEqual(os_family, "Linux")
                    self.assertEqual(os_fullname, "Linux-5.15.0-generic")

    def test_get_os_info_windows(self):
        """Test OS detection for Windows."""
        with patch("platform.system", return_value="Windows"):
            with patch("platform.platform", return_value="Windows-10-10.0.19042"):
                os_family, os_fullname = get_os_info()

                self.assertEqual(os_family, "Windows")
                self.assertEqual(os_fullname, "Windows-10-10.0.19042")

    def test_get_os_info_unknown(self):
        """Test OS detection for unknown system."""
        with patch("platform.system", return_value="UnknownOS"):
            os_family, os_fullname = get_os_info()

            self.assertIsNone(os_family)
            self.assertIsNone(os_fullname)

    def test_get_os_info_exception_handling(self):
        """Test OS detection with exception during platform detection."""
        with patch("platform.system", side_effect=Exception("Platform error")):
            os_family, os_fullname = get_os_info()

            self.assertIsNone(os_family)
            self.assertIsNone(os_fullname)

    def test_get_colored_text_valid_colors(self):
        """Test colored text generation with valid colors."""
        test_text = "Hello World"

        # Test each color in the mapping
        for color_name, color_code in TEXT_COLOR_MAPPING.items():
            colored_text = get_colored_text(test_text, color_name)

            # Should contain the color code and the text
            self.assertIn(color_code, colored_text)
            self.assertIn(test_text, colored_text)
            # Should have ANSI escape sequences
            self.assertTrue(colored_text.startswith("\u001b["))
            self.assertTrue(colored_text.endswith("\u001b[0m"))

    def test_get_colored_text_invalid_color(self):
        """Test colored text generation with invalid color."""
        with self.assertRaises(ValueError) as context:
            get_colored_text("test", "invalid_color")

        self.assertIn("Unsupported color", str(context.exception))
        self.assertIn("invalid_color", str(context.exception))

    def test_print_text_no_color(self):
        """Test print_text function without color."""
        test_text = "Test message"

        # Capture stdout
        with patch("builtins.print") as mock_print:
            print_text(test_text)

            # Verify print was called with plain text
            mock_print.assert_called_once_with(test_text, end="", file=None)

    def test_print_text_with_color(self):
        """Test print_text function with color."""
        test_text = "Test message"

        with patch("builtins.print") as mock_print:
            print_text(test_text, color="blue")

            # Should have been called once
            mock_print.assert_called_once()

            # Get the actual text that was printed
            printed_text = mock_print.call_args[0][0]

            # Should contain color codes and the original text
            self.assertIn(test_text, printed_text)
            self.assertIn("36;1", printed_text)  # Blue color code

    def test_print_text_invalid_color_fallback(self):
        """Test print_text function falls back to plain text with invalid color."""
        test_text = "Test message"

        with patch("builtins.print") as mock_print:
            print_text(test_text, color="invalid_color")

            # Should print plain text when color is invalid
            mock_print.assert_called_once_with(test_text, end="", file=None)

    def test_print_text_with_file_parameter(self):
        """Test print_text function with file parameter."""
        test_text = "Test message"
        mock_file = MagicMock()

        with patch("builtins.print") as mock_print:
            print_text(test_text, file=mock_file)

            # Should print to the specified file
            mock_print.assert_called_once_with(test_text, end="", file=mock_file)
            # Should flush the file
            mock_file.flush.assert_called_once()

    def test_get_shell_path_existing_shell(self):
        """Test shell path detection for existing shell."""
        # Most systems should have bash
        with patch("shutil.which", return_value="/bin/bash") as mock_which:
            shell_path = get_shell_path("bash")

            self.assertEqual(shell_path, "/bin/bash")
            mock_which.assert_called_once_with("bash")

    def test_get_shell_path_nonexistent_shell(self):
        """Test shell path detection for non-existent shell."""
        with patch("shutil.which", return_value=None) as mock_which:
            shell_path = get_shell_path("nonexistent_shell")

            self.assertIsNone(shell_path)
            mock_which.assert_called_once_with("nonexistent_shell")

    def test_text_color_mapping_completeness(self):
        """Test that TEXT_COLOR_MAPPING contains expected colors."""
        expected_colors = ["blue", "yellow", "pink", "green", "red"]

        for color in expected_colors:
            self.assertIn(color, TEXT_COLOR_MAPPING, f"Missing color: {color}")

        # Verify all values are valid ANSI color codes
        for color_name, color_code in TEXT_COLOR_MAPPING.items():
            self.assertIsInstance(color_code, str)
            self.assertTrue(len(color_code) > 0)


if __name__ == "__main__":
    unittest.main()
