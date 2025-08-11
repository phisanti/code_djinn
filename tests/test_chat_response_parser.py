#!/usr/bin/env python3

import unittest
from codedjinn.core.response_parser import ResponseParser


class TestChatResponseParser(unittest.TestCase):
    """Test cases for the new parse_chat_response method."""
    
    def test_answer_only_response(self):
        """Test parsing a response with only an answer."""
        response = "The current directory is where you are working right now."
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'answer')
        self.assertEqual(result['answer'], "The current directory is where you are working right now.")
        self.assertIsNone(result['command'])
        self.assertIsNone(result['description'])
    
    def test_command_only_response(self):
        """Test parsing a response with only a command."""
        response = "<command>ls -la</command>"
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'command')
        self.assertIsNone(result['answer'])
        self.assertEqual(result['command'], 'ls -la')
        self.assertIsNone(result['description'])
    
    def test_command_with_description(self):
        """Test parsing a response with command and description."""
        response = "<command>ls -la</command><description>List all files with details</description>"
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'command')
        self.assertIsNone(result['answer'])
        self.assertEqual(result['command'], 'ls -la')
        self.assertEqual(result['description'], 'List all files with details')
    
    def test_answer_and_command_both(self):
        """Test parsing a response with both answer and command."""
        response = "<answer>Here are the files in your directory:</answer><command>ls -la</command><description>List all files with details</description>"
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'both')
        self.assertEqual(result['answer'], 'Here are the files in your directory:')
        self.assertEqual(result['command'], 'ls -la')
        self.assertEqual(result['description'], 'List all files with details')
    
    def test_answer_and_command_no_description(self):
        """Test parsing a response with answer and command but no description."""
        response = "<answer>Let me show you the files:</answer><command>ls</command>"
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'both')
        self.assertEqual(result['answer'], 'Let me show you the files:')
        self.assertEqual(result['command'], 'ls')
        self.assertIsNone(result['description'])
    
    def test_multiline_answer(self):
        """Test parsing a multiline answer response."""
        response = """This is a multiline answer.
            It explains how to do something
            across multiple lines."""
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'answer')
        self.assertIn('multiline answer', result['answer'])
        self.assertIn('multiple lines', result['answer'])
        self.assertIsNone(result['command'])
    
    def test_multiline_xml_tags(self):
        """Test parsing XML tags that span multiple lines."""
        response = """<answer>This is a long explanation
            that spans multiple lines
            and provides detailed information.</answer>
            <command>find . -name "*.py" -type f</command>
            <description>Search for all Python files
            in the current directory and subdirectories</description>"""
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'both')
        self.assertIn('long explanation', result['answer'])
        self.assertIn('multiple lines', result['answer'])
        self.assertEqual(result['command'], 'find . -name "*.py" -type f')
        self.assertIn('Search for all Python files', result['description'])
        self.assertIn('subdirectories', result['description'])
    
    def test_complex_command_with_pipes(self):
        """Test parsing a complex command with pipes and special characters."""
        response = r'<command>ls -la | grep "\.py$" | wc -l</command><description>Count the number of Python files</description>'
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'command')
        self.assertEqual(result['command'], r'ls -la | grep "\.py$" | wc -l')
        self.assertEqual(result['description'], 'Count the number of Python files')
    
    def test_empty_response(self):
        """Test parsing an empty response."""
        response = ""
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'answer')
        self.assertEqual(result['answer'], '')
        self.assertIsNone(result['command'])
    
    def test_whitespace_only_response(self):
        """Test parsing a response with only whitespace."""
        response = "   \n\t  \n  "
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'answer')
        self.assertEqual(result['answer'], '')
        self.assertIsNone(result['command'])
    
    def test_malformed_xml_tags(self):
        """Test parsing response with malformed XML tags."""
        response = "<answer>This has unclosed answer tag <command>ls</command>"
        result = ResponseParser.parse_chat_response(response)
        
        # Should fall back to treating it as a plain answer
        self.assertEqual(result['type'], 'command')  # Because command tag is properly closed
        self.assertIsNone(result['answer'])  # Unclosed answer tag should not match
        self.assertEqual(result['command'], 'ls')
    
    def test_xml_tags_with_extra_whitespace(self):
        """Test parsing XML tags with extra whitespace."""
        response = "<answer>  This answer has extra whitespace  </answer><command>  ls -la  </command><description>  List files  </description>"
        result = ResponseParser.parse_chat_response(response)
        
        self.assertEqual(result['type'], 'both')
        self.assertEqual(result['answer'], 'This answer has extra whitespace')
        self.assertEqual(result['command'], 'ls -la')
        self.assertEqual(result['description'], 'List files')
    
    def test_case_insensitive_fallback_parsing(self):
        """Test that the original command parsing still works as fallback."""
        # This tests the existing parse_command_response functionality is not broken
        response = "Command: ls -la\nDescription: List all files"
        # Use the original parser to make sure it still works
        command, description = ResponseParser.parse_command_response(response)
        
        self.assertEqual(command, 'ls -la')
        self.assertEqual(description, 'List all files')


if __name__ == '__main__':
    unittest.main()