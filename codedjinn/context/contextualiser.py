"""Context orchestration - assembles all sources and formats to XML.

This module:
1. Calls all context source detectors
2. Formats each context into XML
3. Returns assembled context object with lazy XML generation
"""

from typing import Optional, Dict, Any
from codedjinn.context.sources.project import (
    get_project_detector,
    LocalProjectContext
)
from codedjinn.context.sources.shell import (
    get_shell_context,
    SystemContext,
    ShellHistContext
)
from codedjinn.context.parser import escape_xml_content


class ContextualiserResult:
    """
    Result from contextualiser containing all assembled context.

    This is the single source of truth passed to prompt builders.
    Uses lazy properties to avoid building XML that won't be used.
    """

    def __init__(
        self,
        system_context: SystemContext,
        shellhist_context: ShellHistContext,
        localproject_context: Optional[LocalProjectContext],
        session_context: Optional[Dict[str, Any]],
        cwd: str
    ):
        self.system_context = system_context
        self.shellhist_context = shellhist_context
        self.localproject_context = localproject_context
        self.session_context = session_context
        self.cwd = cwd

        # Pre-compute XML sections for performance (lazy)
        self._system_xml = None
        self._shellhist_xml = None
        self._project_xml = None
        self._session_xml = None
        self._capabilities_xml = None

    @property
    def system_xml(self) -> str:
        """Lazy-build system context XML."""
        if self._system_xml is None:
            self._system_xml = build_system_context_xml(
                self.system_context,
                self.cwd
            )
        return self._system_xml

    @property
    def shellhist_xml(self) -> str:
        """Lazy-build shell history XML."""
        if self._shellhist_xml is None:
            self._shellhist_xml = build_shellhist_context_xml(
                self.shellhist_context
            )
        return self._shellhist_xml

    @property
    def project_xml(self) -> str:
        """Lazy-build local project context XML."""
        if self._project_xml is None:
            if self.localproject_context:
                self._project_xml = build_localproject_context_xml(
                    self.localproject_context
                )
            else:
                self._project_xml = ""
        return self._project_xml

    @property
    def session_xml(self) -> str:
        """Lazy-build session context XML."""
        if self._session_xml is None:
            if self.session_context:
                self._session_xml = build_session_context_xml(
                    self.session_context
                )
            else:
                self._session_xml = ""
        return self._session_xml

    @property
    def capabilities_xml(self) -> str:
        """Lazy-build Code Djinn capabilities XML."""
        if self._capabilities_xml is None:
            self._capabilities_xml = build_capabilities_xml()
        return self._capabilities_xml


def contextualise(
    os_name: str,
    shell: str,
    cwd: str,
    session_context: Optional[Dict[str, Any]] = None,
    include_shellhist: bool = True,
    include_localproject: bool = True
) -> ContextualiserResult:
    """
    Main entry point - gather and assemble all context.

    Args:
        os_name: OS name from config
        shell: Shell type from config
        cwd: Current working directory
        session_context: Previous command context from Session
            Expected keys: 'command', 'output', 'exit_code'
        include_shellhist: Include shell history (default: True)
        include_localproject: Include project detection (default: True)

    Returns:
        ContextualiserResult with all assembled context

    Performance:
        - Shell history: ~2ms (file read)
        - Project detection: ~0ms (cached after first call)
        - Total overhead: ~2-3ms
    """
    # 1. System context (always included)
    system_ctx, shellhist_ctx = get_shell_context(
        os_name=os_name,
        shell=shell,
        include_history=include_shellhist
    )

    # 2. Local project context (optional, usually enabled)
    localproject_ctx = None
    if include_localproject:
        detector = get_project_detector()
        localproject_ctx = detector.get_context(cwd)

    # 3. Session context (from previous Code Djinn command)
    # Just pass through - already in correct format

    return ContextualiserResult(
        system_context=system_ctx,
        shellhist_context=shellhist_ctx,
        localproject_context=localproject_ctx,
        session_context=session_context,
        cwd=cwd
    )


# ============================================================================
# XML Formatting Functions
# These are called lazily by ContextualiserResult properties
# ============================================================================

def build_system_context_xml(system_ctx: SystemContext, cwd: str) -> str:
    """
    Build <system_context> section.

    Contains: OS, shell, working directory
    """
    return f"""<system_context>
  <os>{system_ctx.os_name}</os>
  <shell>{system_ctx.shell}</shell>
  <working_directory>{cwd}</working_directory>
</system_context>"""


def build_shellhist_context_xml(hist_ctx: ShellHistContext) -> str:
    """
    Build <shellhist_context> section.

    Contains: Recent shell commands (if available)
    """
    if not hist_ctx.recent_commands:
        return ""  # Omit section if no history

    parts = ["<shellhist_context>"]
    parts.append("  <!-- Recent commands from user's shell history -->")

    for idx, cmd in enumerate(hist_ctx.recent_commands, 1):
        safe_cmd = escape_xml_content(cmd)
        parts.append(f'  <command index="{idx}">{safe_cmd}</command>')

    parts.append("</shellhist_context>")
    return "\n".join(parts)


def build_localproject_context_xml(proj_ctx: LocalProjectContext) -> str:
    """
    Build <localproject_context> section.

    Logic copied from prompts/context_builder.py:373-432
    """
    parts = ["<localproject_context>"]

    # Project type
    if proj_ctx.project_type:
        parts.append(f"  <type>{proj_ctx.project_type}</type>")

    # Key files
    if proj_ctx.key_files:
        files_str = ", ".join(proj_ctx.key_files)
        parts.append(f"  <key_files>{files_str}</key_files>")

    # Virtual environment
    if proj_ctx.virtual_env:
        parts.append(f"  <virtual_env>{proj_ctx.virtual_env}</virtual_env>")

    # Git repository info
    if proj_ctx.git_branch or proj_ctx.git_status:
        parts.append("  <git_repo>")
        if proj_ctx.git_branch:
            parts.append(f"    <git_branch>{proj_ctx.git_branch}</git_branch>")
        if proj_ctx.git_status:
            parts.append(f"    <git_status>{proj_ctx.git_status}</git_status>")
        parts.append("  </git_repo>")

    # Makefile commands
    if proj_ctx.makefile_commands:
        parts.append("  <makefile_commands>")
        for cmd_dict in proj_ctx.makefile_commands:
            cmd = cmd_dict['cmd']
            desc = cmd_dict['desc']
            if desc:
                parts.append(f"    <cmd>{cmd}: {desc}</cmd>")
            else:
                parts.append(f"    <cmd>{cmd}</cmd>")
        parts.append("  </makefile_commands>")

    parts.append("</localproject_context>")

    return "\n".join(parts)


def build_session_context_xml(session_ctx: Dict[str, Any]) -> str:
    """
    Build <session_context> section.

    Contains: Previous command + output + exit code
    Logic from prompts/context_builder.py:435-472
    """
    command = session_ctx['command']
    exit_code = session_ctx['exit_code']
    output = session_ctx['output']

    escaped = escape_xml_content(output)

    return f"""<session_context>
  <previous_command>
    <executed>{command}</executed>
    <exit_code>{exit_code}</exit_code>
    <output>
{escaped}
    </output>
  </previous_command>
  <usage_note>
User may reference previous command ("that file", "the error", etc.)
  </usage_note>
</session_context>"""


def build_capabilities_xml() -> str:
    """
    Build <tool_capabilities> section explaining Code Djinn's commands.

    This is shared between run and ask modes to avoid duplication.
    """
    return """<tool_capabilities>
You are Code Djinn - a CLI tool with these commands:
- code-djinn run "query": Generate and execute shell commands
- code-djinn ask "query": Analyze previous command output (current mode in ask, not available in run)
- --no-context: Ignore previous command context
- --no-confirm: Skip safety confirmation (run mode only)

Workflow: Each command captures output → next command can reference it via session_context.
To access file contents: Use "code-djinn run 'cat filename'" to read files into session context.
</tool_capabilities>"""
