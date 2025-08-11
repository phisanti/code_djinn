from typing import Optional, Tuple
from .llm_cache import get_cached_llm
from .prompt_builder import build_command_prompt
from .response_parser import ResponseParser
from ..providers.parameter_manager import ParameterManager
from ..utils import get_os_info, get_current_shell, print_text


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
        model: Optional[str] = "Qwen/QwQ-32B",
        api_key: Optional[str] = None,
        system_prompt_preferences: Optional[str] = None,
        shell_path: Optional[str] = None,
    ):
        """
        Initialize Djinn with minimal overhead.

        Args:
            os_fullname: Full OS name (auto-detected if None)
            shell: Shell type (auto-detected if None)
            provider: LLM provider
            model: Model name
            api_key: API key
            system_prompt_preferences: Additional user preferences for prompts
            shell_path: Full path to shell executable
        """
        # Auto-detect system info if not provided (cached in utils)
        if os_fullname is None:
            detected_os, _ = get_os_info()
            os_fullname = detected_os

        if shell is None:
            shell = get_current_shell()

        # Store minimal config - defer expensive operations
        self.os_fullname = os_fullname
        self.shell = shell
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.system_prompt_preferences = system_prompt_preferences or ""
        self.shell_path = shell_path or ""

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

    def test_prompt(self, wish: str, explain: bool = False) -> str:
        """
        Build and return the formatted prompt for testing.

        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation

        Returns:
            The formatted prompt string
        """
        prompt_builder = build_command_prompt(
            self.os_fullname, self.shell, explain, self.system_prompt_preferences
        )
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
        if hasattr(llm, "invoke"):
            return llm.invoke(prompt_text)
        elif hasattr(llm, "__call__"):
            return llm(prompt_text)
        else:
            raise RuntimeError("LLM instance doesn't support invoke or call methods")

    def ask_and_execute(
        self,
        wish: str,
        explain: bool = False,
        llm_verbose: bool = False,
        auto_confirm: bool = False,
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
        execution_mode = ExecutionMode(
            llm,
            self.provider,
            self.os_fullname,
            self.shell,
            self.system_prompt_preferences,
            self.shell_path,
        )

        return execution_mode.ask_and_execute(wish, explain, llm_verbose, auto_confirm)

    def start_chat(self, session_id: Optional[str] = None) -> None:
        """
        Start interactive chat mode with session support.

        Args:
            session_id: Optional session ID for resuming conversations
        """
        from ..modes.chat_mode import ChatMode

        # Use cached LLM for maximum speed
        llm = self._get_llm()

        chat_mode = ChatMode(
            llm,
            self.provider,
            self.os_fullname,
            self.shell,
            self.system_prompt_preferences,
            self.shell_path,
        )

        # Start the chat session
        chat_mode.start_chat_session()

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
            system_prompt_preferences=config.get("SYSTEM_PROMPT_PREFERENCES", ""),
            shell_path=config.get("SHELL_PATH", ""),
        )
