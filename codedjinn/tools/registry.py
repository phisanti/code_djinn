from pathlib import Path
from typing import List

from agno.tools.shell import ShellTools


def build_shell_tools(workdir: Path | None = None) -> ShellTools:
    """Create shell tools scoped to the given working directory."""
    if workdir is None:
        return ShellTools()
    return ShellTools(base_dir=str(workdir))


def get_tools(config: dict | None = None) -> List[object]:
    """
    Return the list of tools to attach to the agent.

    For now, we only provide shell execution. Config toggles can be
    added later to expand/disable tools.
    """
    _ = config  # placeholder to appease linters until we add toggles
    return [build_shell_tools()]
