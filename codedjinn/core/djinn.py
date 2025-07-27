from typing import Optional, Tuple
from .llm_cache import get_cached_llm
from .prompt_builder import build_command_prompt
from .response_parser import ResponseParser
from ..providers.parameter_manager import ParameterManager
from ..utils import get_os_info, print_text


class Djinn:
    """
    High-performance Djinn with aggressive caching and optimizations.
    Designed for sub-100ms startup times.
    """
    
    def __init__(
        self,
        os_fullname: Optional[str] = None,
        shell: Optional[str] = None,
        provider: Optional[str] = "deepinfra",
        model: Optional[str] = "mistralai/Mistral-7B-Instruct-v0.1",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Djinn with minimal overhead.
        
        Args:
            os_fullname: Full OS name (auto-detected if None)
            shell: Shell type (auto-detected if None)
            provider: LLM provider
            model: Model name
            api_key: API key
        """
        # Auto-detect system info if not provided (cached in utils)
        if os_fullname is None or shell is None:
            detected_os, detected_shell = get_os_info()
            os_fullname = os_fullname or detected_os
            shell = shell or detected_shell
        
        # Store minimal config - defer expensive operations
        self.os_fullname = os_fullname
        self.shell = shell
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        
        # Lazy-initialized components
        self._llm = None
        self._parameter_manager = None
    
    def _get_llm(self):
        """Lazy-load LLM with caching for maximum performance."""
        if self._llm is None:
            # Use cached LLM client (huge performance gain)
            self._llm = get_cached_llm(self.provider, self.model, self.api_key)
        return self._llm
    
    def _get_parameter_manager(self):
        """Lazy-load parameter manager."""
        if self._parameter_manager is None:
            self._parameter_manager = ParameterManager()
        return self._parameter_manager
    
    def ask(
        self, 
        wish: str, 
        explain: bool = False, 
        llm_verbose: bool = False
    ) -> Tuple[str, Optional[str]]:
        """
        Generate a command using cached LLM for maximum speed.
        
        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation
            llm_verbose: Whether to show verbose LLM output
            
        Returns:
            Tuple of (command, description)
        """
        try:
            # Get cached LLM (fast after first call)
            llm = self._get_llm()
            
            # Apply provider-specific parameters
            param_manager = self._get_parameter_manager()
            param_manager.apply_parameters(llm, self.provider, explain)
            
            # Build prompt (fast - no langchain)
            prompt_builder = build_command_prompt(self.os_fullname, self.shell, explain)
            prompt_text = prompt_builder.format(wish=wish)
            
            if llm_verbose:
                print_text("\nSending prompt to LLM:", "yellow")
                print_text(prompt_text, "blue")
            
            # Make LLM request
            response = self._invoke_llm(llm, prompt_text)
            
            # Extract content from response
            if hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Parse response (fast)
            command, description = ResponseParser.parse_command_response(response_text)
            
            return command, description
            
        except Exception as e:
            raise RuntimeError(f"Error generating command: {str(e)}")
    
    def test_prompt(self, wish: str, explain: bool = False) -> str:
        """
        Build and return the formatted prompt for testing.
        
        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation
            
        Returns:
            The formatted prompt string
        """
        prompt_builder = build_command_prompt(self.os_fullname, self.shell, explain)
        return prompt_builder.format(wish=wish)
    
    def _invoke_llm(self, llm, prompt_text: str) -> str:
        """
        Invoke the LLM with optimized request handling.
        
        Args:
            llm: The LLM instance
            prompt_text: The formatted prompt
            
        Returns:
            LLM response
        """
        # Use the most direct invocation method for speed
        if hasattr(llm, 'invoke'):
            return llm.invoke(prompt_text)
        elif hasattr(llm, '__call__'):
            return llm(prompt_text)
        else:
            raise RuntimeError("LLM instance doesn't support invoke or call methods")
    
    def ask_and_execute(
        self, 
        wish: str, 
        explain: bool = False, 
        llm_verbose: bool = False,
        auto_confirm: bool = False
    ) -> Tuple[str, Optional[str], bool, str, str]:
        """
        Generate and execute a command with confirmation (execution mode).
        
        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation
            llm_verbose: Whether to show verbose LLM output
            auto_confirm: Skip execution confirmation
            
        Returns:
            Tuple of (command, description, execution_success, stdout, stderr)
        """
        from ..modes.execution_mode import ExecutionMode
        
        # Create execution mode with cached LLM
        llm = self._get_llm()
        execution_mode = ExecutionMode(llm, self.provider, self.os_fullname, self.shell)
        
        return execution_mode.ask_and_execute(wish, explain, llm_verbose, auto_confirm)
    
    @classmethod
    def from_config(cls, config: dict, api_key: str):
        """
        Fast factory method to create Djinn from configuration.
        
        Args:
            config: Configuration dictionary
            api_key: API key for the provider
            
        Returns:
            Djinn instance
        """
        return cls(
            os_fullname=config["OS_FULLNAME"],
            shell=config["SHELL"],
            provider=config["LLM_PROVIDER"],
            model=config["LLM_MODEL"],
            api_key=api_key,
        )