from agno.agent import Agent

from codedjinn.core.configs import (
    AgentSettings,
    ModelConfig,
    get_agent_settings,
    get_model_config,
    load_raw_config,
)
from codedjinn.core.parser import parse_response
from codedjinn.providers.model import build_model
from codedjinn.tools.registry import get_tools
from codedjinn.prompts.system_prompt import get_system_prompt


def get_agent(
    config: dict | None = None,
    *,
    include_tools: bool = False,
    instructions_override: str | None = None,
) -> Agent:
    """
    Build a minimal Agno agent using the stored configuration.
    """
    raw = config or load_raw_config()

    model_cfg: ModelConfig = get_model_config(raw)
    agent_settings: AgentSettings = get_agent_settings(raw)

    model = build_model(
        provider=model_cfg.provider,
        model_id=model_cfg.model,
        api_key=model_cfg.api_key,
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
        timeout=model_cfg.timeout,
    )

    instructions = instructions_override or agent_settings.instructions
    if not instructions:
        instructions = get_system_prompt()

    tools = get_tools(raw) if include_tools else []

    return Agent(
        model=model,
        instructions=instructions,
        markdown=agent_settings.markdown,
        add_history_to_context=agent_settings.add_history_to_context,
        tools=tools,
    )


def run_and_parse(
    prompt: str = "hello",
    config: dict | None = None,
    *,
    include_tools: bool = False,
    instructions_override: str | None = None,
) -> dict[str, str]:
    """
    Convenience helper to run a prompt and parse out minimal fields.
    """
    agent = get_agent(
        config,
        include_tools=include_tools,
        instructions_override=instructions_override,
    )
    raw = agent.run(prompt)
    return parse_response(raw)


if __name__ == "__main__":
    # This will reach out to the configured provider. Use sparingly.
    print(run_and_parse("hello"))
