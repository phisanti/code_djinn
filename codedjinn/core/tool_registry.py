"""
Tool Registry for managing Agno tools.
Provides tools appropriate for different modes (run, chat).
"""

import os
from typing import List, Dict, Optional, Any


class ToolRegistry:
    """Manages available tools for Agno agents."""

    def __init__(self, config: dict):
        """
        Initialize with system configuration.
        
        Args:
            config: System configuration dictionary
        """
        self.config = config
        self.workdir = os.getcwd()

    def get_tools_for_mode(self, mode: str) -> List[Any]:
        """
        Get tools appropriate for specified mode.
        
        Args:
            mode: Mode name ("run" or "chat")
            
        Returns:
            List of tool instances for the mode
        """
        if mode == "run":
            # Run mode: shell + file read only
            return self.get_base_tools()
        elif mode == "chat":
            # Chat mode: add git helpers and more interactive tools
            return self.get_base_tools() + self.get_chat_tools()
        else:
            return self.get_base_tools()

    def get_base_tools(self) -> List[Any]:
        """
        Get base shell and filesystem tools.
        
        Returns:
            List of base tool instances
        """
        tools = []
        
        try:
            # Try to import and create Agno tools
            import sys
            sys.path.append('agno/libs/agno')
            
            # Import shell tools
            from agno.tools.shell import ShellTools
            shell_tool = ShellTools(
                base_dir=self.workdir,
                enable_run_shell_command=True
            )
            tools.append(shell_tool)
            
            # Import filesystem tools  
            from agno.tools.local_file_system import LocalFileSystemTools
            fs_tool = LocalFileSystemTools(
                target_directory=self.workdir,
                enable_write_file=False  # Read-only for safety
            )
            tools.append(fs_tool)
            
        except ImportError as e:
            # Fallback: create placeholder tools for now
            # This allows the system to work even if Agno tools aren't fully available
            print(f"Warning: Could not import Agno tools ({e}). Using placeholder tools.")
            tools.extend(self.get_placeholder_tools())
        
        return tools

    def get_chat_tools(self) -> List[Any]:
        """
        Get additional tools for chat mode.
        
        Returns:
            List of chat-specific tool instances
        """
        tools = []
        
        # Git helpers for chat mode
        tools.extend(self.get_git_tools())
        
        # Web search (if enabled in future)
        # tools.extend(self.get_web_tools())
        
        return tools

    def get_git_tools(self) -> List[Any]:
        """
        Get git-specific helper tools.
        
        Returns:
            List of git tool instances
        """
        # Simple git helpers as functions
        # Can be expanded in Phase 3
        return []

    def get_placeholder_tools(self) -> List[Any]:
        """
        Get placeholder tools when Agno tools aren't available.
        
        Returns:
            List of placeholder tool instances
        """
        # Create simple placeholder tools that can be used for testing
        # These will be replaced with real Agno tools once dependencies are resolved
        return [
            PlaceholderShellTool(self.workdir),
            PlaceholderFileSystemTool(self.workdir),
        ]

    def get_optional_tools(self, flags: dict) -> List[Any]:
        """
        Get optional tools based on feature flags.
        
        Args:
            flags: Feature flags dictionary
            
        Returns:
            List of optional tool instances
        """
        tools = []

        # Web search (if enabled in Phase 3)
        if flags.get("enable_web_search"):
            try:
                # from agno.tools.duckduckgo import DuckDuckGoTools
                # tools.append(DuckDuckGoTools())
                pass
            except ImportError:
                pass

        return tools

    def get_available_tools(self) -> Dict[str, List[str]]:
        """
        Get information about available tools.
        
        Returns:
            Dictionary mapping mode names to lists of available tool names
        """
        return {
            "run": ["shell", "filesystem"],
            "chat": ["shell", "filesystem", "git_helpers"],
        }


class PlaceholderShellTool:
    """Placeholder shell tool for testing when Agno tools aren't available."""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.name = "shell"
    
    def run_command(self, command: str) -> str:
        """Placeholder method."""
        return f"Placeholder: would run '{command}' in {self.base_dir}"


class PlaceholderFileSystemTool:
    """Placeholder filesystem tool for testing when Agno tools aren't available."""
    
    def __init__(self, target_directory: str):
        self.target_directory = target_directory
        self.name = "filesystem"
    
    def read_file(self, path: str) -> str:
        """Placeholder method."""
        return f"Placeholder: would read file '{path}' from {self.target_directory}"
