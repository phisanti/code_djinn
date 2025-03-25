from typing import Optional, Tuple, Union, Dict, Any
from dotenv import dotenv_values, set_key
from langchain.prompts import PromptTemplate
from .utils import get_os_info, print_text
from .llmfactory import LLMFactory
from .prompt_template import get_command_prompt_template
from re import search, DOTALL


class djinn:
    """
    The djinn class is the main class of the codedjinn package. It is used to interact with LLMs and generate commands.
    """

    def __init__(
        self,
        os_fullname: Optional[str] = None,
        shell: Optional[str] = None,
        provider: Optional[str] = "deepinfra",
        model: Optional[str] = "mistralai/Mistral-7B-Instruct-v0.1",
        api: Optional[str] = None,
    ):
        """
        The constructor for the djinn class. It takes the following parameters:
        os_fullname: The full name of the operating system. If not provided, it will be automatically detected.
        shell: The shell used by the user. If not provided, it will be automatically detected.
        provider: The LLM provider to use (deepinfra, mistralai, gemini)
        model: The model to use
        api: The API key for the LLM provider. If not provided, it will be automatically detected from the .env file.
        """

        if os_fullname is None or shell is None:
            os_fullname, shell = get_os_info()

        # Use provided API key if available, otherwise load from .env
        if api is None:
            config = dotenv_values()
            api_key_map = {
                "deepinfra": "DEEPINFRA_API_TOKEN",
                "mistralai": "MISTRAL_API_KEY",
                "gemini": "GEMINI_API_KEY",
            }

            api_key_env = api_key_map.get(provider.lower())
            if api_key_env and api_key_env in config:
                api = config[api_key_env]
            else:
                raise ValueError(
                    f"No API key provided and {api_key_env} not found in .env file"
                )

        self.os_fullname = os_fullname
        self.shell = shell
        self.provider = provider.lower()
        self.model = model

        # Create LLM using factory for lazy loading
        self.llm = LLMFactory().create_llm(provider, model, api)

    def _build_prompt(self, explain: bool = False):
        """
        This function builds the prompt for the LLM. It takes the following parameters:
        explain: A boolean value that indicates whether the user wants to provide an explanation of how the command works. If True, the prompt will include a description of the command.
        """
        template = get_command_prompt_template(self.os_fullname, self.shell, explain)
        prompt_variables = ["wish"]
        prompt = PromptTemplate(template=template, input_variables=prompt_variables)
        return prompt

    def test_prompt(self, wish: str, explain: bool = False):
        """
        This function builds the prompt for the LLM. It takes the following parameters:
        wish: The command the user wants to generate.
        explain: A boolean value that indicates whether the user wants to provide an explanation of how the command works. If True, the prompt will include a description of the command.
        """
        prompt = self._build_prompt(explain)
        promt_text = prompt.format(wish=wish)

        return promt_text

    def ask(
        self, wish: str, explain: bool = False, llm_verbose: bool = False
    ) -> Union[Tuple[str, Optional[str]], str]:
        """
        This function generates a command using the LLM. It takes the following parameters:
        wish: The command the user wants to generate.
        explain: A boolean value that indicates whether the user wants to provide an explanation of how the command works. If True, the prompt will include a description of the command.
        llm_verbose: A boolean value that indicates whether the user wants to see the output of the LLM model. If True, the output of the LLM model will be printed.

        Returns:
            Either a tuple of (command, description) or just the command string if no description is available
        """

        # Set model parameters based on provider
        if self.provider == "deepinfra":
            max_tokens = 1000 if explain else 250
            self.llm.model_kwargs = {
                "temperature": 0.2,
                "repetition_penalty": 1.2,
                "max_new_tokens": max_tokens,
                "top_p": 0.9,
            }
        elif self.provider == "mistralai":
            self.llm.model_kwargs = {
                "temperature": 0.2,
                "max_tokens": 1000 if explain else 250,
            }
        elif self.provider == "gemini":
            self.llm.model_kwargs = {
                "temperature": 0.2,
                "max_output_tokens": 1000 if explain else 250,
            }

        prompt = self._build_prompt(explain)

        try:
            # Create a runnable sequence using the modern pipe syntax
            chain = prompt | self.llm

            # If verbose is enabled, print the inputs and outputs
            if llm_verbose:
                print_text("\nSending prompt to LLM:", "yellow")
                print_text(prompt.format(wish=wish), "blue")
            response = chain.invoke({"wish": wish})

            # Extract the content from the response
            if hasattr(response, "content"):
                # For chat models that return a message
                response_text = response.content
            else:
                # For completion models that return text directly
                response_text = response

            # Parse XML response
            command_match = search(r"<command>(.*?)</command>", response_text, DOTALL)
            description_match = search(
                r"<description>(.*?)</description>", response_text, DOTALL
            )

            if not command_match:
                responses_items = response_text.strip().split("\n")
                command = None
                description = None
                for element in responses_items:
                    if "command:" in element.lower():
                        command = element.replace("Command:", "").strip()
                    elif "description:" in element.lower():
                        description = element.replace("Description:", "").strip()

                if command is None:
                    raise ValueError("Failed to extract command from LLM response")

                return command, description

            command = command_match.group(1).strip()
            description = (
                description_match.group(1).strip() if description_match else None
            )

            return command, description

        except Exception as e:
            raise RuntimeError(f"Error generating command: {str(e)}")
