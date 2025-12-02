"""
Agent Service for managing Agno agent lifecycle and configuration.
Handles model creation, agent initialization, and caching.
"""

import os
from typing import Optional, Dict, Any
from .tool_registry import ToolRegistry


class AgentService:
    """Manages Agno agent lifecycle and configuration."""

    def __init__(self, config: dict, tool_registry: ToolRegistry):
        """
        Initialize with configuration and tool registry.
        
        Args:
            config: System configuration dictionary
            tool_registry: ToolRegistry instance for managing tools
        """
        self.config = config
        self.tool_registry = tool_registry
        self._agents = {}  # Cache for created agents

    def get_agent(self, mode: str = "run") -> Any:
        """
        Get or create agent for specified mode.
        
        Args:
            mode: Mode name ("run" or "chat")
            
        Returns:
            Agent instance for the mode
        """
        if mode not in self._agents:
            tools = self.tool_registry.get_tools_for_mode(mode)
            self._agents[mode] = self.create_agent(mode, tools)
        return self._agents[mode]

    def create_agent(self, mode: str, tools: list) -> Any:
        """
        Create new Agno agent instance.
        
        Args:
            mode: Mode name
            tools: List of tools for the agent
            
        Returns:
            Agent instance
        """
        try:
            # Try to create real Agno agent
            model = self.create_model()
            instructions = self.get_instructions(mode)
            
            import sys
            sys.path.append('agno/libs/agno')
            from agno.agent import Agent
            
            return Agent(
                model=model,
                instructions=instructions,
                tools=tools,
                markdown=False,  # Plain text output
            )
            
        except ImportError as e:
            # Fallback to placeholder agent
            print(f"Warning: Could not create Agno agent ({e}). Using placeholder agent.")
            return PlaceholderAgent(mode, tools, self.config)

    def create_model(self) -> Any:
        """
        Create model instance based on provider configuration.
        
        Returns:
            Model instance
        """
        provider = self.config.get("LLM_PROVIDER", "gemini").lower()
        model_name = self.config.get("LLM_MODEL", "gemini-2.5-flash")
        temperature = float(self.config.get("AGENT_TEMPERATURE", "0.15"))

        try:
            import sys
            sys.path.append('agno/libs/agno')
            
            if provider == "gemini":
                api_key = self.config.get("GEMINI_API_KEY")
                from agno.models.google import Gemini
                return Gemini(
                    id=model_name,
                    api_key=api_key,
                    temperature=temperature,
                )
            elif provider == "mistralai":
                api_key = self.config.get("MISTRAL_API_KEY")
                from agno.models.mistral import MistralChat
                return MistralChat(
                    id=model_name,
                    api_key=api_key,
                    temperature=temperature,
                )
            else:
                # Fallback to Gemini
                api_key = self.config.get("GEMINI_API_KEY")
                from agno.models.google import Gemini
                return Gemini(
                    id="gemini-2.5-flash",
                    api_key=api_key,
                    temperature=temperature,
                )
                
        except ImportError:
            # Return placeholder model
            return PlaceholderModel(provider, model_name, temperature)

    def get_instructions(self, mode: str) -> str:
        """
        Get mode-specific agent instructions.
        
        Args:
            mode: Mode name
            
        Returns:
            Instructions string for the agent
        """
        os_fullname = self.config.get("OS_FULLNAME", "Unknown OS")
        shell = self.config.get("SHELL", "bash")
        prefs = self.config.get("SYSTEM_PROMPT_PREFERENCES", "")

        base = f"""You are a CLI command generator for {os_fullname} using {shell}.

Generate concise, safe shell commands based on user requests.
Output ONLY the command, no explanations unless explicitly asked.

Current directory: {os.getcwd()}
{prefs}"""

        if mode == "run":
            return base + "\n\nProvide single-line commands optimized for immediate execution."
        elif mode == "chat":
            return base + "\n\nYou can have conversations and generate commands when asked."
        else:
            return base

    def clear_cache(self):
        """Clear cached agents for fresh initialization."""
        self._agents = {}

    def get_agent_info(self) -> dict:
        """
        Get information about current agents.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "cached_agents": list(self._agents.keys()),
            "provider": self.config.get("LLM_PROVIDER", "unknown"),
            "model": self.config.get("LLM_MODEL", "unknown"),
            "temperature": self.config.get("AGENT_TEMPERATURE", "0.15"),
        }


class PlaceholderAgent:
    """Placeholder agent for testing when Agno isn't fully available."""
    
    def __init__(self, mode: str, tools: list, config: dict):
        self.mode = mode
        self.tools = tools
        self.config = config
        self.name = f"placeholder_{mode}_agent"
    
    def run(self, prompt: str) -> "PlaceholderResponse":
        """Placeholder run method."""
        # Simple command generation based on prompt
        if "list" in prompt.lower() or "ls" in prompt.lower():
            command = "ls -la"
        elif "git" in prompt.lower():
            command = "git status"
        elif "find" in prompt.lower():
            command = "find . -name '*.py'"
        else:
            command = f"echo 'Generated command for: {prompt}'"
        
        return PlaceholderResponse(command)


class PlaceholderResponse:
    """Placeholder response object."""
    
    def __init__(self, content: str):
        self.content = content


class PlaceholderModel:
    """Placeholder model for testing."""
    
    def __init__(self, provider: str, model_name: str, temperature: float):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.name = f"placeholder_{provider}_{model_name}"
