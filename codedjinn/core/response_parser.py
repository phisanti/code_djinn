from typing import Optional, Tuple
import re
from re import DOTALL


class ResponseParser:
    """
    Handles parsing of LLM responses, supporting both XML and fallback formats.
    """
    
    @staticmethod
    def parse_command_response(response_text: str) -> Tuple[str, Optional[str]]:
        """
        Parse LLM response to extract command and optional description.
        
        Args:
            response_text: Raw response text from the LLM
            
        Returns:
            Tuple of (command, description) where description may be None
            
        Raises:
            ValueError: If no command can be extracted from the response
        """
        # First try XML parsing
        command, description = ResponseParser._parse_xml_response(response_text)
        
        if command:
            return command, description
        
        # Fallback to line-by-line parsing
        command, description = ResponseParser._parse_fallback_response(response_text)
        
        if command:
            return command, description
        
        raise ValueError("Failed to extract command from LLM response")
    
    @staticmethod
    def _parse_xml_response(response_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse XML-structured response.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Tuple of (command, description) or (None, None) if parsing fails
        """
        command_match = re.search(r"<command>(.*?)</command>", response_text, DOTALL)
        description_match = re.search(r"<description>(.*?)</description>", response_text, DOTALL)
        
        if command_match:
            command = command_match.group(1).strip()
            description = description_match.group(1).strip() if description_match else None
            return command, description
        
        return None, None
    
    @staticmethod
    def _parse_fallback_response(response_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse response using fallback line-by-line method.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Tuple of (command, description) or (None, None) if parsing fails
        """
        response_items = response_text.strip().split("\n")
        command = None
        description = None
        
        for element in response_items:
            element_lower = element.lower()
            if "command:" in element_lower:
                command = element.replace("Command:", "").replace("command:", "").strip()
            elif "description:" in element_lower:
                description = element.replace("Description:", "").replace("description:", "").strip()
        
        return command, description
    
    @staticmethod
    def parse_chat_response(response_text: str) -> dict:
        """
        Parse chat response that may contain questions, commands, or both.
        
        Expected XML format:
        <answer>conversational response</answer>
        <command>shell_command</command>
        <description>what the command does</description>
        
        Args:
            response_text: Raw response text from the LLM
            
        Returns:
            dict with keys: 'type', 'answer', 'command', 'description'
        """
        result = {
            'type': 'answer',  # Default to conversational
            'answer': None,
            'command': None, 
            'description': None
        }
        
        # Parse XML tags using existing regex patterns
        answer_match = re.search(r"<answer>(.*?)</answer>", response_text, DOTALL)
        command_match = re.search(r"<command>(.*?)</command>", response_text, DOTALL)
        description_match = re.search(r"<description>(.*?)</description>", response_text, DOTALL)
        
        if answer_match:
            result['answer'] = answer_match.group(1).strip()
        
        if command_match:
            result['command'] = command_match.group(1).strip()
            result['type'] = 'command' if not answer_match else 'both'
            
            if description_match:
                result['description'] = description_match.group(1).strip()
        
        # Fallback for non-XML responses
        if not answer_match and not command_match:
            result['answer'] = response_text.strip()
        
        return result